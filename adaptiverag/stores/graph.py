"""Graph reads and writes on Postgres: corpus chunks for extraction, linking, traversal."""

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

import numpy as np
from psycopg import Connection
from psycopg.types.json import Jsonb

from adaptiverag import llm
from adaptiverag.config import router_cfg
from adaptiverag.stores import db
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Chunk, Edge, GraphPath, Hit, Retrieved, Seed, Strategy


def corpus_chunks(doc_ids: list[str], strategy: Strategy) -> tuple[list[Chunk], dict[str, str]]:
    """Chunks of one strategy for these documents in (doc_id, ord) order, and each doc's text."""
    with db.conn() as c:
        rows = c.execute(
            "select chunk_id, doc_id, strategy, ord, start_offset, end_offset, text, n_words "
            "from chunks where doc_id = any(%s) and strategy = %s order by doc_id, ord",
            (doc_ids, strategy),
        ).fetchall()
        docs = c.execute(
            "select doc_id, text from documents where doc_id = any(%s)", (doc_ids,)
        ).fetchall()
    return [Chunk(*row) for row in rows], {doc_id: text for doc_id, text in docs}


# rejects of these chunks, including whole responses (chunk_id null) that covered one of them
OF_CHUNKS = "chunk_id = any(%s) or (chunk_id is null and raw->'chunk_ids' ?| %s)"


def save_rejects(rejects: list[dict[str, Any]], chunk_ids: list[str]) -> None:
    """Replace the stored rejects of these chunks, so a rerun does not count them twice."""
    with db.conn() as c:
        c.execute(f"delete from extraction_rejects where {OF_CHUNKS}", (chunk_ids, chunk_ids))
        with c.cursor() as cur:
            cur.executemany(
                "insert into extraction_rejects (chunk_id, raw, reason) values (%s, %s, %s)",
                [(r["chunk_id"], Jsonb(r["raw"]), r["reason"]) for r in rejects],
            )


def reject_counts(chunk_ids: list[str]) -> dict[str, int]:
    """Stored rejects of these chunks by reason."""
    with db.conn() as c:
        rows = c.execute(
            f"select reason, count(*) from extraction_rejects where {OF_CHUNKS} "
            "group by reason order by reason",
            (chunk_ids, chunk_ids),
        ).fetchall()
    return {reason: n for reason, n in rows}


# an alias counts as found when it matches a run of words in the question (pg_trgm word similarity)
ALIAS_MATCH = """
select a.surface_form, a.canonical_id, e.canonical_name, e.type, a.confidence,
       word_similarity(lower(a.surface_form), lower(%(q)s))
from aliases a join entities e using (canonical_id)
where word_similarity(lower(a.surface_form), lower(%(q)s)) >= %(min)s
"""
NEAREST_ENTITY = """
select canonical_id, canonical_name, type, 1 - (embedding <=> %(q)s)
from entities where embedding is not null
order by embedding <=> %(q)s limit 1
"""
# every relation touching the frontier, with the cosine of its embedding to the question
FRONTIER_EDGES = """
select r.rel_id, r.subject_id, s.canonical_name, r.predicate, r.object_id, o.canonical_name,
       r.chunk_id, r.extraction_confidence, coalesce(1 - (r.embedding <=> %(q)s), 0)
from relations r
join entities s on s.canonical_id = r.subject_id
join entities o on o.canonical_id = r.object_id
where r.subject_id = any(%(ids)s) or r.object_id = any(%(ids)s)
"""
CHUNK_TEXT = """
select c.chunk_id, c.doc_id, d.title, c.text
from chunks c join documents d using (doc_id) where c.chunk_id = any(%s)
"""

# surface form, canonical id, name, type, alias confidence, word similarity
AliasRow = tuple[str, str, str, str, float, float]
# frontier ids -> (edge, cosine to the question) rows
Fetch = Callable[[list[str]], list[tuple[Edge, float]]]


def pick_seeds(rows: list[AliasRow], min_score: float) -> list[Seed]:
    """One seed per entity scored alias confidence x word similarity, best first. An alias inside
    a longer matched alias that scores as well is dropped ('Tim' when 'Tim Burton' matched)."""
    best: dict[str, Seed] = {}
    for surface, cid, name, type_, conf, sim in rows:
        score = float(conf) * float(sim)
        if score >= min_score and (cid not in best or score > best[cid].score):
            best[cid] = Seed(cid, name, type_, score, surface)
    seeds = sorted(best.values(), key=lambda s: (-s.score, -len(s.matched), s.canonical_id))
    return [
        s
        for s in seeds
        if not any(
            len(o.matched) > len(s.matched)
            and s.matched.lower() in o.matched.lower()
            and o.score >= s.score
            for o in seeds
        )
    ]


def nearest_seed(rows: list[tuple[str, str, str, float]], min_score: float) -> list[Seed]:
    """The entity nearest the question embedding, when no alias matched and it is close enough."""
    return [
        Seed(c, name, t, float(cos), "embedding") for c, name, t, cos in rows if cos >= min_score
    ]


def seeds_for(c: Connection[Any], question: str, qvec: np.ndarray, min_score: float) -> list[Seed]:
    """Alias matches first; the embedding fallback only when no alias matched."""
    seeds = pick_seeds(
        c.execute(ALIAS_MATCH, {"q": question, "min": min_score}).fetchall(), min_score
    )
    if seeds:
        return seeds
    rows = c.execute(NEAREST_ENTITY, {"q": np.asarray(qvec, dtype=np.float32)}).fetchall()
    return nearest_seed(rows, min_score)


def link_entities(question: str, qvec: np.ndarray, trace: Trace) -> list[Seed]:
    """Seed entities for the question: aliases found in it, else the nearest entity by embedding."""
    with trace.span("link"):
        return seeds_for(
            db.shared(), question, qvec, float(router_cfg()["graph"]["min_seed_score"])
        )


def edge_score(confidence: float, cos: float) -> float:
    """D10: extraction confidence x (0.5 + 0.5 x cosine of the relation and the question)."""
    return confidence * (0.5 + 0.5 * cos)


def bfs(
    seeds: list[Seed], fetch: Fetch, depth: int, fanout: int, max_paths: int
) -> list[GraphPath]:
    """Breadth first from every seed, one fetch per hop for the whole frontier. Each node keeps its
    fanout best edges, a path never revisits a node, and a path's score is the product of its edge
    scores. Paths joining two seeds rank first, then by score, ties by relation ids."""
    seed_ids = {s.canonical_id for s in seeds}
    # (start, end, edges, score, nodes on the path)
    frontier: list[tuple[str, str, tuple[Edge, ...], float, frozenset[str]]] = [
        (s, s, (), 1.0, frozenset({s})) for s in sorted(seed_ids)
    ]
    found: dict[tuple[str, ...], GraphPath] = {}
    for _ in range(depth):
        ends = sorted({end for _, end, _, _, _ in frontier})
        if not ends:
            break
        best: dict[str, list[tuple[float, Edge]]] = defaultdict(list)
        for edge, cos in fetch(ends):
            for node in {edge.subject_id, edge.object_id} & set(ends):
                best[node].append((edge_score(edge.confidence, cos), edge))
        for node in best:
            best[node] = sorted(best[node], key=lambda p: (-p[0], p[1].rel_id))[:fanout]
        grown = []
        for start, end, edges, score, seen in frontier:
            for s, edge in best.get(end, []):
                other = edge.object_id if edge.subject_id == end else edge.subject_id
                if other in seen:
                    continue
                joins = bool(((seen | {other}) - {start}) & seed_ids)
                path = GraphPath((*edges, edge), score * s, joins)
                # the same edges walked from the other seed are the same path
                key = tuple(sorted(e.rel_id for e in path.edges))
                if key not in found or path.score > found[key].score:
                    found[key] = path
                grown.append((start, other, path.edges, path.score, seen | {other}))
        frontier = grown
    ranked = sorted(
        found.values(), key=lambda p: (not p.connects_seeds, -p.score, [e.rel_id for e in p.edges])
    )
    return ranked[:max_paths]


def edges_for(c: Connection[Any], ids: list[str], qvec: np.ndarray) -> list[tuple[Edge, float]]:
    """Relations touching these entities, as edges with their cosine to the question."""
    q = np.asarray(qvec, dtype=np.float32)
    rows = c.execute(FRONTIER_EDGES, {"q": q, "ids": ids}).fetchall()
    return [
        (Edge(r[0], r[1], r[2], r[3], r[4], r[5], r[6], float(r[7])), float(r[8])) for r in rows
    ]


def traverse(
    seeds: list[Seed], qvec: np.ndarray, depth: int, fanout: int, max_paths: int
) -> list[GraphPath]:
    """BFS from the seeds (D10), one query per hop for the whole frontier."""
    c = db.shared()
    return bfs(seeds, lambda ids: edges_for(c, ids, qvec), depth, fanout, max_paths)


def provenance(paths: list[GraphPath], k: int) -> list[tuple[str, float]]:
    """(chunk_id, path score) of the chunks the best paths cite, in path order, each chunk once."""
    order: dict[str, float] = {}
    for p in paths:
        for e in p.edges:
            order.setdefault(e.chunk_id, p.score)
    return list(order.items())[:k]


def path_found(paths: list[GraphPath], min_path_score: float) -> bool:
    """D10: a path joining two seeds, or a single seed path at or above graph.min_path_score."""
    return any(p.connects_seeds or p.score >= min_path_score for p in paths)


def retrieve_from_seeds(
    c: Connection[Any], seeds: list[Seed], k: int, qvec: np.ndarray, trace: Trace
) -> Retrieved:
    """Traverse from seeds already linked; the cited chunks become hits. The router links once."""
    cfg = router_cfg()["graph"]
    started = time.perf_counter()
    depth, fanout, max_paths = int(cfg["depth"]), int(cfg["fanout"]), int(cfg["max_paths"])
    paths = bfs(seeds, lambda ids: edges_for(c, ids, qvec), depth, fanout, max_paths)
    cited = provenance(paths, k)
    rows = {r[0]: r for r in c.execute(CHUNK_TEXT, ([cid for cid, _ in cited],)).fetchall()}
    stored = [(cid, score) for cid, score in cited if cid in rows]
    hits = [
        Hit(cid, rows[cid][1], rows[cid][2], rows[cid][3], score, "graph", rank)
        for rank, (cid, score) in enumerate(stored, 1)
    ]
    latency_ms = int((time.perf_counter() - started) * 1000)
    top = paths[0].score if paths else 0.0
    found = path_found(paths, float(cfg["min_path_score"]))
    trace.set(retrieval_latency_ms=latency_ms, n_results=len(hits), top_score=top, path_found=found)
    return Retrieved(hits, paths, seeds, top, found, latency_ms)


def retrieve(question: str, k: int, trace: Trace, qvec: np.ndarray | None = None) -> Retrieved:
    """Hits are the provenance chunks of the best paths."""
    if qvec is None:
        qvec = llm.embed([question], trace=trace)[0]
    seeds = link_entities(question, qvec, trace)
    return retrieve_from_seeds(db.shared(), seeds, k, qvec, trace)
