"""Entity resolution (06_DECISIONS.md D9): normalize names, block, merge, write alias rows."""

import hashlib
import re
from collections import Counter, defaultdict
from typing import Any

import numpy as np

from adaptiverag import llm
from adaptiverag.config import ingest_cfg
from adaptiverag.ingest.validate import match_form
from adaptiverag.types import Triple

# dropped from the end of a name so "Apple Inc." and "Apple" resolve together; merges still need
# the same entity type, so a person named like a company is never folded into it
ORG_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "ltd",
    "limited",
    "llc",
    "plc",
}
APOSTROPHE = re.compile(r"['’]s\b|['’]")


def join_initials(words: list[str]) -> list[str]:
    """['j', 'r', 'r', 'tolkien'] -> ['jrr', 'tolkien']: a run of single letters is one token."""
    out: list[str] = []
    after_letter = False
    for w in words:
        if len(w) == 1 and after_letter:
            out[-1] += w
        else:
            out.append(w)
        after_letter = len(w) == 1
    return out


def normalize_name(s: str) -> str:
    """'The Apple Computer Co., Inc.' -> 'apple computer'; 'J. R. R. Tolkien' -> 'jrr tolkien'."""
    words = join_initials(match_form(APOSTROPHE.sub("", s.replace("&", " and "))).split())
    while len(words) > 1 and words[-1] in ORG_SUFFIXES:
        words.pop()
    if len(words) > 1 and words[0] == "the":
        words.pop(0)
    return " ".join(words)


def blocking_key(s: str) -> str:
    """Normalized first token. Only names in the same block (and of the same type) are compared."""
    words = normalize_name(s).split()
    return words[0] if words else ""


def trigrams(s: str) -> set[str]:
    """pg_trgm style trigrams: each normalized word padded with two spaces before, one after."""
    grams: set[str] = set()
    for w in normalize_name(s).split():
        padded = f"  {w} "
        grams.update(padded[i : i + 3] for i in range(len(padded) - 2))
    return grams


def trigram_sim(a: str, b: str) -> float:
    """Shared trigrams over all trigrams, the measure pg_trgm's similarity() uses."""
    ta, tb = trigrams(a), trigrams(b)
    return len(ta & tb) / len(ta | tb) if ta or tb else 0.0


# one name of one type in one document; namesakes in different documents start apart
Node = tuple[str, str, str]  # (type, normalized name, doc_id)
Name = tuple[str, str]  # (type, normalized name): the unit that gets one embedding


def doc_of(chunk_id: str) -> str:
    """Chunk ids are '{doc_id}:{strategy}:{ord}'."""
    return chunk_id.split(":", 1)[0]


def entity_id(type_: str, name: str, anchor_doc: str = "") -> str:
    """'e_' + 12 hex of sha1(type|normalized name); a second namesake adds its anchor doc_id."""
    key = f"{type_}|{normalize_name(name)}" + (f"|{anchor_doc}" if anchor_doc else "")
    return "e_" + hashlib.sha1(key.encode()).hexdigest()[:12]


def relation_id(subject_id: str, predicate: str, object_id: str, chunk_id: str) -> str:
    """First 16 hex of sha1(subject|predicate|object|chunk), the contract's relation key."""
    return hashlib.sha1(f"{subject_id}|{predicate}|{object_id}|{chunk_id}".encode()).hexdigest()[
        :16
    ]


def pick_name(counts: Counter[str]) -> str:
    """Most frequent surface form, then the longest, then alphabetical, so reruns agree."""
    return min(counts, key=lambda s: (-counts[s], -len(s), s))


def ends(t: Triple) -> tuple[Node, Node]:
    doc = doc_of(t.chunk_id)
    subject: Node = (t.subject_type, normalize_name(t.subject), doc)
    obj: Node = (t.object_type, normalize_name(t.object), doc)
    return subject, obj


def mentions(triples: list[Triple]) -> tuple[dict[Node, Counter[str]], dict[Node, set[Name]]]:
    """Surface forms seen per node, and the names at the other end of each node's triples."""
    surfaces: dict[Node, Counter[str]] = defaultdict(Counter)
    neighbours: dict[Node, set[Name]] = defaultdict(set)
    for t in triples:
        s, o = ends(t)
        if s[1] and o[1]:
            surfaces[s][t.subject.strip()] += 1
            surfaces[o][t.object.strip()] += 1
            neighbours[s].add(o[:2])
            neighbours[o].add(s[:2])
    return surfaces, neighbours


def cosine(vecs: dict[Name, np.ndarray], a: Name, b: Name) -> float:
    return float(vecs[a] @ vecs[b]) if a in vecs and b in vecs else 0.0


def merge_reason(
    a: Node,
    b: Node,
    neighbours: dict[Node, set[Name]],
    vecs: dict[Name, np.ndarray],
    cfg: dict[str, Any],
) -> str | None:
    """Why D9 merges two nodes ('name 0.95', 'embedding 0.91; same document'), or None.
    Two PERSON nodes also need the same document or a shared neighbour."""
    if a[0] != b[0]:
        return None
    sim, cos = trigram_sim(a[1], b[1]), cosine(vecs, a[:2], b[:2])
    if sim >= cfg["name_sim"]:
        reason = f"name {sim:.2f}"
    elif cos >= cfg["embed_sim"]:
        reason = f"embedding {cos:.2f}"
    else:
        return None
    if a[0] == "PERSON" and cfg["person_needs_shared_neighbor"]:
        if a[2] == b[2]:
            return f"{reason}; same document"
        if neighbours[a] & neighbours[b]:
            return f"{reason}; shared neighbour"
        return None
    return reason


def same_entity(
    a: Node,
    b: Node,
    neighbours: dict[Node, set[Name]],
    vecs: dict[Name, np.ndarray],
    cfg: dict[str, Any],
) -> bool:
    """D9 merge rule."""
    return merge_reason(a, b, neighbours, vecs, cfg) is not None


def clusters(
    nodes: list[Node],
    neighbours: dict[Node, set[Name]],
    vecs: dict[Name, np.ndarray],
    cfg: dict[str, Any],
    merges: list[tuple[Node, Node, str]] | None = None,
) -> list[list[Node]]:
    """Union find over pairs from the same (type, first token) block, in sorted order. Each merge
    made is appended to merges when a list is given, for the labelled precision sample."""
    parent = {n: n for n in nodes}

    def root(n: Node) -> Node:
        while parent[n] != n:
            n = parent[n]
        return n

    blocks: dict[tuple[str, str], list[Node]] = defaultdict(list)
    for n in sorted(nodes):
        blocks[(n[0], blocking_key(n[1]))].append(n)
    for block in blocks.values():
        for i, a in enumerate(block):
            for b in block[i + 1 :]:
                if root(a) == root(b):
                    continue
                reason = merge_reason(a, b, neighbours, vecs, cfg)
                if reason:
                    keep, drop = sorted((root(a), root(b)))
                    parent[drop] = keep
                    if merges is not None:
                        merges.append((a, b, reason))
    groups: dict[Node, list[Node]] = defaultdict(list)
    for n in sorted(nodes):
        groups[root(n)].append(n)
    return list(groups.values())


def build_rows(
    triples: list[Triple], vecs: dict[Name, np.ndarray], cfg: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Pure core of resolve(): cluster the nodes, then one row per entity, alias and relation."""
    surfaces, neighbours = mentions(triples)
    groups = clusters(list(surfaces), neighbours, vecs, cfg)
    # when namesakes stay apart, the most mentioned one keeps the plain contract id
    groups.sort(key=lambda g: (-sum(sum(surfaces[n].values()) for n in g), min(n[2] for n in g)))

    entities: list[dict[str, Any]] = []
    aliases: list[dict[str, Any]] = []
    entity_of: dict[Node, str] = {}
    for group in groups:
        counts: Counter[str] = Counter()
        for n in group:
            counts.update(surfaces[n])
        type_, name = group[0][0], pick_name(counts)
        eid = entity_id(type_, name)
        if any(e["canonical_id"] == eid for e in entities):
            eid = entity_id(type_, name, min(n[2] for n in group))
        if any(e["canonical_id"] == eid for e in entities):
            raise ValueError(f"two {type_} entities named {name!r} share an anchor document")
        canon: Name = (type_, normalize_name(name))
        entities.append(
            {
                "canonical_id": eid,
                "canonical_name": name,
                "type": type_,
                "embedding": vecs.get(canon),
            }
        )
        for surface in sorted(counts):
            key: Name = (type_, normalize_name(surface))
            conf = (
                1.0 if key == canon else max(trigram_sim(surface, name), cosine(vecs, key, canon))
            )
            aliases.append(
                {"surface_form": surface, "canonical_id": eid, "confidence": min(conf, 1.0)}
            )
        entity_of.update((n, eid) for n in group)

    relations: dict[str, dict[str, Any]] = {}
    for t in triples:
        s_node, o_node = ends(t)
        s, o = entity_of.get(s_node), entity_of.get(o_node)
        # skipped: a name that normalizes to nothing, or both ends resolved to one entity
        if s is None or o is None or s == o:
            continue
        rel_id = relation_id(s, t.predicate, o, t.chunk_id)
        if rel_id in relations and relations[rel_id]["extraction_confidence"] >= t.confidence:
            continue
        relations[rel_id] = {
            "rel_id": rel_id,
            "subject_id": s,
            "predicate": t.predicate,
            "object_id": o,
            "chunk_id": t.chunk_id,
            "doc_id": doc_of(t.chunk_id),
            "evidence_start": t.evidence_start,
            "evidence_end": t.evidence_end,
            "extraction_confidence": t.confidence,
        }
    return entities, aliases, list(relations.values())


def merge_decisions(
    triples: list[Triple], vecs: dict[Name, np.ndarray], cfg: dict[str, Any]
) -> list[dict[str, str]]:
    """Every merge the resolver makes on these triples: both names as written, their type, their
    documents and the rule that fired. A person labels a sample of them for precision."""
    surfaces, neighbours = mentions(triples)
    merges: list[tuple[Node, Node, str]] = []
    clusters(list(surfaces), neighbours, vecs, cfg, merges)
    return [
        {
            "type": a[0],
            "a": pick_name(surfaces[a]),
            "a_doc": a[2],
            "b": pick_name(surfaces[b]),
            "b_doc": b[2],
            "rule": reason,
        }
        for a, b, reason in merges
    ]


def resolve(
    triples: list[Triple],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """(entities, aliases, relations) rows. Each distinct name is embedded once via llm.embed."""
    names, texts = name_texts(triples)
    matrix = llm.embed(texts)
    return build_rows(triples, dict(zip(names, matrix, strict=True)), ingest_cfg()["resolve"])


def name_texts(triples: list[Triple]) -> tuple[list[Name], list[str]]:
    """Each distinct (type, normalized name) and the surface form embedded for it."""
    surfaces, _ = mentions(triples)
    by_name: dict[Name, Counter[str]] = defaultdict(Counter)
    for node, counts in surfaces.items():
        by_name[node[:2]].update(counts)
    names = sorted(by_name)
    return names, [pick_name(by_name[n]) for n in names]


def graph_texts(triples: list[Triple]) -> list[str]:
    """Every text a graph build embeds: the names, then the relations as a build without
    embeddings would resolve them. Merges by embedding later change a few relation texts."""
    _, names = name_texts(triples)
    entities, _, relations = build_rows(triples, {}, ingest_cfg()["resolve"])
    return sorted(set(names) | set(relation_texts(entities, relations)))


def relation_texts(entities: list[dict[str, Any]], relations: list[dict[str, Any]]) -> list[str]:
    """'subject predicate object' per relation, with canonical names; this is what gets embedded."""
    names = {e["canonical_id"]: e["canonical_name"] for e in entities}
    return [
        f"{names[r['subject_id']]} {r['predicate'].replace('_', ' ')} {names[r['object_id']]}"
        for r in relations
    ]
