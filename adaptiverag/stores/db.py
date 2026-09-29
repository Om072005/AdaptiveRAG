"""Postgres connections on the pooled Neon URL, with pgvector types registered."""

from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from adaptiverag.config import ConfigError, settings


def conn() -> psycopg.Connection[Any]:
    """Open a connection on DATABASE_URL (pooled). Autocommit off; use it as a context manager."""
    url = settings().database_url
    if not url:
        raise ConfigError("DATABASE_URL is not set (see .env.example)")
    # The pooler runs in transaction mode, so server side prepared statements are turned off.
    c = psycopg.connect(url, autocommit=False, prepare_threshold=None)
    register_vector(c)
    return c
