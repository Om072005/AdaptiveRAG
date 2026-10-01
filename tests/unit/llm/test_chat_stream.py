import json
from collections.abc import Callable

import httpx
import pytest

from adaptiverag import llm
from adaptiverag.config import models
from adaptiverag.llm import installed as real_installed
from adaptiverag.llm import processor as real_processor

Install = Callable[[Callable[[httpx.Request], httpx.Response]], list[httpx.Request]]


def sse(*pieces: dict[str, object]) -> bytes:
    return (
        b"".join(b"data: " + json.dumps(p).encode() + b"\n\n" for p in pieces) + b"data: [DONE]\n\n"
    )


def delta(**d: str) -> dict[str, object]:
    return {"choices": [{"index": 0, "delta": d, "finish_reason": None}]}


STREAM = sse(
    delta(role="assistant", content="", reasoning="Compare "),
    delta(content="", reasoning="the years."),
    delta(content="Answer: "),
    delta(content="Paris [1]"),
    {"choices": [], "usage": {"prompt_tokens": 80, "completion_tokens": 16, "total_tokens": 96}},
)


def test_streamed_chat_passes_on_thinking_then_answer(fake_provider: Install) -> None:
    seen = fake_provider(lambda r: httpx.Response(200, content=STREAM))
    pieces: list[tuple[str, str]] = []
    result = llm.chat(
        "small", [{"role": "user", "content": "q"}], on_delta=lambda k, t: pieces.append((k, t))
    )
    sent = json.loads(seen[0].content)
    assert sent["stream"] is True and sent["stream_options"] == {"include_usage": True}
    assert pieces == [
        ("thinking", "Compare "),
        ("thinking", "the years."),
        ("answer", "Answer: "),
        ("answer", "Paris [1]"),
    ]
    assert result.text == "Answer: Paris [1]"
    assert (result.tokens_in, result.tokens_out, result.estimated) == (80, 16, False)


def test_streamed_and_plain_calls_share_one_cache_entry(
    fake_provider: Install, memory_cache: dict[str, dict[str, object]]
) -> None:
    seen = fake_provider(lambda r: httpx.Response(200, content=STREAM))
    messages = [{"role": "user", "content": "q"}]
    llm.chat("small", messages, on_delta=lambda k, t: None)
    (row,) = memory_cache.values()
    assert row["response"] == {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Answer: Paris [1]",
                    "reasoning": "Compare the years.",
                }
            }
        ],
        "usage": {"prompt_tokens": 80, "completion_tokens": 16, "total_tokens": 96},
    }
    # the cached answer comes back whole, thinking first, without another request
    pieces: list[tuple[str, str]] = []
    again = llm.chat("small", messages, on_delta=lambda k, t: pieces.append((k, t)))
    assert len(seen) == 1 and again.cached and again.text == "Answer: Paris [1]"
    assert pieces == [("thinking", "Compare the years."), ("answer", "Answer: Paris [1]")]
    assert llm.chat("small", messages).cached  # a plain call finds the same entry


def test_stream_refused_by_a_busy_server_is_rate_limited(fake_provider: Install) -> None:
    fake_provider(lambda r: httpx.Response(503, content=b"busy"))
    with pytest.raises(llm.RateLimited):
        llm.chat("small", [{"role": "user", "content": "q"}], on_delta=lambda k, t: None)


def tags(*names: str) -> httpx.Response:
    return httpx.Response(200, json={"models": [{"name": n} for n in names]})


def test_installed_reads_the_local_server_once(
    fake_provider: Install, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm, "_installed", {})
    seen = fake_provider(lambda r: tags("gpt-oss:20b", "nomic-embed-text:latest"))
    assert real_installed(models()["small"]) and real_installed(models()["embed"])
    assert not real_installed(models()["large"])
    assert [r.url.path for r in seen] == ["/api/tags"]


def test_a_server_that_does_not_answer_has_nothing_installed(
    fake_provider: Install, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm, "_installed", {})

    def refuse(r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    fake_provider(refuse)
    assert not real_installed(models()["small"])
    assert llm._installed == {}  # asked again next time, once the server runs


@pytest.mark.parametrize(
    ("vram", "expected"), [(14, "100% GPU"), (6, "43% GPU, 57% CPU"), (0, "100% CPU")]
)
def test_processor_says_where_the_model_sits(
    fake_provider: Install, vram: int, expected: str
) -> None:
    model = models()["small"].model
    fake_provider(
        lambda r: httpx.Response(
            200, json={"models": [{"name": model, "size": 14, "size_vram": vram}]}
        )
    )
    assert real_processor(models()["small"]) == expected


def test_processor_is_none_for_a_model_not_loaded(fake_provider: Install) -> None:
    fake_provider(lambda r: httpx.Response(200, json={"models": []}))
    assert real_processor(models()["small"]) is None


def test_a_stream_that_never_finishes_is_an_error_and_is_not_cached(
    fake_provider: Install, memory_cache: dict[str, dict[str, object]]
) -> None:
    cut = b"data: " + json.dumps(delta(content="Answer: Par")).encode() + b"\n\n"
    fake_provider(lambda r: httpx.Response(200, content=cut))
    with pytest.raises(llm.RateLimited, match="ended early"):
        llm.chat("small", [{"role": "user", "content": "q"}], on_delta=lambda k, t: None)
    assert memory_cache == {}


def test_an_error_inside_the_stream_is_a_provider_error(fake_provider: Install) -> None:
    body = sse(delta(content="Answer: "), {"error": {"message": "model crashed"}})
    fake_provider(lambda r: httpx.Response(200, content=body))
    with pytest.raises(llm.ProviderError, match="model crashed"):
        llm.chat("small", [{"role": "user", "content": "q"}], on_delta=lambda k, t: None)


def test_a_stream_refused_before_any_piece_falls_back_to_the_plain_request(
    fake_provider: Install,
) -> None:
    plain = {
        "choices": [{"message": {"content": "Answer: Paris", "reasoning": "Capital."}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
    }

    def handler(r: httpx.Request) -> httpx.Response:
        if json.loads(r.content).get("stream"):
            return httpx.Response(503, content=b"busy")
        return httpx.Response(200, json=plain)

    seen = fake_provider(handler)
    pieces: list[tuple[str, str]] = []
    result = llm.chat(
        "small", [{"role": "user", "content": "q"}], on_delta=lambda k, t: pieces.append((k, t))
    )
    assert result.text == "Answer: Paris" and result.retries == 1 and len(seen) == 2
    assert pieces == [("thinking", "Capital."), ("answer", "Answer: Paris")]


def test_missing_needs_a_server_that_answered(
    fake_provider: Install, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm, "_installed", {})
    fake_provider(lambda r: tags("gpt-oss:20b"))
    assert llm.missing(models()["large"]) and not llm.missing(models()["small"])
    monkeypatch.setattr(llm, "_installed", {})

    def refuse(r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    fake_provider(refuse)
    assert not llm.missing(models()["large"])  # a server that is down is not "model missing"
