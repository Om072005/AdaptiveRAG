"""Postgres connections on the pooled Neon URL, with pgvector types registered."""

from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from adaptiverag.config import ConfigError, settings

_shared: psycopg.Connection[Any] | None = None


def conn() -> psycopg.Connection[Any]:
    """Open a connection on DATABASE_URL (pooled). Autocommit off; use it as a context manager."""
    url = settings().database_url
    if not url:
        raise ConfigError("DATABASE_URL is not set (see .env.example)")
    # The pooler runs in transaction mode, so server side prepared statements are turned off.
    c = psycopg.connect(url, autocommit=False, prepare_threshold=None)
    register_vector(c)
    return c


def shared() -> psycopg.Connection[Any]:
    """One long lived autocommit connection for reads on the query path.

    Opening a Neon connection costs a TLS handshake, which would otherwise land inside
    retrieval latency on every query. Reconnects if the last one was closed or broke.
    """
    global _shared
    if _shared is None or _shared.closed or _shared.broken:
        _shared = conn()
        _shared.autocommit = True
    return _shared


def reset_shared() -> None:
    """Drop the shared connection, for example after Neon closed it while idle."""
    global _shared
    if _shared is not None and not _shared.closed:
        _shared.close()
    _shared = None
