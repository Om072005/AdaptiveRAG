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
    clock = {"t": 1000.0}

    def fake_sleep(s: float) -> None:  # time passes instantly, so pacing never really waits
        clock["t"] += s

    monkeypatch.setattr(llm, "_sleep", fake_sleep)
    monkeypatch.setattr(llm, "_now", lambda: clock["t"])
    monkeypatch.setattr(llm, "_sent", [])
    monkeypatch.setattr(llm, "_no_reasoning_effort", set())
    monkeypatch.setattr(llm, "use_cache", False)
    seen: list[httpx.Request] = []

    def install(handler: Handler) -> list[httpx.Request]:
        def record(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        monkeypatch.setattr(llm, "_client", httpx.Client(transport=httpx.MockTransport(record)))
        return seen

    yield install


@pytest.fixture
def memory_cache(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, object]]:
    """Turn the cache on, backed by a dict instead of Postgres."""
    store: dict[str, dict[str, object]] = {}

    def get_many(keys: list[str]) -> dict[str, dict[str, object]]:
        return {k: store[k] for k in keys if k in store}

    def put_many(rows: list[dict[str, object]]) -> None:
        for row in rows:
            store.setdefault(str(row["key"]), row)

    monkeypatch.setattr(llm, "use_cache", True)
    monkeypatch.setattr(llm.cache, "get_many", get_many)
    monkeypatch.setattr(llm.cache, "put_many", put_many)
    return store
