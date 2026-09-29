from collections.abc import Callable, Iterator

import httpx
import pytest

from adaptiverag import llm

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def fake_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Callable[[Handler], list[httpx.Request]]]:
    """Route every provider call to a handler; returns the list of requests it saw."""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setattr(llm, "_sleep", lambda s: None)
    monkeypatch.setattr(llm, "_no_reasoning_effort", set())
    seen: list[httpx.Request] = []

    def install(handler: Handler) -> list[httpx.Request]:
        def record(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        monkeypatch.setattr(llm, "_client", httpx.Client(transport=httpx.MockTransport(record)))
        return seen

    yield install
