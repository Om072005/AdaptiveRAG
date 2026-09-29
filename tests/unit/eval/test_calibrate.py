import pytest

from adaptiverag.eval import calibrate


def test_pearson_and_its_degenerate_cases() -> None:
    assert calibrate.pearson([0.0, 0.5, 1.0], [0.0, 0.5, 1.0]) == pytest.approx(1.0)
    assert calibrate.pearson([0.0, 0.5, 1.0], [1.0, 0.5, 0.0]) == pytest.approx(-1.0)
    assert calibrate.pearson([0.5, 0.5, 0.5], [0.0, 0.5, 1.0]) is None
    assert calibrate.pearson([0.0, 1.0], [0.0, 1.0]) is None


def test_components_need_a_stored_query_response() -> None:
    assert calibrate.components({"answer": "Answer: X"}, "vector", 0.9, False) is None
    detail = {
        "answer": {"text": "Answer: X. It is X [1].", "citations": [{"n": 1, "chunk_id": "c1"}]}
    }
    cov, strength = calibrate.components(detail, "vector", 0.55, False) or (0, 0)
    assert cov == 1.0 and strength == 1.0
    _, graph_strength = calibrate.components(detail, "graph", 0.0, False) or (0, 0)
    assert graph_strength == 0.3


def test_best_weight_picks_the_component_that_tracks_faithfulness() -> None:
    parts = [(0.0, 0.9), (0.5, 0.1), (1.0, 0.5)]  # coverage tracks faithfulness, strength does not
    w, corr = calibrate.best_weight(parts, [0.0, 0.5, 1.0])
    assert w == 1.0 and corr == pytest.approx(1.0)


def test_best_threshold_matches_the_judge_flags() -> None:
    t, acc = calibrate.best_threshold([0.2, 0.3, 0.8, 0.9], [0.25, 0.5, 1.0, 0.75], flag_below=0.6)
    assert acc == 1.0 and 0.3 < t <= 0.8
