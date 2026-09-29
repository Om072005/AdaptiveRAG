import pytest

from adaptiverag.stores.db import conn
from adaptiverag.telemetry.trace import Trace

pytestmark = pytest.mark.network


def test_low_confidence_answer_lands_in_the_review_queue_once() -> None:
    from adaptiverag.stores.traces import queue_review

    t = Trace("network test low confidence", "vector", "cli")
    t.set(route_taken="vector", answer_confidence=0.2, flagged=True)
    tid = t.save()
    try:
        with conn() as c:
            assert queue_review(c, tid, [("answer_confidence_low", "answer_confidence", 0.2)]) == 0
            rows = c.execute(
                "select reason, metric, score, status from review_queue where trace_id = %s", (tid,)
            ).fetchall()
        assert len(rows) == 1 and rows[0][0] == "answer_confidence_low" and rows[0][3] == "open"
    finally:
        with conn() as c:
            c.execute("delete from review_queue where trace_id = %s", (tid,))
            c.execute("delete from traces where trace_id = %s", (tid,))
