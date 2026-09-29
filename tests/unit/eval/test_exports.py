from adaptiverag.eval import bake, replays

LOG = """| # | Symptom | Root cause | Fix | Status | Run |
|---|---|---|---|---|---|
| 1 | Low recall | Random vectors | None | Open | `20260929-1429-random` |
| 2 | Crash | Bug | Fixed | Closed |  |
"""


def test_parse_failures_reads_the_log_table() -> None:
    rows = bake.parse_failures(LOG)
    assert rows[0] == {
        "n": 1,
        "symptom": "Low recall",
        "root_cause": "Random vectors",
        "fix": "None",
        "status": "Open",
        "run_id": "20260929-1429-random",
    }
    assert rows[1]["run_id"] is None and len(rows) == 2


def test_eligible_needs_a_judged_faithfulness_at_the_floor() -> None:
    assert bake.eligible(0.6, 0.6) and not bake.eligible(0.59, 0.6) and not bake.eligible(None, 0.6)


def test_eval_rows_match_the_results_shape() -> None:
    run = {"run_id": "r", "mode": "vector", "variant": "baseline"}
    agg = {
        "em": 0.5,
        "f1": 0.6,
        "recall_at_k": 0.7,
        "faithfulness": 0.8,
        "cost_per_query_usd": 0.001,
        "p50_ms": 100,
        "p95_ms": 200,
        "by_type": {"single_hop": {"f1": 0.9, "recall_at_k": 1.0}},
    }
    rows = bake.eval_rows(run, agg, 0.25, 0.6)
    assert set(rows["routes"][0]) == {
        "run_id",
        "mode",
        "em",
        "f1",
        "recall_at_k",
        "faithfulness",
        "cost_per_query_usd",
        "p50_ms",
        "p95_ms",
    }
    assert rows["by_type"] == [
        {"run_id": "r", "mode": "vector", "type": "single_hop", "f1": 0.9, "recall_at_k": 1.0}
    ]
    assert rows["quality_per_cost"][0]["eligible"] is True
    assert rows["selector"][0]["large_share"] == 0.25


def test_outcome_words() -> None:
    assert replays.outcome(1.0, 1.0, "multi_hop", "multi_hop") == "correct"
    assert replays.outcome(0.0, 0.4, "multi_hop", None) == "partial"
    assert replays.outcome(0.0, 0.0, "multi_hop", None) == "wrong"
    assert replays.outcome(1.0, 1.0, "multi_hop", "single_hop") == "misrouted"


def test_check_set_enforces_the_contract_rules() -> None:
    good = [(t, "correct") for t in ("single_hop", "multi_hop", "comparison") for _ in range(4)]
    good[0], good[1] = ("single_hop", "wrong"), ("single_hop", "misrouted")
    assert replays.check_set(good) == []
    assert replays.check_set(good[:11])[0] == "11 questions, the page needs 12 to 16"
    no_wrong = [(t, "correct") for t, _ in good]
    assert replays.check_set(no_wrong) == ["fewer than 2 questions that went wrong"]
    few_comparisons = (
        [("single_hop", "wrong")] * 6 + [("multi_hop", "x")] * 4 + [("comparison", "x")] * 2
    )
    assert replays.check_set(few_comparisons) == ["comparison: 2 questions, at least 4 needed"]


def test_judgement_shape_and_flag() -> None:
    j = replays.judgement((1.0, 0.5, 1.0, "fine", 0.001), True, 0.6)
    assert j == {
        "faithfulness": 1.0,
        "relevance": 0.5,
        "completeness": 1.0,
        "rationale": "fine",
        "cost_usd": 0.001,
        "flagged": True,
        "queued": True,
    }
    assert replays.judgement(None, False, 0.6) is None
