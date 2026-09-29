from adaptiverag.config import router_cfg
from adaptiverag.generate.select import choose_model
from adaptiverag.types import Classification, RouteDecision

from .fixtures import retrieved


def decision(final: str = "vector", label: str | None = None) -> RouteDecision:
    c = Classification(label, 0.9, {}, "logreg", 0.0, 1) if label else None  # type: ignore[arg-type]
    return RouteDecision("auto", c, final, final)  # type: ignore[arg-type]


def test_graph_or_hybrid_route_goes_large() -> None:
    assert choose_model(decision("graph"), retrieved(), 100) == ("large", "large:route graph")
    assert choose_model(decision("hybrid"), retrieved(), 100)[0] == "large"


def test_relational_label_goes_large() -> None:
    assert choose_model(decision("vector", "multi_hop"), retrieved(), 100) == (
        "large",
        "large:label multi_hop",
    )


def test_long_context_goes_large() -> None:
    limit = router_cfg()["select"]["large_if_context_tokens"]
    size, reason = choose_model(decision("vector", "single_hop"), retrieved(), limit + 1)
    assert size == "large" and reason.startswith("large:context")


def test_simple_question_stays_small() -> None:
    size, reason = choose_model(decision("vector", "single_hop"), retrieved(), 300)
    assert size == "small" and "single_hop" in reason
