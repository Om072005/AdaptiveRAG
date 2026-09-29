from collections.abc import Callable

import numpy as np
import pytest

from adaptiverag import llm
from adaptiverag.stores import vector
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Hit

ROWS = [
    ("d1:sentence:0", "d1", "Ed Wood", "Ed Wood is a 1994 film.", 0.81),
    ("d2:sentence:3", "d2", "Tim Burton", "Tim Burton directed it.", 0.64),
]


def test_rows_become_ranked_vector_hits() -> None:
    hits = vector.to_hits(ROWS)
    assert [h.rank for h in hits] == [1, 2]
    assert hits[0] == Hit(
        "d1:sentence:0", "d1", "Ed Wood", "Ed Wood is a 1994 film.", 0.81, "vector", 1
    )
    assert all(h.source == "vector" for h in hits)


def test_unknown_strategy_is_refused() -> None:
    with pytest.raises(ValueError):
        vector.search(np.zeros(768, dtype=np.float32), 8, "tokens")  # type: ignore[arg-type]


def fake_search(seen: list[tuple[int, str]]) -> Callable[..., list[Hit]]:
    def search(qvec: np.ndarray, k: int, strategy: str) -> list[Hit]:
        seen.append((k, strategy))
        return vector.to_hits(ROWS)[:k]

    return search


def test_retrieve_records_the_trace_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[int, str]] = []
    monkeypatch.setattr(vector, "search", fake_search(seen))
    monkeypatch.setattr(llm, "embed", lambda texts, trace=None: np.ones((len(texts), 768)))
    trace = Trace("Who directed Ed Wood?", "vector", "cli")
    r = vector.retrieve("Who directed Ed Wood?", 8, trace)
    assert seen == [(8, "sentence")]
    assert [h.chunk_id for h in r.hits] == ["d1:sentence:0", "d2:sentence:3"]
    assert r.top_score == 0.81 and not r.path_found and r.paths == [] and r.seeds == []
    assert trace.fields["n_results"] == 2
    assert trace.fields["top_score"] == 0.81
    assert trace.fields["retrieval_latency_ms"] == r.latency_ms >= 0


def test_given_query_vector_is_not_embedded_again(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector, "search", fake_search([]))

    def no_embed(texts: list[str], trace: object = None) -> np.ndarray:
        raise AssertionError("qvec was given")

    monkeypatch.setattr(llm, "embed", no_embed)
    r = vector.retrieve("q", 1, Trace("q", "vector", "cli"), qvec=np.ones(768, dtype=np.float32))
    assert len(r.hits) == 1


def test_no_hits_gives_zero_top_score(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector, "search", lambda qvec, k, strategy: [])
    trace = Trace("q", "vector", "cli")
    r = vector.retrieve("q", 8, trace, qvec=np.ones(768, dtype=np.float32))
    assert r.hits == [] and r.top_score == 0.0
    assert trace.fields["n_results"] == 0
