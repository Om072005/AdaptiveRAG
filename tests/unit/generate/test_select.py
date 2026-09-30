import pytest

from adaptiverag.generate import select
from adaptiverag.generate.select import choose_model
from adaptiverag.types import Classification, RouteDecision

from .fixtures import retrieved


def decision(final: str = "vector", label: str | None = None) -> RouteDecision:
    c = Classification(label, 0.9, {}, "logreg", 0.0, 1) if label else None  # type: ignore[arg-type]
    return RouteDecision("auto", c, final, final)  # type: ignore[arg-type]


# the rules the selector can express; the served config (D17) empties the route and label lists
RULES = {
    "select": {
        "large_if_routes": ["graph", "hybrid"],
        "large_if_labels": ["multi_hop", "comparison"],
        "large_if_context_tokens": 2500,
    }
}
LIMIT = RULES["select"]["large_if_context_tokens"]


@pytest.fixture(autouse=True)
def rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(select, "router_cfg", lambda: RULES)


def test_graph_or_hybrid_route_goes_large() -> None:
    assert choose_model(decision("graph"), retrieved(), 100) == ("large", "large:route graph")
    assert choose_model(decision("hybrid"), retrieved(), 100)[0] == "large"


def test_relational_label_goes_large() -> None:
    assert choose_model(decision("vector", "multi_hop"), retrieved(), 100) == (
        "large",
        "large:label multi_hop",
    )


def test_long_context_goes_large() -> None:
    size, reason = choose_model(decision("vector", "single_hop"), retrieved(), LIMIT + 1)
    assert size == "large" and reason.startswith("large:context")


def test_simple_question_stays_small() -> None:
    size, reason = choose_model(decision("vector", "single_hop"), retrieved(), 300)
    assert size == "small" and "single_hop" in reason


def test_empty_rule_lists_keep_graph_and_hybrid_small(monkeypatch: pytest.MonkeyPatch) -> None:
    # D17: always-small matched the selector's F1 at 1/60 of the cost, so the lists are empty
    served = {"select": {**RULES["select"], "large_if_routes": [], "large_if_labels": []}}
    monkeypatch.setattr(select, "router_cfg", lambda: served)
    for final, label in (("graph", "multi_hop"), ("hybrid", "comparison")):
        assert choose_model(decision(final, label), retrieved(), 300)[0] == "small"
