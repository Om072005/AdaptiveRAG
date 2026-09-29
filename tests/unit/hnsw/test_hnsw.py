from functools import cache
from pathlib import Path

import numpy as np

from adaptiverag.stores.flat import FlatIndex
from adaptiverag.stores.hnsw import HNSW


def random_unit(n: int, dim: int, seed: int = 7) -> np.ndarray:
    vecs = np.random.default_rng(seed).normal(size=(n, dim)).astype(np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def build(n: int = 1500, dim: int = 24, M: int = 16) -> tuple[HNSW, np.ndarray]:
    data = random_unit(n, dim)
    index = HNSW(dim, M=M)
    index.add(data)
    return index, data


@cache
def shared() -> tuple[HNSW, np.ndarray]:
    """One 1500 point index for the read only tests, built once."""
    return build()


def test_graph_shape_follows_the_parameters() -> None:
    index, data = build(M=8)
    assert len(index.levels) == len(index.links) == len(data)
    assert index.levels[index.entry] == max(index.levels)
    for node, layers in enumerate(index.links):
        assert len(layers) == index.levels[node] + 1
        assert len(layers[0]) <= 16 and all(len(links) <= 8 for links in layers[1:])
        assert node not in {n for links in layers for n in links}
    assert max(index.levels) >= 1  # 1500 nodes with M=8 should reach at least layer 1


def test_every_stored_vector_finds_itself() -> None:
    index, data = shared()
    hits = [index.search(v, 1)[0][0] == i for i, v in enumerate(data[:200])]
    assert sum(hits) >= 199


def test_results_are_sorted_cosine_scores() -> None:
    index, data = shared()
    ids, scores = index.search(random_unit(1, 24, seed=9)[0], 10, ef=50)
    assert len(ids) == 10 and len(set(ids.tolist())) == 10
    assert np.allclose(scores, data[ids] @ random_unit(1, 24, seed=9)[0], atol=1e-5)
    assert all(np.diff(scores) <= 1e-7)


def test_close_to_exact_on_small_data() -> None:
    index, data = shared()
    flat = FlatIndex()
    flat.add(data)
    queries = random_unit(50, 24, seed=11)
    found = [len(set(index.search(q, 10, ef=100)[0]) & set(flat.search(q, 10)[0])) for q in queries]
    assert sum(found) / (10 * len(queries)) >= 0.9


def test_same_seed_builds_the_same_graph() -> None:
    a, _ = build(n=400)
    b, _ = build(n=400)
    assert a.levels == b.levels and a.links == b.links and a.entry == b.entry


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    index, data = build(n=600)
    path = tmp_path / "index.hnsw"
    index.save(str(path))
    loaded = HNSW.load(str(path))
    assert loaded.links == index.links and loaded.levels == index.levels
    for q in random_unit(10, 24, seed=5):
        assert np.array_equal(loaded.search(q, 5)[0], index.search(q, 5)[0])
    extra = random_unit(20, 24, seed=6)
    index.add(extra)
    loaded.add(extra)
    assert loaded.links == index.links  # the level draws continue from the saved rng state


def test_empty_index_and_k_above_size() -> None:
    empty = HNSW(8)
    assert len(empty.search(np.ones(8), 3)[0]) == 0
    index, _ = build(n=5, dim=8)
    assert sorted(index.search(np.ones(8), 10)[0].tolist()) == [0, 1, 2, 3, 4]
