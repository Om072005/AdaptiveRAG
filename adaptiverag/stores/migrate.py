"""Apply db/migrations/*.sql in order, once each. Run: python -m adaptiverag.stores.migrate"""

from pathlib import Path

import psycopg

from adaptiverag.config import ROOT, ConfigError, settings

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


def apply(url: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations, each in its own transaction. Returns the versions applied."""
    done: list[str] = []
    with psycopg.connect(url, autocommit=True) as c:
        c.execute(BOOTSTRAP)
        applied = {row[0] for row in c.execute("select version from schema_migrations")}
        for f in pending(migration_files(directory), applied):
            with c.transaction():
                c.execute(f.read_text(encoding="utf-8"))
                c.execute("insert into schema_migrations (version) values (%s)", (f.stem,))
            done.append(f.stem)
    return done


def main() -> None:
    url = settings().database_url_direct
    if not url:
        raise ConfigError("DATABASE_URL_DIRECT is not set (see .env.example)")
    done = apply(url)
    print("applied: " + ", ".join(done) if done else "nothing to apply, schema is up to date")


if __name__ == "__main__":
    main()
