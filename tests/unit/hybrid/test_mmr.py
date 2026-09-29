import numpy as np

from adaptiverag.router.hybrid import mmr
from adaptiverag.types import Hit, Route


def unit(*xs: float) -> np.ndarray:
    v = np.array(xs, dtype=np.float32)
    return v / np.linalg.norm(v)


def hit(chunk_id: str, rank: int, source: Route = "vector") -> Hit:
    return Hit(chunk_id, "d", "T", chunk_id, 1.0 / rank, source, rank)


Q = unit(1, 0, 0)
VECS = {
    "a": unit(0.82, 0.572, 0),  # most relevant, cosine 0.82
    "a_copy": unit(0.81, 0.585, 0.03),  # near duplicate of a, cosine 0.81
    "b": unit(0.78, -0.3, 0.55),  # a little less relevant, different content
}


def test_near_duplicate_chunks_are_pushed_down() -> None:
    hits = [hit("a", 1), hit("a_copy", 2), hit("b", 3)]
    ranked = mmr(hits, Q, VECS, lam=0.7, k=3)
    assert [h.chunk_id for h in ranked] == ["a", "b", "a_copy"]
    assert [h.rank for h in ranked] == [1, 2, 3]


def test_lambda_one_is_plain_relevance() -> None:
    hits = [hit("b", 1), hit("a_copy", 2), hit("a", 3)]
    assert [h.chunk_id for h in mmr(hits, Q, VECS, lam=1.0, k=3)] == ["a", "a_copy", "b"]


def test_k_limits_and_scores_and_sources_are_kept() -> None:
    hits = [hit("a", 1, "graph"), hit("a_copy", 2), hit("b", 3, "hybrid")]
    ranked = mmr(hits, Q, VECS, lam=0.7, k=2)
    assert [(h.chunk_id, h.source, h.score) for h in ranked] == [
        ("a", "graph", 1.0),
        ("b", "hybrid", 1 / 3),
    ]


def test_hits_without_a_vector_rank_after_the_others() -> None:
    hits = [hit("x", 1, "graph"), hit("a", 2), hit("b", 3)]
    assert [h.chunk_id for h in mmr(hits, Q, VECS, lam=0.7, k=5)] == ["a", "b", "x"]


def test_empty() -> None:
    assert mmr([], Q, VECS, lam=0.7, k=5) == []
