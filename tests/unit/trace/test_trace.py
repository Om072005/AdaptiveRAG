import time

import pytest

from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import LLMResult, Role


def call(
    role: Role, cost: float, latency: int = 100, cached: bool = False, wait: int = 0
) -> LLMResult:
    return LLMResult("", role, "m", 10, 5, cost, latency, cached, False, 1 if wait else 0, wait)


def test_costs_are_split_by_role_and_summed() -> None:
    t = Trace("q", "auto", "cli")
    for r in [
        call("embed", 0.00001),
        call("classify", 0.0001),
        call("large", 0.002),
        call("judge", 0.003),
    ]:
        t.add_llm(r)
    row = t.row()
    assert row["classifier_cost_usd"] == pytest.approx(0.0001)
    assert row["generation_cost_usd"] == pytest.approx(0.002)
    assert row["eval_cost_usd"] == pytest.approx(0.003)
    assert row["total_cost_usd"] == pytest.approx(0.00511)
    assert (row["tokens_in"], row["tokens_out"]) == (10, 5)  # generation calls only


def test_latency_excludes_throttle_wait_and_counts_cached_originals() -> None:
    t = Trace("q", "vector", "cli")
    t.add_llm(call("small", 0.001, latency=400, cached=True))
    t.add_llm(call("embed", 0.0, latency=50, wait=5_000))
    row = t.row()
    assert row["throttle_wait_ms"] == 5_000
    assert (
        400 <= row["total_latency_ms"] < 1_000
    )  # wall clock is tiny here, the wait is not counted
    assert row["cached"] is False


def test_all_cached_and_empty_ledger() -> None:
    t = Trace("q", "vector", "cli")
    assert t.row()["cached"] is False
    t.add_llm(call("small", 0.001, cached=True))
    assert t.row()["cached"] is True


def test_spans_record_names_and_land_in_detail() -> None:
    t = Trace("q", "vector", "cli")
    with t.span("retrieve"):
        time.sleep(0.01)
    t.set(detail={"answer": "x"})
    detail = t.row()["detail"]
    assert detail["answer"] == "x"
    assert detail["spans"][0]["name"] == "retrieve" and detail["spans"][0]["ms"] >= 10


def test_span_is_recorded_even_when_the_block_raises() -> None:
    t = Trace("q", "vector", "cli")
    with pytest.raises(RuntimeError), t.span("generate"):
        raise RuntimeError("boom")
    assert [s["name"] for s in t.spans] == ["generate"]


def test_set_rejects_unknown_and_computed_columns() -> None:
    t = Trace("q", "vector", "cli")
    with pytest.raises(ValueError):
        t.set(no_such_column=1)
    with pytest.raises(ValueError):
        t.set(total_cost_usd=0)  # computed from the ledger, never set by hand


def test_forced_mode_is_the_default_route_taken() -> None:
    assert Trace("q", "graph", "cli").row()["route_taken"] == "graph"


def test_fifth_call_raises_budget_exceeded() -> None:
    from adaptiverag.llm import BudgetExceeded

    t = Trace("q", "auto", "cli")
    for _ in range(t.max_calls):
        t.add_llm(call("small", 0.001))
    with pytest.raises(BudgetExceeded):
        t.add_llm(call("small", 0.001))
    assert len(t.calls) == 4
