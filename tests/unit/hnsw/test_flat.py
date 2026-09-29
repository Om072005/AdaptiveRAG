import numpy as np

from adaptiverag.stores.flat import FlatIndex


def random_unit(n: int, dim: int, seed: int = 7) -> np.ndarray:
    vecs = np.random.default_rng(seed).normal(size=(n, dim)).astype(np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def test_exact_top_k_on_random_data() -> None:
    data, queries = random_unit(2000, 64), random_unit(20, 64, seed=8)
    index = FlatIndex()
    index.add(data)
    for q in queries:
        ids, scores = index.search(q, 10)
        expected = np.argsort(-(data @ q), kind="stable")[:10]
        assert list(ids) == list(expected)
        assert np.allclose(scores, data[expected] @ q, atol=1e-5)
        assert all(np.diff(scores) <= 0)


def test_ids_continue_across_adds() -> None:
    data = random_unit(30, 16)
    index = FlatIndex()
    index.add(data[:10])
    index.add(data[10:])
    ids, scores = index.search(data[25], 1)
    assert ids[0] == 25 and scores[0] > 0.999


def test_scores_are_cosine_whatever_the_length() -> None:
    data = random_unit(50, 16)
    index = FlatIndex()
    index.add(data * 3.0)
    ids, scores = index.search(data[4] * 0.5, 1)
    assert ids[0] == 4 and abs(scores[0] - 1.0) < 1e-5


def test_ties_break_on_the_lower_id() -> None:
    index = FlatIndex()
    index.add(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]))
    ids, _ = index.search(np.array([1.0, 0.0]), 2)
    assert list(ids) == [0, 2]


def test_k_larger_than_the_index_and_empty_index() -> None:
    index = FlatIndex()
    assert len(index.search(np.ones(4), 3)[0]) == 0
    index.add(random_unit(3, 4))
    ids, scores = index.search(np.ones(4), 10)
    assert sorted(ids) == [0, 1, 2] and len(scores) == 3
