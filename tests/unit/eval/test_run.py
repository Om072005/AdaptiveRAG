from datetime import datetime

import pytest

from adaptiverag.eval import run
from adaptiverag.eval.gold import GoldItem
from tests.unit.eval.fakes import TRACE_ID, fake_result

ITEM = GoldItem(
    "hp_1", "q?", "Globex", "multi_hop", "dev", ["A", "B"], [("A", 0), ("B", 1)], "hotpotqa"
)


def test_run_id_format() -> None:
    assert run.make_run_id(datetime(2026, 10, 3, 14, 5), "dev", "auto", "baseline") == (
        "20261003-1405-dev-auto-baseline"
    )


def test_check_args_locks_test_split_and_size_variants() -> None:
    with pytest.raises(SystemExit, match="locked"):
        run.check_args("test", "baseline", None, allow_test=False)
    run.check_args("test", "baseline", None, allow_test=True)
    with pytest.raises(SystemExit, match="--size small"):
        run.check_args("dev", "always-small", "large", allow_test=False)
    run.check_args("dev", "always-small", "small", allow_test=False)
    run.check_args("dev", "selector", None, allow_test=False)


def test_test_split_refused_by_cli_without_allow_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_TEST", "0")
    with pytest.raises(SystemExit, match="locked"):
        run.main(["--split", "test", "--mode", "vector", "--variant", "baseline"])


def test_chunk_spans_clip_to_chunk_and_drop_non_overlapping() -> None:
    chunks = {
        "d1:fixed:0": ("d1", 0, 50),
        "d1:fixed:1": ("d1", 40, 90),
        "d2:fixed:0": ("d2", 0, 30),
    }
    spans = run.chunk_spans([("d1", 30, 60), ("d1", 95, 99)], chunks)
    assert spans == [("d1:fixed:0", 30, 50), ("d1:fixed:1", 0, 20)]


def test_score_builds_an_eval_results_row() -> None:
    result = fake_result("the Globex", ["C", "A", "B"])
    row = run.score(ITEM, result, [("A:sentence:0", 0, 10)], k=2)
    assert row["em"] == 1.0 and row["f1"] == 1.0
    assert row["recall_at_k"] == 0.5 and row["mrr"] == 0.5
    assert row["sp_precision"] == 10 / 60
    assert row["predicted_type"] == "multi_hop" and row["route_taken"] == "hybrid"
    assert row["cost_usd"] == 0.002 and row["latency_ms"] == 120 and row["trace_id"] == TRACE_ID


def test_summarize_means_overall_and_by_type() -> None:
    rows = [
        {
            "gold_type": "multi_hop",
            "em": 1.0,
            "f1": 1.0,
            "recall_at_k": 1.0,
            "mrr": 1.0,
            "sp_precision": 0.5,
            "cost_usd": 0.002,
        },
        {
            "gold_type": "comparison",
            "em": 0.0,
            "f1": 0.5,
            "recall_at_k": 0.5,
            "mrr": 0.0,
            "sp_precision": 0.1,
            "cost_usd": 0.004,
        },
    ]
    s = run.summarize(rows)
    assert s["n_done"] == 2 and s["f1"] == 0.75 and s["cost_usd"] == pytest.approx(0.003)
    assert s["by_type"]["comparison"] == {
        "n": 1,
        "em": 0.0,
        "f1": 0.5,
        "recall_at_k": 0.5,
        "mrr": 0.0,
        "sp_precision": 0.1,
    }
    assert run.summarize([]) == {"n_done": 0}
