from decimal import Decimal
from typing import Any

import pytest

from adaptiverag.telemetry.aggregate import group_stats, quality_per_cost, selector, summarize


def result(
    run: str,
    qtype: str,
    route: str,
    cost: str | None,
    judge: str,
    ms: int | None,
    f1: float,
    faith: float | None,
) -> dict[str, Any]:
    return {
        "run_id": run,
        "split": "dev",
        "mode": "auto",
        "variant": "v",
        "question_id": f"{qtype}{ms}",
        "gold_type": qtype,
        "route_taken": route,
        "em": 0.0,
        "f1": f1,
        "recall_at_k": 1.0,
        "faithfulness": faith,
        "total_cost_usd": None if cost is None else Decimal(cost),
        "eval_cost_usd": Decimal(judge),
        "total_latency_ms": ms,
        "model_selected": "m",
    }


ROWS = [
    result("r1", "single_hop", "vector", "0.0010", "0.0004", 100, 1.0, 0.9),
    result("r1", "single_hop", "vector", "0.0020", "0.0004", 300, 0.5, None),
    result("r1", "multi_hop", "graph", "0.0050", "0.0010", 900, 0.0, 0.4),
    result("r1", "multi_hop", "hybrid", None, "0", None, 0.2, None),
]


def test_cost_per_query_leaves_out_the_judge() -> None:
    stats = group_stats(ROWS[:2])
    assert stats["cost_per_query_usd"] == pytest.approx(0.0011)
    assert stats["judge_cost_per_query_usd"] == pytest.approx(0.0004)


def test_latency_percentiles_and_quality_means() -> None:
    stats = group_stats(ROWS[:3])
    assert stats["p50_ms"] == 300 and stats["p95_ms"] == pytest.approx(840)
    assert stats["f1"] == pytest.approx(0.5)
    assert stats["faithfulness"] == pytest.approx(0.65)  # only judged answers count


def test_results_without_a_trace_are_counted_not_averaged() -> None:
    stats = group_stats(ROWS)
    assert stats["n"] == 4 and stats["n_without_trace"] == 1
    assert stats["cost_per_query_usd"] == pytest.approx((0.0006 + 0.0016 + 0.0040) / 3)


def test_summary_groups_by_type_and_by_route() -> None:
    s = summarize(ROWS)
    assert s["runs"]["r1"]["n"] == 4 and s["runs"]["r1"]["variant"] == "v"
    assert [(g["gold_type"], g["n"]) for g in s["by_type"]] == [("single_hop", 2), ("multi_hop", 2)]
    assert [(g["route_taken"], g["n"]) for g in s["by_route"]] == [
        ("vector", 2),
        ("graph", 1),
        ("hybrid", 1),
    ]
    hybrid = s["by_route"][2]
    assert hybrid["cost_per_query_usd"] is None and hybrid["p50_ms"] is None


def test_runs_stay_apart() -> None:
    rows = ROWS[:1] + [result("r2", "single_hop", "vector", "0.0100", "0", 50, 1.0, None)]
    by_type = summarize(rows)["by_type"]
    assert [(g["run_id"], g["cost_per_query_usd"]) for g in by_type] == [
        ("r1", pytest.approx(0.0006)),
        ("r2", pytest.approx(0.01)),
    ]


def test_quality_per_cost_applies_the_faithfulness_floor() -> None:
    runs = {
        "cheap": {
            "variant": "always-small",
            "f1": 0.5,
            "faithfulness": 0.55,
            "cost_per_query_usd": 0.0001,
        },
        "good": {
            "variant": "selector",
            "f1": 0.6,
            "faithfulness": 0.8,
            "cost_per_query_usd": 0.0003,
        },
        "unjudged": {
            "variant": "always-large",
            "f1": 0.7,
            "faithfulness": None,
            "cost_per_query_usd": 0.001,
        },
    }
    rows = {r["run_id"]: r for r in quality_per_cost(runs, 0.6)}
    assert (
        rows["cheap"]["eligible"] is False and rows["cheap"]["why_not"] == "faithfulness under 0.6"
    )
    assert rows["good"]["eligible"] is True and rows["good"]["why_not"] == ""
    assert rows["unjudged"]["eligible"] is False and rows["unjudged"]["why_not"] == "not judged"


def test_selector_large_share_counts_only_answered_rows() -> None:
    rows = [
        {
            **result("s", "single_hop", "vector", "0.001", "0", 100, 1.0, None),
            "model_selected": "big",
        },
        {
            **result("s", "multi_hop", "graph", "0.002", "0", 200, 0.0, None),
            "model_selected": "small",
        },
        {
            **result("s", "multi_hop", "graph", "0.003", "0", 300, 0.5, None),
            "model_selected": "big",
        },
        {**result("s", "multi_hop", "graph", None, "0", None, 0.5, None), "model_selected": None},
    ]
    (row,) = selector(rows, "big")
    assert row["large_share"] == pytest.approx(2 / 3)
    assert row["cost_per_query_usd"] == pytest.approx(0.002)
