from dataclasses import replace

import numpy as np

from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Hit, Route


def rrf(lists: list[list[Hit]], k: int = 60) -> list[Hit]:
    """Reciprocal rank fusion: a chunk scores the sum of 1 / (k + rank) over the lists holding it.

    One hit per chunk id. A chunk found by more than one backend becomes source 'hybrid', so a
    graph find is never relabelled as a vector one. Ties keep the order the chunks were first seen.
    """
    score: dict[str, float] = {}
    first: dict[str, Hit] = {}
    sources: dict[str, set[Route]] = {}
    for hits in lists:
        seen: set[str] = set()
        for h in sorted(hits, key=lambda h: h.rank):
            if h.chunk_id in seen:  # the same chunk twice in one list counts once, at its best rank
                continue
            seen.add(h.chunk_id)
            score[h.chunk_id] = score.get(h.chunk_id, 0.0) + 1.0 / (k + h.rank)
            first.setdefault(h.chunk_id, h)
            sources.setdefault(h.chunk_id, set()).add(h.source)
    order = sorted(score, key=lambda cid: -score[cid])
    return [
        replace(first[cid], score=score[cid], source=fused_source(sources[cid]), rank=rank)
        for rank, cid in enumerate(order, 1)
    ]


def fused_source(sources: set[Route]) -> Route:
    """'hybrid' when more than one backend found the chunk, else that backend."""
    return next(iter(sources)) if len(sources) == 1 else "hybrid"


def mmr(
    hits: list[Hit], qvec: np.ndarray, vecs: dict[str, np.ndarray], lam: float, k: int
) -> list[Hit]:
    """Maximal marginal relevance: pick lam * cos(query) - (1 - lam) * max cos(picked), k times.

    vecs maps chunk_id to its stored unit embedding; a hit without one ranks after those that have
    one, in input order. Scores and sources are kept, ranks are renumbered from 1.
    """
    known = [h for h in hits if h.chunk_id in vecs]
    rest = [h for h in hits if h.chunk_id not in vecs]
    picked: list[Hit] = []
    if known:
        m = np.array([vecs[h.chunk_id] for h in known], dtype=np.float32)
        relevance = m @ np.asarray(qvec, dtype=np.float32)
        redundancy = np.zeros(len(known), dtype=np.float32)  # a negative cosine counts as none
        left = list(range(len(known)))
        while left and len(picked) < k:
            gain = lam * relevance[left] - (1 - lam) * redundancy[left]
            best = left.pop(int(np.argmax(gain)))  # argmax takes the first of equal gains
            picked.append(known[best])
            redundancy = np.maximum(redundancy, m @ m[best])
    ranked = picked + rest
    return [replace(h, rank=rank) for rank, h in enumerate(ranked[:k], 1)]


def merge_rerank(
    vector_hits: list[Hit], graph_hits: list[Hit], qvec: np.ndarray, k: int, trace: Trace
) -> list[Hit]:
    raise NotImplementedError
