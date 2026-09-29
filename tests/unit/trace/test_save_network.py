import psycopg
import pytest

from adaptiverag.stores.db import conn
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import LLMResult

pytestmark = pytest.mark.network


def test_save_writes_trace_and_calls_together() -> None:
    t = Trace("network test question", "vector", "cli")
    t.add_llm(LLMResult("", "small", "m", 12, 3, 0.0001, 90, False, False, 0, 0))
    t.add_llm(LLMResult("", "embed", "e", 4, 0, 0.000001, 20, True, True, 0, 0))
    t.set(route_taken="vector", model_selected="small")
    trace_id = t.save()
    with conn() as c:
        total = c.execute(
            "select total_cost_usd from traces where trace_id = %s", (trace_id,)
        ).fetchone()
        calls = c.execute(
            "select sum(cost_usd), count(*) from llm_calls where trace_id = %s", (trace_id,)
        ).fetchone()
        c.execute("delete from traces where trace_id = %s", (trace_id,))
    assert total is not None and calls is not None
    assert total[0] == calls[0] and calls[1] == 2


def test_failed_call_insert_leaves_no_trace_row() -> None:
    t = Trace("network test rollback", "vector", "cli")
    t.add_llm(LLMResult("", "small", None, 1, 1, 0.0, 1, False, False, 0, 0))  # type: ignore[arg-type]
    with pytest.raises(psycopg.errors.NotNullViolation):
        t.save()
    with conn() as c:
        row = c.execute("select count(*) from traces where trace_id = %s", (t.trace_id,)).fetchone()
    assert row == (0,)
