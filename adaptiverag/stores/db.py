"""Postgres connections on the pooled Neon URL, with pgvector types registered. With no
DATABASE_URL set, the embedded demo database (stores/embedded.py) is used instead."""

import sys
from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from adaptiverag.config import settings

EMBEDDED = "embedded"  # DATABASE_URL value that asks for the embedded database explicitly
_shared: psycopg.Connection[Any] | None = None


def url() -> str:
    """DATABASE_URL, or the embedded demo database's URL when it is empty or 'embedded'."""
    configured = settings().database_url
    if configured and configured != EMBEDDED:
        return configured
    from adaptiverag.stores import embedded

    if not configured and not embedded.uri.cache_info().currsize:
        # said once per process, so a team member whose .env went missing notices at once
        print(
            f"DATABASE_URL is not set: using the embedded demo database in {embedded.PGDATA}",
            file=sys.stderr,
        )
    return embedded.uri()


def conn() -> psycopg.Connection[Any]:
    """Open a connection on DATABASE_URL (pooled). Autocommit off; use it as a context manager."""
    url_ = url()
    # The pooler runs in transaction mode, so server side prepared statements are turned off.
    c = psycopg.connect(url_, autocommit=False, prepare_threshold=None)
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
