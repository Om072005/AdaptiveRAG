import dataclasses

import pytest

from adaptiverag.types import Classification, Hit, Retrieved, RouteDecision


def test_route_decision_defaults_are_not_shared() -> None:
    a = RouteDecision(requested="auto", classification=None, initial="vector", final="vector")
    b = RouteDecision(requested="auto", classification=None, initial="vector", final="vector")
    a.fallbacks.append("vector_low_score->hybrid")
    assert b.fallbacks == []


def test_hit_is_frozen() -> None:
    hit = Hit("d:sentence:0", "d", "Title", "text", 0.8, "vector", 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        hit.score = 0.9  # type: ignore[misc]


def test_retrieved_holds_hits_and_classification_fields() -> None:
    hit = Hit("d:sentence:0", "d", "Title", "text", 0.8, "vector", 1)
    r = Retrieved(hits=[hit], paths=[], seeds=[], top_score=0.8, path_found=False, latency_ms=12)
    c = Classification("multi_hop", 0.7, {"multi_hop": 0.7}, "logreg", 0.0, 1)
    assert r.hits[0].rank == 1 and c.label == "multi_hop"
