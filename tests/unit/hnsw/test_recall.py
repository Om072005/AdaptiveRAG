"""Recall of our HNSW against the exact flat index, on data small enough for every check run.

The 10k x 768 random vector measurement is a benchmark (bench/hnsw_vs_flat.py), not a unit test.
"""

from functools import cache

import numpy as np

from adaptiverag.stores.flat import FlatIndex
from adaptiverag.stores.hnsw import HNSW


def clustered(n: int, dim: int, clusters: int, seed: int = 7) -> np.ndarray:
    """Points scattered around a few centres, closer to how text embeddings sit than pure noise."""
    rng = np.random.default_rng(seed)
    centres = rng.normal(size=(clusters, dim))
    vecs = centres[rng.integers(clusters, size=n)] + 0.35 * rng.normal(size=(n, dim))
    return (vecs / np.linalg.norm(vecs, axis=1, keepdims=True)).astype(np.float32)


def recall_at_10(index: HNSW, flat: FlatIndex, queries: np.ndarray, ef: int) -> float:
    found = [
        len(set(index.search(q, 10, ef=ef)[0].tolist()) & set(flat.search(q, 10)[0].tolist()))
        for q in queries
    ]
    return sum(found) / (10 * len(queries))


@cache
def built(kind: str) -> tuple[HNSW, FlatIndex, np.ndarray]:
    if kind == "clustered":
        data, queries = clustered(1500, 32, 20), clustered(50, 32, 20, seed=8)
    else:
        rng = np.random.default_rng(7)
        data, queries = rng.normal(size=(1500, 32)), rng.normal(size=(50, 32))
    index, flat = HNSW(32), FlatIndex()
    index.add(data)
    flat.add(data)
    return index, flat, queries


def test_recall_at_10_on_clustered_data_at_ef_64() -> None:
    index, flat, queries = built("clustered")
    assert recall_at_10(index, flat, queries, ef=64) >= 0.95


def test_recall_rises_with_ef_and_reaches_exact() -> None:
    index, flat, queries = built("random")
    recalls = [recall_at_10(index, flat, queries, ef) for ef in (10, 64, 400)]
    assert recalls[0] <= recalls[1] <= recalls[2]
    assert recalls[2] >= 0.99
