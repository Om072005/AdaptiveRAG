from adaptiverag.eval import tune
from adaptiverag.eval.tune import Question

COST = {"vector": 0.001, "graph": 0.002, "hybrid": 0.003}


def q(label: str, conf: float, top: float, path: bool, f1: tuple[float, float, float]) -> Question:
    return Question(label, conf, top, path, dict(zip(tune.ROUTES, f1, strict=True)), COST)


def test_route_follows_the_decision_table() -> None:
    assert tune.route_for(q("single_hop", 0.4, 0.9, True, (1, 1, 1)), 0.6, 0.55) == "hybrid"
    assert tune.route_for(q("single_hop", 0.9, 0.9, True, (1, 1, 1)), 0.6, 0.55) == "vector"
    assert tune.route_for(q("single_hop", 0.9, 0.5, True, (1, 1, 1)), 0.6, 0.55) == "hybrid"
    assert tune.route_for(q("multi_hop", 0.9, 0.9, True, (1, 1, 1)), 0.6, 0.55) == "graph"
    assert tune.route_for(q("comparison", 0.9, 0.9, False, (1, 1, 1)), 0.6, 0.55) == "hybrid"


def test_relational_hybrid_sends_confident_relational_questions_to_hybrid() -> None:
    multi = q("multi_hop", 0.9, 0.9, True, (0.0, 1.0, 0.5))
    assert tune.route_for(multi, 0.6, 0.55, "hybrid") == "hybrid"
    single = q("single_hop", 0.9, 0.9, True, (1, 1, 1))
    assert tune.route_for(single, 0.6, 0.55, "hybrid") == "vector"
    assert tune.simulate([multi], 0.6, 0.55, "hybrid")["routes"]["hybrid"] == 1


def test_simulate_scores_each_question_with_its_route_f1() -> None:
    qs = [
        q("single_hop", 0.9, 0.9, True, (1.0, 0.0, 0.5)),
        q("multi_hop", 0.5, 0.9, True, (0.0, 1.0, 0.25)),
    ]
    r = tune.simulate(qs, 0.6, 0.55)
    assert r["f1"] == (1.0 + 0.25) / 2 and r["routes"] == {"vector": 1, "graph": 0, "hybrid": 1}
    assert r["cost"] == (0.001 + 0.003) / 2


def test_grid_finds_the_better_threshold_and_diff_says_so() -> None:
    # the multi hop question does better on graph, which needs min_confidence at or below 0.5
    qs = [
        q("single_hop", 0.9, 0.9, True, (1.0, 0.0, 0.5)),
        q("multi_hop", 0.5, 0.9, True, (0.0, 1.0, 0.25)),
    ]
    best = tune.grid(qs)[0]
    assert best["f1"] == 1.0 and best["min_confidence"] <= 0.5
    current = tune.simulate(qs, 0.6, 0.55)
    lines = tune.diff_lines(current, best)
    assert lines[0].startswith("[classifier] min_confidence = 0.6 -> ")


def test_no_diff_when_nothing_improves() -> None:
    qs = [q("single_hop", 0.9, 0.9, True, (1.0, 0.0, 0.0))]
    current = tune.simulate(qs, 0.6, 0.55)
    assert tune.diff_lines(current, tune.grid(qs)[0]) == []


def test_ties_prefer_the_cheaper_setting() -> None:
    qs = [q("single_hop", 0.9, 0.6, True, (1.0, 1.0, 1.0))]
    assert tune.grid(qs)[0]["routes"]["vector"] == 1
