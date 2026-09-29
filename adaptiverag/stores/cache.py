"""llm_cache reads and writes. Rows keep the original tokens and latency of the uncached call."""

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from adaptiverag.stores import db


def _run(sql: str, params: Any = None, many: bool = False) -> list[tuple[Any, ...]]:
    """Execute on the shared connection, reconnecting once if Neon dropped it while idle."""
    for attempt in range(2):
        try:
            c = db.shared()
            if many:
                with c.cursor() as cur:
                    cur.executemany(sql, params)
                return []
            cur = c.execute(sql, params)
            return cur.fetchall() if cur.description else []
        except psycopg.OperationalError:
            db.reset_shared()
            if attempt == 1:
                raise
    return []


def get_many(keys: list[str]) -> dict[str, dict[str, Any]]:
    """Cached rows by key, for the keys that exist."""
    if not keys:
        return {}
    rows = _run(
        "select key, role, model, response, tokens_in, tokens_out, latency_ms "
        "from llm_cache where key = any(%s)",
        (keys,),
    )
    names = ["key", "role", "model", "response", "tokens_in", "tokens_out", "latency_ms"]
    return {row[0]: dict(zip(names, row, strict=True)) for row in rows}


def put_many(rows: list[dict[str, Any]]) -> None:
    """Insert rows; a key that already exists keeps its original values."""
    if not rows:
        return
    _run(
        "insert into llm_cache (key, role, model, response, tokens_in, tokens_out, latency_ms) "
        "values (%s, %s, %s, %s, %s, %s, %s) on conflict (key) do nothing",
        [
            (
                r["key"],
                r["role"],
                r["model"],
                Jsonb(r["response"]),
                r["tokens_in"],
                r["tokens_out"],
                r["latency_ms"],
            )
            for r in rows
        ],
        many=True,
    )
