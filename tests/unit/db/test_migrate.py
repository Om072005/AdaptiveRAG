import re
from pathlib import Path

import pytest

from adaptiverag.config import settings
from adaptiverag.stores import migrate


def test_files_are_applied_in_name_order(tmp_path: Path) -> None:
    for name in ["0002_b.sql", "0010_c.sql", "0001_a.sql", "notes.txt"]:
        (tmp_path / name).write_text("select 1;", encoding="utf-8")
    assert [f.name for f in migrate.migration_files(tmp_path)] == [
        "0001_a.sql",
        "0002_b.sql",
        "0010_c.sql",
    ]


def test_pending_skips_applied_versions(tmp_path: Path) -> None:
    files = [tmp_path / "0001_init.sql", tmp_path / "0002_more.sql"]
    assert migrate.pending(files, {"0001_init"}) == [files[1]]
    assert migrate.pending(files, {"0001_init", "0002_more"}) == []


def test_repo_migrations_are_numbered() -> None:
    names = [f.name for f in migrate.migration_files()]
    assert names and names[0] == "0001_init.sql"
    assert all(re.fullmatch(r"\d{4}_[a-z0-9_]+\.sql", n) for n in names)


@pytest.mark.network
def test_second_run_applies_nothing() -> None:
    url = settings().database_url_direct
    if not url:
        pytest.skip("DATABASE_URL_DIRECT not set")
    migrate.apply(url)
    assert migrate.apply(url) == []
