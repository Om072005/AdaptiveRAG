"""eval.run against real Postgres, on temp tables that shadow the real ones and vanish on close."""

import contextlib
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from adaptiverag.config import settings
from adaptiverag.eval import run
from adaptiverag.eval.gold import GoldItem
from adaptiverag.llm import RateLimited
from adaptiverag.types import QueryResult
from tests.unit.eval.fakes import fake_result

pytestmark = pytest.mark.network
TITLES = ["A", "B", "C", "D", "E"]
ITEMS = [
    GoldItem(f"hp_{i}", f"q{i}?", "Globex", "multi_hop", "dev", [t], [(t, 0)], "hotpotqa")
    for i, t in enumerate(TITLES)
]


@pytest.fixture
def c(monkeypatch: pytest.MonkeyPatch) -> Iterator[psycopg.Connection[Any]]:
    url = settings().database_url_direct
    if not url:
        pytest.skip("DATABASE_URL_DIRECT not set")
    conn = psycopg.connect(url)
    for t in ("documents", "chunks", "eval_runs", "eval_results"):
        conn.execute(f"create temp table {t} (like public.{t} including defaults)")
    for t in TITLES:
        conn.execute(
            "insert into documents (doc_id, source, title, text, sentences)"
            " values (%s, 'x', %s, %s, %s)",
            (f"doc_{t}", t, "y" * 40, Jsonb([[0, 20], [21, 40]])),
        )
        conn.execute(
            "insert into chunks (chunk_id, doc_id, strategy, ord, start_offset, end_offset,"
            " text, n_words) values (%s, %s, 'sentence', 0, 0, 20, %s, 1)",
            (f"{t}:sentence:0", f"doc_{t}", "x" * 20),
        )
    monkeypatch.setattr(run, "select_items", lambda split, limit: ITEMS[:limit])
    monkeypatch.setattr(run.db, "conn", lambda: contextlib.nullcontext(conn))
    yield conn
    conn.close()


def answer_failing_after(n: int) -> Any:
    calls = {"n": 0}

    def answer(q: str, mode: str, source: str, force_size: str | None) -> QueryResult:
        calls["n"] += 1
        if calls["n"] > n:
            raise RateLimited("429")
        return fake_result("Globex", [TITLES[int(q[1])]])

    return answer


def test_rate_limited_run_resumes_without_duplicates(c: psycopg.Connection[Any]) -> None:
    args = ["--split", "mini", "--mode", "vector", "--variant", "resume-test", "--limit", "5"]
    with pytest.raises(SystemExit) as stop:
        run.main(args, answer=answer_failing_after(3))
    assert stop.value.code == 2
    (run_id,) = c.execute("select run_id from eval_runs").fetchone() or ("",)
    assert c.execute("select count(*) from eval_results").fetchone() == (3,)

    run.main(["--resume", run_id], answer=answer_failing_after(99))
    ids = [r[0] for r in c.execute("select question_id from eval_results order by 1")]
    assert ids == ["hp_0", "hp_1", "hp_2", "hp_3", "hp_4"]
    summary = c.execute("select summary from eval_runs").fetchone()[0]  # type: ignore[index]
    assert summary["n_done"] == 5 and summary["options"] == {"size": None, "limit": 5}

    run.main(["--resume", run_id], answer=answer_failing_after(0))  # nothing left to answer
    assert c.execute("select count(*) from eval_results").fetchone() == (5,)
