"""POST /api/query: input validation, error shape and the QueryResponse body."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from adaptiverag import server
from adaptiverag.llm import RateLimited
from adaptiverag.serialize import QueryResponse, to_response

from .test_query_response import result

client = TestClient(server.app)


@pytest.fixture
def fake_pipeline(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []
    stored = to_response(result(), "What is the capital?")

    def answer(question: str, mode: str, source: str) -> Any:
        calls.append((question, mode, source))
        return result()

    monkeypatch.setattr(server, "answer_query", answer)
    monkeypatch.setattr(server, "response_from_trace", lambda trace_id: stored)
    return calls


def test_two_char_question_is_a_400_with_the_field(fake_pipeline: list[tuple[Any, ...]]) -> None:
    r = client.post("/api/query", json={"question": "hi", "mode": "vector"})
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["message"] == "Invalid request"
    assert "question" in body["error"]["fields"]
    assert fake_pipeline == []


def test_unknown_mode_is_a_400(fake_pipeline: list[tuple[Any, ...]]) -> None:
    r = client.post("/api/query", json={"question": "What is the capital?", "mode": "web"})
    assert r.status_code == 400 and "mode" in r.json()["error"]["fields"]


def test_valid_question_returns_the_stored_query_response(
    fake_pipeline: list[tuple[Any, ...]],
) -> None:
    r = client.post("/api/query", json={"question": "  What is the capital?  "})
    assert r.status_code == 200
    QueryResponse.model_validate(r.json())
    assert fake_pipeline == [("What is the capital?", "auto", "demo")]


def test_rate_limited_is_a_503_with_replay_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    def limited(*a: Any, **kw: Any) -> Any:
        raise RateLimited("daily quota used up")

    monkeypatch.setattr(server, "answer_query", limited)
    r = client.post("/api/query", json={"question": "What is the capital?"})
    assert r.status_code == 503
    assert r.json()["replay_suggested"] is None and "quota" in r.json()["error"]["message"]
