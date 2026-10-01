"""Apply db/migrations/*.sql in order, once each. Run: python -m adaptiverag.stores.migrate"""

from pathlib import Path
from typing import Any

import psycopg

from adaptiverag.config import ROOT, ConfigError, settings
from adaptiverag.stores import db

MIGRATIONS_DIR = ROOT / "db" / "migrations"
BOOTSTRAP = (
    "create table if not exists schema_migrations "
    "(version text primary key, applied_at timestamptz not null default now())"
)


def migration_files(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """Every .sql file in the migrations folder, in name order (0001_, 0002_, ...)."""
    return sorted(directory.glob("*.sql"), key=lambda p: p.name)


def pending(files: list[Path], applied: set[str]) -> list[Path]:
    """Files whose version (file name without .sql) is not recorded yet."""
    return [f for f in files if f.stem not in applied]


def without_trgm(sql: str) -> str:
    """The migration minus its pg_trgm lines (the extension and the alias trigram index).

    The embedded demo database has no pg_trgm; the graph store then computes word similarity in
    Python (stores/trgm.py) and needs neither."""
    return "".join(
        line
        for line in sql.splitlines(keepends=True)
        if "pg_trgm" not in line and "gin_trgm_ops" not in line
    )


def trgm_available(c: psycopg.Connection[Any]) -> bool:
    row = c.execute(
        "select count(*) from pg_available_extensions where name = 'pg_trgm'"
    ).fetchone()
    return bool(row and row[0])


def apply(url: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations, each in its own transaction. Returns the versions applied."""
    done: list[str] = []
    with psycopg.connect(url, autocommit=True) as c:
        c.execute(BOOTSTRAP)
        applied = {row[0] for row in c.execute("select version from schema_migrations")}
        trgm = trgm_available(c)
        for f in pending(migration_files(directory), applied):
            sql = f.read_text(encoding="utf-8")
            with c.transaction():
                c.execute(sql if trgm else without_trgm(sql))
                c.execute("insert into schema_migrations (version) values (%s)", (f.stem,))
            done.append(f.stem)
    return done


def main() -> None:
    s = settings()
    if s.database_url == db.EMBEDDED or not (s.database_url or s.database_url_direct):
        url = db.url()  # no database configured: the embedded demo database
    else:
        url = s.database_url_direct
        if not url:
            raise ConfigError("DATABASE_URL_DIRECT is not set (see .env.example)")
    done = apply(url)
    print("applied: " + ", ".join(done) if done else "nothing to apply, schema is up to date")


if __name__ == "__main__":
    main()
