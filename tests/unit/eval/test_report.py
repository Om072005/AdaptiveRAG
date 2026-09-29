from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from adaptiverag.eval import report


def row(qtype: str, f1: float, faith: float | None, ms: int) -> dict[str, Any]:
    return {
        "gold_type": qtype,
        "em": float(f1 == 1.0),
        "f1": f1,
        "recall_at_k": 1.0,
        "mrr": 0.5,
        "sp_precision": None,
        "faithfulness": faith,
        "relevance": faith,
        "completeness": faith,
        "cost_usd": Decimal("0.002"),
        "latency_ms": ms,
    }


NEW = [
    row("multi_hop", 1.0, 1.0, 100),
    row("multi_hop", 0.5, None, 300),
    row("comparison", 0.0, 0.5, 200),
]
OLD = [row("multi_hop", 0.5, 0.5, 100), row("single_hop", 1.0, 1.0, 100)]
RUN = {
    "run_id": "20261003-1405-dev-vector-baseline",
    "split": "dev",
    "mode": "vector",
    "variant": "baseline",
    "git_sha": "abcdef1234567890",
    "git_dirty": False,
    "config_hash": "1a723a189a8d",
    "n": 3,
    "created_at": datetime(2026, 10, 3),
}


def test_percentile_is_nearest_rank() -> None:
    assert report.percentile([], 50) is None
    assert report.percentile([300, 100, 200], 50) == 200
    assert report.percentile([float(i) for i in range(1, 101)], 95) == 95
    assert report.percentile([5.0], 95) == 5.0


def test_aggregate_skips_unscored_rows_per_metric() -> None:
    agg = report.aggregate(NEW)
    assert agg["n"] == 3 and agg["f1"] == pytest.approx(0.5)
    assert agg["faithfulness"] == pytest.approx(0.75)
    assert agg["sp_precision"] is None
    assert agg["cost_per_query_usd"] == pytest.approx(0.002)
    assert agg["p50_ms"] == 200 and agg["p95_ms"] == 300
    assert list(agg["by_type"]) == ["multi_hop", "comparison"]
    assert agg["by_type"]["multi_hop"]["f1"] == 0.75 and agg["by_type"]["multi_hop"]["n"] == 2


def test_diff_is_new_minus_old_on_shared_types_only() -> None:
    d = report.diff(report.aggregate(NEW), report.aggregate(OLD))
    assert d["overall"]["f1"] == pytest.approx(0.5 - 0.75)
    assert d["overall"]["sp_precision"] is None
    assert list(d["by_type"]) == ["multi_hop"]
    assert d["by_type"]["multi_hop"]["f1"] == pytest.approx(0.25)


def test_render_shows_provenance_and_changes() -> None:
    old_run = {**RUN, "run_id": "20261002-0900-dev-vector-baseline"}
    md = report.render_md(
        RUN, report.aggregate(NEW), {"run": old_run, "aggregate": report.aggregate(OLD)}
    )
    assert md.startswith("# 20261003-1405-dev-vector-baseline\n")
    assert "git `abcdef123456`" in md and "config `1a723a189a8d`" in md and "3 of 3" in md
    assert "Compared with: `20261002-0900-dev-vector-baseline`" in md
    assert "| f1 | 0.500 | -0.250 |" in md
    assert "| multi_hop | 2 | 0.500 | 0.750 | 1.000 | 1.000 | +0.250 |" in md
    assert "| comparison | 1 |" in md


def test_render_without_a_previous_run() -> None:
    md = report.render_md(RUN, report.aggregate(NEW), None)
    assert "no earlier comparable run" in md and "| f1 | 0.500 |  |" in md
