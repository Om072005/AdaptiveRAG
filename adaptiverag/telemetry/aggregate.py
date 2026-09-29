"""Economics of stored eval runs: cost and latency per query type and per route.

Cost is list price and latency is the original call latency, as the traces store them, so a rerun
answered from the cache never looks cheaper or faster. Cost per query leaves out the judge: it is
the cost of answering, and the judge's cost is reported next to it.
"""

from typing import Any

import numpy as np

from adaptiverag.stores import econ


def group_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """n, mean answer cost, mean judge cost, p50 and p95 latency, mean F1 and faithfulness."""
    traced = [
        r for r in rows if r["total_cost_usd"] is not None and r["total_latency_ms"] is not None
    ]
    judged = [r["faithfulness"] for r in rows if r["faithfulness"] is not None]
    answer_cost = [float(r["total_cost_usd"]) - float(r["eval_cost_usd"] or 0) for r in traced]
    latency = [r["total_latency_ms"] for r in traced]
    return {
        "n": len(rows),
        "n_without_trace": len(rows) - len(traced),
        "cost_per_query_usd": float(np.mean(answer_cost)) if traced else None,
        "judge_cost_per_query_usd": (
            float(np.mean([float(r["eval_cost_usd"] or 0) for r in traced])) if traced else None
        ),
        "p50_ms": float(np.percentile(latency, 50)) if traced else None,
        "p95_ms": float(np.percentile(latency, 95)) if traced else None,
        "f1": float(np.mean([r["f1"] for r in rows])) if rows else None,
        "faithfulness": float(np.mean(judged)) if judged else None,
    }


def grouped(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """One stats row per (run_id, value of key), in first seen order."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault((r["run_id"], r[key]), []).append(r)
    return [{"run_id": run, key: value, **group_stats(g)} for (run, value), g in groups.items()]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per run totals, then the same numbers per gold query type and per route taken."""
    runs: dict[str, dict[str, Any]] = {}
    for r in rows:
        runs.setdefault(r["run_id"], {k: r[k] for k in ("split", "mode", "variant")})
    by_run = {
        run: {**meta, **group_stats([r for r in rows if r["run_id"] == run])}
        for run, meta in runs.items()
    }
    return {
        "runs": by_run,
        "by_type": grouped(rows, "gold_type"),
        "by_route": grouped(rows, "route_taken"),
    }


def economics(run_ids: list[str]) -> dict[str, Any]:
    """Cost and latency per type, per route, and quality per unit cost."""
    return summarize(econ.result_rows(run_ids))
