"""llm_cache reads and writes. Rows keep the original tokens and latency of the uncached call."""

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from adaptiverag.config import ConfigError, settings

_conn: psycopg.Connection[Any] | None = None


def _connection() -> psycopg.Connection[Any]:
    # One long lived autocommit connection: a cache lookup should not pay for a new TLS handshake.
    global _conn
    if _conn is None or _conn.closed:
        url = settings().database_url
        if not url:
            raise ConfigError("DATABASE_URL is not set (see .env.example)")
        _conn = psycopg.connect(url, autocommit=True, prepare_threshold=None)
    return _conn


def _run(sql: str, params: Any = None, many: bool = False) -> list[tuple[Any, ...]]:
    """Execute once, reconnecting a single time if Neon dropped the idle connection."""
    global _conn
    for attempt in range(2):
        try:
            c = _connection()
            if many:
                with c.cursor() as cur:
                    cur.executemany(sql, params)
                return []
            cur = c.execute(sql, params)
            return cur.fetchall() if cur.description else []
        except psycopg.OperationalError:
            _conn = None
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
