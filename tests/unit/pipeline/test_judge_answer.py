"""judge_answer: judged once, stored, queued when low; a second call makes no model call."""

from typing import Any

import pytest

from adaptiverag import pipeline
from adaptiverag.serialize import to_response


class FakeConn:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def __enter__(self) -> "FakeConn":
        return self

    def __exit__(self, *a: Any) -> None:
        pass

    def execute(self, q: str, params: Any = None) -> Any:
        self.sql.append(q)


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, query_result: Any) -> dict[str, Any]:
    state: dict[str, Any] = {"judgement": None, "judge_calls": 0, "queued": [], "conn": FakeConn()}
    response = to_response(query_result, "What is the capital?")

    def read(trace_id: str) -> dict[str, Any] | None:
        return state["judgement"]

    def fake_judge(question: str, answer: Any, retrieved: Any, trace: Any) -> dict[str, Any]:
        state["judge_calls"] += 1
        state["seen"] = (answer, retrieved)
        return {
            "faithfulness": 0.25,
            "relevance": 1.0,
            "completeness": 0.75,
            "rationale": "one claim unsupported",
            "model": "judge-model",
            "cost_usd": 0.0004,
        }

    def store(c: Any, trace_id: str, verdict: dict[str, Any], judge_trace: Any) -> None:
        state["judgement"] = {
            **{
                k: verdict[k]
                for k in ("faithfulness", "relevance", "completeness", "rationale", "cost_usd")
            },
            "queued": False,
        }

    def queue(c: Any, trace_id: str, reasons: list[tuple[str, str, float]]) -> int:
        state["queued"] += reasons
        if reasons and state["judgement"]:
            state["judgement"]["queued"] = True
        return len(reasons)

    monkeypatch.setattr(pipeline, "read_judgement", read)
    monkeypatch.setattr(pipeline, "response_from_trace", lambda tid: response)
    monkeypatch.setattr(pipeline, "chunk_texts", lambda ids: {i: f"full text of {i}" for i in ids})
    monkeypatch.setattr(pipeline.judge, "judge", fake_judge)
    monkeypatch.setattr(pipeline, "store_judgement", store)
    monkeypatch.setattr(pipeline, "queue_review", queue)
    monkeypatch.setattr(pipeline, "conn", lambda: state["conn"])
    return state


def test_first_call_judges_stores_and_queues_low_scores(world: dict[str, Any]) -> None:
    out = pipeline.judge_answer("t-1")
    assert world["judge_calls"] == 1
    assert out["flagged"] is True and out["queued"] is True and out["cost_usd"] == 0.0004
    assert world["queued"] == [("judge_below_threshold", "faithfulness", 0.25)]
    assert any("flagged = true" in q for q in world["conn"].sql)


def test_second_call_returns_the_stored_judgement_without_a_model_call(
    world: dict[str, Any],
) -> None:
    first = pipeline.judge_answer("t-1")
    second = pipeline.judge_answer("t-1")
    assert world["judge_calls"] == 1 and second == first


def test_judge_sees_full_chunk_texts_and_graph_facts(world: dict[str, Any]) -> None:
    pipeline.judge_answer("t-1")
    answer, retrieved = world["seen"]
    assert retrieved.hits[0].text.startswith("full text of")
    assert retrieved.paths and retrieved.paths[0].edges[0].subject_name == "Istanbul"
    assert answer.text.startswith("Ankara")


def test_a_missing_judge_model_says_how_to_get_it(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from adaptiverag.config import models
    from adaptiverag.eval.judge import JudgeFailed

    monkeypatch.setattr(pipeline.llm, "missing", lambda spec: spec.role == "judge")
    name = models()["judge"].model
    with pytest.raises(JudgeFailed, match=f"ollama pull {name}"):
        pipeline.judge_answer("t-1")
    assert world["judge_calls"] == 0
