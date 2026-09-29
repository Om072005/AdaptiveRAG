"""traces and llm_calls writes."""

from typing import Any

from psycopg import sql
from psycopg.types.json import Jsonb

from adaptiverag.stores.db import conn, shared

CALL_COLUMNS = [
    "trace_id",
    "role",
    "model",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "latency_ms",
    "cached",
    "estimated",
    "retries",
    "wait_ms",
]


def insert(row: dict[str, Any], calls: list[dict[str, Any]]) -> None:
    """One transaction: the trace row and its call ledger land together or not at all."""
    values = {k: Jsonb(v) if k == "detail" else v for k, v in row.items()}
    trace_sql = sql.SQL("insert into traces ({}) values ({})").format(
        sql.SQL(", ").join(map(sql.Identifier, values)),
        sql.SQL(", ").join(sql.Placeholder() * len(values)),
    )
    call_sql = sql.SQL("insert into llm_calls ({}) values ({})").format(
        sql.SQL(", ").join(map(sql.Identifier, CALL_COLUMNS)),
        sql.SQL(", ").join(sql.Placeholder() * len(CALL_COLUMNS)),
    )
    with conn() as c:
        c.execute(trace_sql, list(values.values()))
        if calls:
            with c.cursor() as cur:
                cur.executemany(call_sql, [[call[k] for k in CALL_COLUMNS] for call in calls])
        if row.get("flagged") and row.get("answer_confidence") is not None:
            queue_review(
                c,
                row["trace_id"],
                [("answer_confidence_low", "answer_confidence", float(row["answer_confidence"]))],
            )


def queue_review(c: Any, trace_id: str, reasons: list[tuple[str, str, float]]) -> int:
    """Open review_queue rows for a trace; a reason already queued for it is not added twice."""
    added = 0
    for reason, metric, score in reasons:
        cur = c.execute(
            "insert into review_queue (trace_id, reason, metric, score) select %s, %s, %s, %s"
            " where not exists (select 1 from review_queue where trace_id = %s and reason = %s"
            " and metric is not distinct from %s)",
            (trace_id, reason, metric, score, trace_id, reason, metric),
        )
        added += cur.rowcount
    return added


def read_detail(trace_id: str) -> dict[str, Any] | None:
    """traces.detail of one trace (the stored QueryResponse plus notes), or None."""
    row = shared().execute("select detail from traces where trace_id = %s", (trace_id,)).fetchone()
    return dict(row[0]) if row else None


def read_judgement(trace_id: str) -> dict[str, Any] | None:
    """The stored judgement of a trace and whether it is queued for review, or None."""
    row = (
        shared()
        .execute(
            "select j.faithfulness, j.relevance, j.completeness, j.rationale, j.cost_usd,"
            " exists (select 1 from review_queue q where q.trace_id = j.trace_id"
            " and q.reason = 'judge_below_threshold')"
            " from judgements j where j.trace_id = %s",
            (trace_id,),
        )
        .fetchone()
    )
    if row is None:
        return None
    keys = ["faithfulness", "relevance", "completeness", "rationale", "cost_usd", "queued"]
    return dict(zip(keys, row, strict=True))


def chunk_texts(chunk_ids: list[str]) -> dict[str, str]:
    """Full text of stored chunks by id (the response only keeps 600 char snippets)."""
    rows = shared().execute(
        "select chunk_id, text from chunks where chunk_id = any(%s)", (chunk_ids,)
    )
    return {cid: text for cid, text in rows.fetchall()}
