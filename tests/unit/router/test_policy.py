"""One test per row of the decision table in 01_CONTRACTS.md section 3, plus the boundaries."""

import pytest

from adaptiverag.config import router_cfg
from adaptiverag.router.policy import decide_initial, needs_fallback
from adaptiverag.types import Classification, QType, Retrieved, Route, Seed

CFG = {
    "classifier": {"min_confidence": 0.60},
    "vector": {"min_top_score": 0.55},
    "graph": {"min_seed_score": 0.45, "min_path_score": 0.20},
    "policy": {"low_budget_usd": 0.05},
}
PLENTY = 1.0


def labelled(label: QType, confidence: float = 0.9) -> Classification:
    return Classification(label, confidence, {label: confidence}, "rules", 0.0, 0)


def seed(score: float) -> Seed:
    return Seed("e_1", "Tim Burton", "PERSON", score, "tim burton")


def retrieved(top_score: float = 0.8, path_found: bool = True) -> Retrieved:
    return Retrieved([], [], [], top_score, path_found, 5)


@pytest.mark.parametrize("mode", ["vector", "graph", "hybrid"])
def test_row1_forced_mode_is_taken_as_is(mode: Route) -> None:
    # even an ambiguous classification and no seeds do not change a forced route
    assert decide_initial(mode, labelled("multi_hop", 0.1), [], PLENTY, CFG) == (
        mode,
        [f"forced:{mode}"],
    )


def test_row2_low_classifier_confidence_goes_hybrid() -> None:
    assert decide_initial("auto", labelled("multi_hop", 0.42), [seed(0.9)], PLENTY, CFG) == (
        "hybrid",
        ["ambiguous:multi_hop 0.42"],
    )


def test_row2_confidence_at_the_bar_is_not_ambiguous() -> None:
    route, _ = decide_initial("auto", labelled("single_hop", 0.60), [], PLENTY, CFG)
    assert route == "vector"


def test_row3_single_hop_goes_vector() -> None:
    assert decide_initial("auto", labelled("single_hop"), [seed(0.9)], PLENTY, CFG) == (
        "vector",
        ["no_relational_structure"],
    )


@pytest.mark.parametrize("label", ["multi_hop", "comparison"])
def test_row4_relational_without_graph_seeds_goes_vector(label: QType) -> None:
    for seeds in ([], [seed(0.44)]):
        assert decide_initial("auto", labelled(label), seeds, PLENTY, CFG) == (
            "vector",
            ["entities_not_in_graph"],
        )


@pytest.mark.parametrize("label", ["multi_hop", "comparison"])
def test_row5_relational_with_seeds_goes_graph(label: QType) -> None:
    seeds = [seed(0.2), seed(0.45)]  # one seed at the bar is enough
    assert decide_initial("auto", labelled(label), seeds, PLENTY, CFG) == (
        "graph",
        [f"relational:{label}"],
    )


def test_auto_without_a_classification_is_a_bug() -> None:
    with pytest.raises(ValueError):
        decide_initial("auto", None, [], PLENTY, CFG)


def test_f1_weak_vector_results_fall_back() -> None:
    assert needs_fallback("vector", retrieved(top_score=0.54), CFG) == "vector_low_score"
    assert needs_fallback("vector", retrieved(top_score=0.55), CFG) is None


def test_f2_graph_without_a_connected_path_falls_back() -> None:
    assert needs_fallback("graph", retrieved(top_score=0.0, path_found=False), CFG) == (
        "graph_no_path"
    )
    assert needs_fallback("graph", retrieved(top_score=0.0, path_found=True), CFG) is None


def test_hybrid_never_falls_back() -> None:
    assert needs_fallback("hybrid", retrieved(top_score=0.0, path_found=False), CFG) is None


def test_config_has_every_key_the_policy_reads() -> None:
    real = router_cfg()
    for section, keys in CFG.items():
        assert set(keys) <= set(real[section])


LOW = 0.049  # under policy.low_budget_usd = 0.05


def test_row6_low_budget_turns_graph_into_vector() -> None:
    assert decide_initial("auto", labelled("multi_hop"), [seed(0.9)], LOW, CFG) == (
        "vector",
        ["relational:multi_hop", "low_budget"],
    )


def test_row6_low_budget_turns_hybrid_into_vector() -> None:
    assert decide_initial("auto", labelled("comparison", 0.3), [], LOW, CFG) == (
        "vector",
        ["ambiguous:comparison 0.30", "low_budget"],
    )


def test_row6_leaves_vector_and_forced_routes_alone() -> None:
    assert decide_initial("auto", labelled("single_hop"), [], LOW, CFG) == (
        "vector",
        ["no_relational_structure"],
    )
    assert decide_initial("graph", labelled("multi_hop"), [seed(0.9)], LOW, CFG) == (
        "graph",
        ["forced:graph"],
    )


def test_row6_budget_at_the_bar_is_not_low() -> None:
    route, _ = decide_initial("auto", labelled("multi_hop"), [seed(0.9)], 0.05, CFG)
    assert route == "graph"
