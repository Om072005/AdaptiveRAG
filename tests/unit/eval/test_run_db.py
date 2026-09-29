"""eval.run against real Postgres, on temp tables that shadow the real ones and vanish on close."""

import contextlib
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from adaptiverag.config import settings
from adaptiverag.eval import judge, run
from adaptiverag.eval.gold import GoldItem
from adaptiverag.llm import RateLimited
from adaptiverag.types import LLMResult, QueryResult
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
    for t in (
        "documents",
        "chunks",
        "eval_runs",
        "eval_results",
        "traces",
        "llm_calls",
        "judgements",
    ):
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
    assert summary["n_done"] == 5 and summary["options"] == {
        "size": None,
        "limit": 5,
        "judge": False,
    }

    run.main(["--resume", run_id], answer=answer_failing_after(0))  # nothing left to answer
    assert c.execute("select count(*) from eval_results").fetchone() == (5,)


def test_judged_run_stores_scores_ledger_costs_and_failures(
    c: psycopg.Connection[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    replies = iter(
        [
            '{"faithfulness": 5, "relevance": 3, "completeness": 5, "rationale": "fine"}',
            "bad",
            "bad",
        ]
    )

    def fake_chat(role: str, messages: list[dict[str, str]], **kw: Any) -> LLMResult:
        r = LLMResult(next(replies), "judge", "gemini-x", 100, 20, 0.001, 30, False, False, 0, 0)
        kw["trace"].add_llm(r)
        return r

    monkeypatch.setattr(judge.llm, "chat", fake_chat)
    trace_ids = iter([f"00000000-0000-4000-8000-00000000000{n}" for n in (1, 2)])

    def answer(q: str, mode: str, source: str, force_size: str | None) -> QueryResult:
        tid = next(trace_ids)
        c.execute(
            "insert into traces (trace_id, source, question, mode, route_taken, total_cost_usd)"
            " values (%s, 'eval', %s, 'vector', 'vector', 0.002)",
            (tid, q),
        )
        return fake_result("Globex", [TITLES[int(q[1])]], trace_id=tid)

    run.main(
        ["--split", "mini", "--mode", "vector", "--variant", "j", "--limit", "2", "--judge"],
        answer=answer,
    )
    got = c.execute("select question_id, faithfulness, relevance from eval_results order by 1")
    assert got.fetchall() == [("hp_0", 1.0, 0.5), ("hp_1", None, None)]
    assert c.execute("select count(*), sum(cost_usd) from judgements").fetchone() == (
        1,
        Decimal("0.00100000"),
    )
    assert c.execute("select count(*) from llm_calls where role = 'judge'").fetchone() == (1,)
    costs = c.execute(
        "select eval_cost_usd, total_cost_usd from traces order by trace_id"
    ).fetchall()
    assert costs == [(Decimal("0.00100000"), Decimal("0.00300000")), (0, Decimal("0.00200000"))]
    summary = c.execute("select summary from eval_runs").fetchone()[0]  # type: ignore[index]
    assert summary["faithfulness"] == 1.0 and summary["judge_failures"] == ["hp_1"]
