"""Reads for the economics report: one row per eval result, joined to its run and its trace."""

from typing import Any

from adaptiverag.stores import db

COLUMNS = [
    "run_id",
    "split",
    "mode",
    "variant",
    "question_id",
    "gold_type",
    "route_taken",
    "em",
    "f1",
    "recall_at_k",
    "faithfulness",
    "total_cost_usd",
    "eval_cost_usd",
    "total_latency_ms",
    "model_selected",
]

# traces hold list price cost and original latency even for cache hits (see telemetry/trace.py)
QUERY = """
select r.run_id, er.split, er.mode, er.variant, r.question_id, r.gold_type, r.route_taken,
       r.em, r.f1, r.recall_at_k, r.faithfulness,
       t.total_cost_usd, t.eval_cost_usd, t.total_latency_ms, t.model_selected
from eval_results r
join eval_runs er on er.run_id = r.run_id
left join traces t on t.trace_id = r.trace_id
where r.run_id = any(%s)
order by r.run_id, r.question_id
"""


def result_rows(run_ids: list[str]) -> list[dict[str, Any]]:
    """Every eval result of these runs with its trace's cost and latency (None if no trace)."""
    with db.conn() as c:
        rows = c.execute(QUERY, (run_ids,)).fetchall()
    return [dict(zip(COLUMNS, r, strict=True)) for r in rows]
