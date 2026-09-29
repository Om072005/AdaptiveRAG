import dataclasses
import json

import httpx
import pytest

from adaptiverag import llm
from adaptiverag.config import models

LOAD_URL = "http://127.0.0.1:11434/api/generate"


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    seen: list[httpx.Request] = []

    def handle(r: httpx.Request) -> httpx.Response:
        seen.append(r)
        if r.url.path == "/api/generate":
            return httpx.Response(200, json={"done": True})
        body = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
        }
        return httpx.Response(200, json=body)

    monkeypatch.setattr(llm, "_client", httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(llm, "_loaded", None)
    monkeypatch.setattr(llm, "use_cache", False)
    return seen


def paths(seen: list[httpx.Request]) -> list[str]:
    return [r.url.path for r in seen]


def test_a_model_is_loaded_once_and_again_after_a_switch(server: list[httpx.Request]) -> None:
    msgs = [{"role": "user", "content": "q"}]
    llm.chat("small", msgs)
    llm.chat("small", msgs)
    llm.chat("large", msgs)
    assert paths(server) == [
        "/api/generate",
        "/v1/chat/completions",
        "/v1/chat/completions",
        "/api/generate",
        "/v1/chat/completions",
    ]
    assert json.loads(server[0].content) == {"model": models()["small"].model}
    assert json.loads(server[3].content) == {"model": models()["large"].model}


def test_hosted_models_are_never_loaded(
    server: list[httpx.Request], monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted = dataclasses.replace(models()["small"], load_url="")
    assert llm.load_local(hosted) == 0 and server == []


def test_a_server_that_cannot_load_stops_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(r: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "out of memory"})

    monkeypatch.setattr(llm, "_client", httpx.Client(transport=httpx.MockTransport(refuse)))
    monkeypatch.setattr(llm, "_loaded", None)
    with pytest.raises(llm.RateLimited, match="did not load"):
        llm.load_local(models()["large"])


def test_every_local_role_has_the_load_url() -> None:
    local = [s for s in models().values() if s.provider == "ollama"]
    assert local and all(s.load_url == LOAD_URL for s in local)
