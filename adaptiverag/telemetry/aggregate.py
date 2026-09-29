"""Economics of stored eval runs: cost and latency per query type and per route, quality per cost.

Cost is list price and latency is the original call latency, as the traces store them, so a rerun
answered from the cache never looks cheaper or faster. Cost per query leaves out the judge: it is
the cost of answering, and the judge's cost is reported next to it. A run whose mean faithfulness
is under judge.flag_below is not eligible, whatever it costs (README: a cheaper route that drops
faithfulness below the threshold is not a win); a run with no judged answers is not eligible either.
"""

from typing import Any

import numpy as np

from adaptiverag.config import models, router_cfg
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


def quality_per_cost(runs: dict[str, dict[str, Any]], floor: float) -> list[dict[str, Any]]:
    """One row per run: F1, faithfulness, cost per query and whether it clears the floor."""
    out = []
    for run_id, r in runs.items():
        faith = r["faithfulness"]
        eligible = faith is not None and faith >= floor
        why = "" if eligible else ("not judged" if faith is None else f"faithfulness under {floor}")
        out.append(
            {
                "run_id": run_id,
                "variant": r["variant"],
                "f1": r["f1"],
                "faithfulness": faith,
                "cost_per_query_usd": r["cost_per_query_usd"],
                "eligible": eligible,
                "why_not": why,
            }
        )
    return out


def selector(rows: list[dict[str, Any]], large_model: str) -> list[dict[str, Any]]:
    """Per run: F1, cost per query and the share of answers the large model wrote."""
    out = []
    for run_id in dict.fromkeys(r["run_id"] for r in rows):
        mine = [r for r in rows if r["run_id"] == run_id]
        chosen = [r["model_selected"] for r in mine if r["model_selected"] is not None]
        stats = group_stats(mine)
        out.append(
            {
                "run_id": run_id,
                "variant": mine[0]["variant"],
                "f1": stats["f1"],
                "cost_per_query_usd": stats["cost_per_query_usd"],
                "large_share": sum(m == large_model for m in chosen) / len(chosen)
                if chosen
                else None,
            }
        )
    return out


def economics(run_ids: list[str]) -> dict[str, Any]:
    """Cost and latency per type, per route, and quality per unit cost."""
    rows = econ.result_rows(run_ids)
    summary = summarize(rows)
    floor = float(router_cfg()["judge"]["flag_below"])
    return {
        **summary,
        "quality_per_cost": quality_per_cost(summary["runs"], floor),
        "selector": selector(rows, models()["large"].model),
        "faithfulness_floor": floor,
    }
