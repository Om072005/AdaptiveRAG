import pytest

from adaptiverag.eval import review

ROW = {
    "gold_type": "multi_hop",
    "predicted_type": "multi_hop",
    "faithfulness": 1.0,
    "relevance": 1.0,
    "completeness": 1.0,
    "answer_confidence": 0.9,
    "classifier_confidence": 0.9,
}


def test_clean_row_needs_no_review() -> None:
    assert review.flag_reasons(ROW, 0.6, 0.55) == []


def test_each_low_judge_metric_is_its_own_reason() -> None:
    row = ROW | {"faithfulness": 0.25, "completeness": 0.5}
    assert review.flag_reasons(row, 0.6, 0.55) == [
        ("judge_below_threshold", "faithfulness", 0.25),
        ("judge_below_threshold", "completeness", 0.5),
    ]


def test_low_answer_confidence_and_misroute() -> None:
    row = ROW | {
        "answer_confidence": 0.3,
        "predicted_type": "single_hop",
        "classifier_confidence": 0.85,
    }
    assert review.flag_reasons(row, 0.6, 0.55) == [
        ("answer_confidence_low", "answer_confidence", 0.3),
        ("misroute", "classifier_confidence", 0.85),
    ]


def test_unjudged_row_and_forced_route_are_not_flagged() -> None:
    row = ROW | {
        "faithfulness": None,
        "relevance": None,
        "completeness": None,
        "predicted_type": None,
    }
    assert review.flag_reasons(row, 0.6, 0.55) == []


def test_threshold_is_strictly_below() -> None:
    assert review.flag_reasons(ROW | {"relevance": 0.6}, 0.6, 0.55) == []


def test_label_rejects_unknown_status() -> None:
    with pytest.raises(SystemExit, match="status must be one of"):
        review.label(None, 1, "maybe", "dhruv", None)  # type: ignore[arg-type]
