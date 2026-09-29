"""Graph reads and writes on Postgres: corpus chunks for extraction, linking, traversal."""

from typing import Any

import numpy as np
from psycopg import Connection
from psycopg.types.json import Jsonb

from adaptiverag.config import router_cfg
from adaptiverag.stores import db
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Chunk, GraphPath, Retrieved, Seed, Strategy


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
# surface form, canonical id, name, type, alias confidence, word similarity
AliasRow = tuple[str, str, str, str, float, float]


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


def traverse(
    seeds: list[Seed], qvec: np.ndarray, depth: int, fanout: int, max_paths: int
) -> list[GraphPath]:
    raise NotImplementedError


def retrieve(question: str, k: int, trace: Trace, qvec: np.ndarray | None = None) -> Retrieved:
    """Hits are the provenance chunks of the best paths."""
    raise NotImplementedError
