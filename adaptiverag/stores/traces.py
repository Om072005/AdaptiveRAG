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


def read_detail(trace_id: str) -> dict[str, Any] | None:
    """traces.detail of one trace (the stored QueryResponse plus notes), or None."""
    row = shared().execute("select detail from traces where trace_id = %s", (trace_id,)).fetchone()
    return dict(row[0]) if row else None
