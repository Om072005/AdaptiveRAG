import dataclasses
import json
from collections.abc import Callable

import httpx
import pytest

from adaptiverag import llm
from adaptiverag.config import models

Install = Callable[[Callable[[httpx.Request], httpx.Response]], list[httpx.Request]]


@pytest.fixture
def local_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The embed role pointed at a keyless local server with nomic style prefixes."""
    base = models()
    spec = dataclasses.replace(
        base["embed"],
        provider="ollama",
        model="nomic-embed-text",
        base_url="http://127.0.0.1:11434/v1",
        key_env="",
        price_in_per_m=0.0,
        texts_per_minute=None,
        document_prefix="search_document: ",
        query_prefix="search_query: ",
    )
    monkeypatch.setattr(llm, "models", lambda: {**base, "embed": spec})


def handler(r: httpx.Request) -> httpx.Response:
    texts = json.loads(r.content)["input"]
    data = [{"index": i, "embedding": [1.0] + [0.0] * 767} for i in range(len(texts))]
    return httpx.Response(200, json={"data": data, "usage": {"prompt_tokens": 7 * len(texts)}})


def test_questions_get_the_query_prefix_and_documents_the_document_prefix(
    fake_provider: Install, local_embed: None
) -> None:
    seen = fake_provider(handler)
    llm.embed(["Who founded Acme?"], kind="query")
    llm.embed(["Acme was founded by Jane."])
    assert json.loads(seen[0].content)["input"] == ["search_query: Who founded Acme?"]
    assert json.loads(seen[1].content)["input"] == ["search_document: Acme was founded by Jane."]


def test_keyless_local_provider_sends_no_authorization(
    fake_provider: Install, local_embed: None
) -> None:
    seen = fake_provider(handler)
    llm.embed(["x"])
    assert "authorization" not in {k.lower() for k in seen[0].headers}
    assert str(seen[0].url) == "http://127.0.0.1:11434/v1/embeddings"


def test_reported_usage_is_not_estimated(fake_provider: Install, local_embed: None) -> None:
    from adaptiverag.telemetry.trace import Trace

    fake_provider(handler)
    t = Trace("q", "vector", "cli")
    llm.embed(["a", "b"], trace=t, kind="query")
    call = t.calls[0]
    assert (call.tokens_in, call.estimated, call.cost_usd) == (14, False, 0.0)


def test_same_text_as_query_and_document_are_different_cache_entries(
    fake_provider: Install, local_embed: None, memory_cache: dict[str, dict[str, object]]
) -> None:
    seen = fake_provider(handler)
    llm.embed(["Acme"], kind="query")
    llm.embed(["Acme"])
    llm.embed(["Acme"], kind="query")
    assert len(seen) == 2 and len(memory_cache) == 2
