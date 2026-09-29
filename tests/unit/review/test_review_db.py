"""review queue against real Postgres, on temp tables that vanish on close."""

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

from adaptiverag.config import settings
from adaptiverag.eval import review

pytestmark = pytest.mark.network
T1, T2 = "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002"


@pytest.fixture
def c() -> Iterator[psycopg.Connection[Any]]:
    url = settings().database_url_direct
    if not url:
        pytest.skip("DATABASE_URL_DIRECT not set")
    conn = psycopg.connect(url)
    for t in ("traces", "eval_results", "review_queue"):
        conn.execute(f"create temp table {t} (like public.{t} including defaults)")
    for tid, conf in [(T1, 0.9), (T2, 0.2)]:
        conn.execute(
            "insert into traces (trace_id, source, question, mode, route_taken, answer_confidence,"
            " classifier_confidence) values (%s, 'eval', %s, 'auto', 'vector', %s, 0.9)",
            (tid, f"question {tid[-1]}", conf),
        )
    for qid, tid, faith, predicted in [
        ("q1", T1, 1.0, "multi_hop"),
        ("q2", T2, 0.25, "single_hop"),
    ]:
        conn.execute(
            "insert into eval_results (run_id, question_id, trace_id, gold_type, predicted_type,"
            " route_taken, em, f1, recall_at_k, mrr, faithfulness, relevance, completeness,"
            " cost_usd, latency_ms) values ('r1', %s, %s, 'multi_hop', %s, 'vector', 0, 0, 0, 0,"
            " %s, 1, 1, 0, 1)",
            (qid, tid, predicted, faith),
        )
    yield conn
    conn.close()


def test_queue_adds_each_reason_once_then_label(c: psycopg.Connection[Any]) -> None:
    assert review.queue_run(c, "r1") == 3  # q2: low faithfulness, low answer confidence, misroute
    assert review.queue_run(c, "r1") == 0
    items = review.list_items(c, "open")
    assert [(i[2], i[3]) for i in items] == [
        ("judge_below_threshold", "faithfulness"),
        ("answer_confidence_low", "answer_confidence"),
        ("misroute", "classifier_confidence"),
    ]
    assert items[0][6] == "question 2"
    review.label(c, items[2][0], "misroute", "dhruv", "classifier said single hop")
    assert len(review.list_items(c, "open")) == 2
    row = c.execute(
        "select status, reviewer, notes, resolved_at is not null from review_queue where id = %s",
        (items[2][0],),
    ).fetchone()
    assert row == ("misroute", "dhruv", "classifier said single hop", True)
    with pytest.raises(SystemExit, match="no review item"):
        review.label(c, 999999999, "ok", "dhruv", None)
