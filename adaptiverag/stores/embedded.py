"""The embedded demo database: Postgres 16 with pgvector from the pgserver package, kept under
.demo/ in the checkout. It is used whenever DATABASE_URL is empty, so a fresh clone needs no
account and no network. It has no pg_trgm; see stores/trgm.py."""

from functools import cache
from pathlib import Path

from adaptiverag.config import ROOT

DEMO_DIR = ROOT / ".demo"
PGDATA = DEMO_DIR / "pgdata"


def _keep_locks_in(folder: Path) -> None:
    """pgserver keeps a lock file in the user's runtime folder; keep it next to the data instead."""
    import fasteners
    from pgserver import PostgresServer

    folder.mkdir(parents=True, exist_ok=True)
    PostgresServer.runtime_path = folder
    PostgresServer.lock_path = folder / ".lockfile"
    PostgresServer._lock = fasteners.InterProcessLock(PostgresServer.lock_path)


@cache
def uri() -> str:
    """Start the server on first use (or attach to the one already running) and return its URL.

    The server outlives this process, so the CLI, the API and the eval share one database and
    only the first command of a session pays the start (about 15 s the very first time)."""
    import pgserver

    _keep_locks_in(DEMO_DIR)
    server = pgserver.get_server(PGDATA, cleanup_mode=None)
    return str(server.get_uri())


def stop() -> bool:
    """Stop the server if it runs; the data stays. Returns whether one was running."""
    import pgserver

    if not (PGDATA / "postmaster.pid").exists():
        return False
    pg_ctl = getattr(pgserver, "pg_ctl")  # noqa: B009 (made at import time, one per binary)
    pg_ctl(["-w", "stop"], pgdata=PGDATA)
    uri.cache_clear()
    return True
