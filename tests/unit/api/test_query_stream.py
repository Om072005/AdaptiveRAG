import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from adaptiverag import server
from adaptiverag.llm import RateLimited
from adaptiverag.telemetry.trace import Listener

client = TestClient(server.app)
STORED = {"trace_id": "t-1", "answer": {"short": "Paris"}}


class Done:
    trace_id = "t-1"


def events(r: Any) -> list[dict[str, Any]]:
    return [json.loads(line) for line in r.text.splitlines() if line]


def test_steps_and_pieces_stream_before_the_full_response(monkeypatch: pytest.MonkeyPatch) -> None:
    def answer(question: str, mode: str, source: str, listener: Listener) -> Done:
        assert (question, mode, source) == ("What is the capital?", "vector", "demo")
        listener({"type": "step", "step": "embed", "at_ms": 3})
        listener({"type": "delta", "kind": "thinking", "text": "France..."})
        listener({"type": "delta", "kind": "answer", "text": "Answer: Paris"})
        return Done()

    monkeypatch.setattr(server, "answer_query", answer)
    monkeypatch.setattr(server, "response_from_trace", lambda trace_id: STORED)
    r = client.post(
        "/api/query/stream", json={"question": " What is the capital? ", "mode": "vector"}
    )
    assert r.status_code == 200 and r.headers["content-type"] == "application/x-ndjson"
    assert [e["type"] for e in events(r)] == ["step", "delta", "delta", "done"]
    assert events(r)[-1]["response"] == STORED


def test_a_busy_model_ends_the_stream_with_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def answer(question: str, mode: str, source: str, listener: Listener) -> Done:
        listener({"type": "step", "step": "embed", "at_ms": 3})
        raise RateLimited("gpt-oss:20b: provider busy (503), resume later")

    monkeypatch.setattr(server, "answer_query", answer)
    out = events(client.post("/api/query/stream", json={"question": "What is it?"}))
    assert out[-1] == {"type": "error", "message": "gpt-oss:20b: provider busy (503), resume later"}


def test_an_unexpected_failure_does_not_leak_details(monkeypatch: pytest.MonkeyPatch) -> None:
    def answer(question: str, mode: str, source: str, listener: Listener) -> Done:
        raise RuntimeError("password=secret in a connection string")

    monkeypatch.setattr(server, "answer_query", answer)
    out = events(client.post("/api/query/stream", json={"question": "What is it?"}))
    assert out == [{"type": "error", "message": "the query failed, see the API log"}]


def test_stream_validates_like_the_plain_endpoint() -> None:
    r = client.post("/api/query/stream", json={"question": "hi"})
    assert r.status_code == 400 and "question" in r.json()["error"]["fields"]


def test_a_refused_model_request_does_not_pass_on_the_server_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from adaptiverag.llm import ProviderError

    def answer(question: str, mode: str, source: str, listener: Listener) -> Done:
        raise ProviderError("gpt-oss:20b: 400 internal path C:/models/blob")

    monkeypatch.setattr(server, "answer_query", answer)
    out = events(client.post("/api/query/stream", json={"question": "What is it?"}))
    assert out == [
        {"type": "error", "message": "the model server refused the request, see the API log"}
    ]


def test_the_worker_stops_at_its_next_step_once_the_page_has_gone() -> None:
    import queue
    import threading

    gone = threading.Event()
    gone.set()
    reached: list[str] = []

    def answer(question: str, mode: str, source: str, listener: Listener) -> Done:
        listener({"type": "step", "step": "embed", "at_ms": 1})
        reached.append("after the first step")
        return Done()

    q: queue.Queue[dict[str, Any] | None] = queue.Queue()
    with pytest.MonkeyPatch.context() as m:
        m.setattr(server, "answer_query", answer)
        server.run_live(server.QueryIn(question="What is it?"), q, gone)
    assert reached == [] and q.get_nowait() is None
