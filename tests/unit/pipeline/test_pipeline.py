from typing import Any

import pytest

from adaptiverag import llm, pipeline
from adaptiverag.generate import answer as answer_mod
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import (
    Classification,
    Hit,
    LLMResult,
    Mode,
    Retrieved,
    RouteDecision,
)

saved: list[dict[str, Any]] = []
routed: list[tuple[str, str]] = []

HITS = [
    Hit(
        "d1:sentence:0",
        "d1",
        "Istanbul",
        "Istanbul is the largest city in Turkey.",
        0.82,
        "vector",
        1,
    ),
    Hit("d2:sentence:0", "d2", "Ankara", "Ankara is the capital of Turkey.", 0.74, "vector", 2),
]


def fake_route(question: str, mode: Mode, trace: Trace) -> tuple[RouteDecision, Retrieved]:
    """Stands in for router.route_and_retrieve: forced modes go as asked, auto classifies."""
    routed.append((question, mode))
    with trace.span("retrieve"):
        trace.set(retrieval_latency_ms=12, n_results=2, top_score=0.82)
    if mode == "auto":
        c = Classification("single_hop", 0.91, {"single_hop": 0.91}, "rules", 0.0, 1)
        decision = RouteDecision(mode, c, "vector", "vector", reasons=["no_relational_structure"])
    else:
        decision = RouteDecision(mode, None, mode, mode, reasons=[f"forced:{mode}"])
    return decision, Retrieved(list(HITS), [], [], 0.82, False, 12)


def fake_chat(role: str, messages: list[dict[str, str]], **kw: Any) -> LLMResult:
    r = LLMResult(
        "Answer: Ankara\nTurkey's capital is Ankara [2][9].",
        role,  # type: ignore[arg-type]
        f"model-{role}",
        900,
        40,
        0.0002,
        350,
        False,
        False,
        0,
        0,
    )
    kw["trace"].add_llm(r)
    return r


@pytest.fixture(autouse=True)
def fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    saved.clear()
    routed.clear()
    monkeypatch.setattr(pipeline, "route_and_retrieve", fake_route)
    monkeypatch.setattr(answer_mod.llm, "chat", fake_chat)
    monkeypatch.setattr(Trace, "save", lambda self: saved.append(self.row()) or self.trace_id)


def test_forced_vector_question_to_cited_answer() -> None:
    r = pipeline.answer_query(
        "What is the capital of the country whose largest city is Istanbul?", "vector"
    )
    assert r.answer.short == "Ankara"
    assert [c.n for c in r.answer.citations] == [2]
    assert r.answer.size == "small" and r.answer.select_reason.startswith("small:")
    assert r.decision.reasons == ["forced:vector"]
    row = saved[0]
    assert row["trace_id"] == r.trace_id
    assert row["route_taken"] == "vector" and row["model_selected"] == "model-small"
    assert row["generation_cost_usd"] == pytest.approx(0.0002) == r.total_cost_usd
    assert row["answer_confidence"] == r.answer.confidence
    assert row["detail"]["citation_errors"] == 1
    assert [s["name"] for s in row["detail"]["spans"]] == ["retrieve", "generate"]


def test_every_mode_goes_through_the_router() -> None:
    for mode in ("auto", "vector", "graph", "hybrid"):
        pipeline.answer_query("q about Ankara", mode)  # type: ignore[arg-type]
    assert [m for _, m in routed] == ["auto", "vector", "graph", "hybrid"]


def test_auto_mode_keeps_the_classification_on_the_response() -> None:
    r = pipeline.answer_query("What is the capital of Turkey?", "auto")
    assert r.decision.classification is not None
    route = saved[0]["detail"]["route"]
    assert (route["label"], route["method"], route["reasons"]) == (
        "single_hop",
        "rules",
        ["no_relational_structure"],
    )


def test_force_size_overrides_the_selector() -> None:
    r = pipeline.answer_query("q about Ankara", "vector", force_size="large")
    assert r.answer.size == "large" and r.answer.select_reason == "forced:large"


def test_graph_route_asks_for_the_large_model() -> None:
    assert pipeline.answer_query("What is the capital of Turkey?", "graph").answer.size == "large"


def test_empty_retrieval_says_not_enough_context_without_a_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def empty(question: str, mode: Mode, trace: Trace) -> tuple[RouteDecision, Retrieved]:
        return RouteDecision(mode, None, "vector", "vector"), Retrieved([], [], [], 0.0, False, 3)

    monkeypatch.setattr(pipeline, "route_and_retrieve", empty)
    r = pipeline.answer_query("q", "vector")
    assert (r.answer.short, r.answer.confidence, r.flagged) == ("not enough context", 0.0, True)
    assert saved[0]["total_cost_usd"] == 0


def test_budget_stop_is_saved_then_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    def over_budget(*a: Any, **kw: Any) -> LLMResult:
        raise llm.BudgetExceeded("cap")

    monkeypatch.setattr(answer_mod.llm, "chat", over_budget)
    with pytest.raises(llm.BudgetExceeded):
        pipeline.answer_query("q", "vector")
    assert saved[0]["detail"]["budget_exceeded"] is True
