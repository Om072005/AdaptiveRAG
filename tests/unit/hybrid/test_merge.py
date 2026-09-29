import numpy as np
import pytest

from adaptiverag.router import hybrid
from adaptiverag.stores import vector
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Hit, Route


def hit(chunk_id: str, rank: int, source: Route) -> Hit:
    return Hit(chunk_id, chunk_id.split(":")[0], "T", chunk_id, 0.5, source, rank)


def unit(*xs: float) -> np.ndarray:
    v = np.array(xs, dtype=np.float32)
    return v / np.linalg.norm(v)


VECS = {"v1:s:0": unit(1, 0.1, 0), "both:s:0": unit(0.9, 0, 0.4), "g1:s:0": unit(0.2, 1, 0)}


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    asked: list[list[str]] = []

    def chunk_vectors(ids: list[str]) -> dict[str, np.ndarray]:
        asked.append(ids)
        return {i: VECS[i] for i in ids if i in VECS}

    monkeypatch.setattr(vector, "chunk_vectors", chunk_vectors)
    return asked


def test_merge_records_its_span_and_reads_vectors_once(stored: list[list[str]]) -> None:
    trace = Trace("q", "hybrid", "cli")
    vector_hits = [hit("v1:s:0", 1, "vector"), hit("both:s:0", 2, "vector")]
    graph_hits = [hit("both:s:0", 1, "graph"), hit("g1:s:0", 2, "graph")]
    merged = hybrid.merge_rerank(vector_hits, graph_hits, unit(1, 0, 0), 8, trace)
    assert [s["name"] for s in trace.spans] == ["merge"]
    assert len(stored) == 1 and sorted(stored[0]) == ["both:s:0", "g1:s:0", "v1:s:0"]
    assert [h.rank for h in merged] == [1, 2, 3]


def test_k_caps_the_merged_list(stored: list[list[str]]) -> None:
    graph_hits = [hit("g1:s:0", 1, "graph")]
    vector_hits = [hit("v1:s:0", 1, "vector"), hit("both:s:0", 2, "vector")]
    merged = hybrid.merge_rerank(
        vector_hits, graph_hits, unit(1, 0, 0), 2, Trace("q", "hybrid", "cli")
    )
    assert len(merged) == 2


def test_no_hits_at_all(stored: list[list[str]]) -> None:
    assert hybrid.merge_rerank([], [], unit(1, 0, 0), 8, Trace("q", "hybrid", "cli")) == []
