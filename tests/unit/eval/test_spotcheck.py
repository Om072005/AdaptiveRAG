import pytest

from adaptiverag.eval import spotcheck


def test_sample_is_fixed_per_run_and_capped() -> None:
    ids = [f"q{i:03d}" for i in range(100)]
    a = spotcheck.sample_ids(ids, "run-1")
    assert len(a) == 20 and a == spotcheck.sample_ids(list(reversed(ids)), "run-1")
    assert a != spotcheck.sample_ids(ids, "run-2")
    assert spotcheck.sample_ids(ids[:5], "run-1") == ids[:5]


def test_parse_score_maps_like_the_judge() -> None:
    assert [spotcheck.parse_score(s) for s in ["1", " 3 ", "5"]] == [0.0, 0.5, 1.0]
    assert spotcheck.parse_score("6") is None and spotcheck.parse_score("x") is None


def test_answer_text_from_either_detail_shape() -> None:
    assert spotcheck.answer_text({"answer": "Answer: X\nbecause [1]."}) == "Answer: X\nbecause [1]."
    assert spotcheck.answer_text({"answer": {"text": "Answer: Y"}}) == "Answer: Y"
    assert spotcheck.answer_text({}) == ""


def test_agreement_gap_step_and_flag_decision() -> None:
    same = {"faithfulness": 1.0, "relevance": 0.75, "completeness": 1.0}
    pairs = [
        (same, same),
        (
            {"faithfulness": 1.0, "relevance": 1.0, "completeness": 1.0},
            {"faithfulness": 0.25, "relevance": 0.75, "completeness": 1.0},
        ),
    ]
    a = spotcheck.agreement(pairs, flag_below=0.6)
    assert a["n"] == 2
    assert a["faithfulness"] == {"mean_abs_gap": pytest.approx(0.375), "within_one_step": 0.5}
    assert a["relevance"]["within_one_step"] == 1.0
    assert a["same_flag_decision"] == 0.5


def test_agreement_with_no_pairs() -> None:
    a = spotcheck.agreement([], 0.6)
    assert a["n"] == 0 and a["faithfulness"]["mean_abs_gap"] is None
