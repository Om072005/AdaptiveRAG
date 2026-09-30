import json
from collections.abc import Callable

import httpx
import numpy as np
import pytest

from adaptiverag import llm
from adaptiverag.config import models

Install = Callable[[Callable[[httpx.Request], httpx.Response]], list[httpx.Request]]


def chat_body(
    text: str = "Answer: Paris", usage: dict[str, int] | None = None
) -> dict[str, object]:
    usage = usage or {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}
    return {"choices": [{"message": {"content": text}}], "usage": usage}


def test_usage_tokens_counts_hidden_reasoning() -> None:
    # Groq: reasoning is inside completion_tokens
    assert llm.usage_tokens({"prompt_tokens": 74, "completion_tokens": 22, "total_tokens": 96}) == (
        74,
        22,
    )
    # Gemini: thinking only shows in total_tokens
    assert llm.usage_tokens({"prompt_tokens": 18, "completion_tokens": 2, "total_tokens": 68}) == (
        18,
        50,
    )


def test_cost_is_list_price_per_million() -> None:
    spec = models()["large"]
    expected = 1000 * spec.price_in_per_m / 1e6 + 500 * spec.price_out_per_m / 1e6
    assert llm.cost_usd(spec, 1000, 500) == pytest.approx(expected)


def test_chat_sends_role_model_and_reasoning_effort(fake_provider: Install) -> None:
    seen = fake_provider(lambda r: httpx.Response(200, json=chat_body()))
    result = llm.chat("large", [{"role": "user", "content": "q"}], json_mode=True)
    sent = json.loads(seen[0].content)
    assert str(seen[0].url) == models()["large"].base_url.rstrip("/") + "/chat/completions"
    assert sent["model"] == models()["large"].model
    assert sent["reasoning_effort"] == models()["large"].reasoning_effort
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["temperature"] == 0.0
    assert result.text == "Answer: Paris"
    assert (result.tokens_in, result.tokens_out, result.cached, result.estimated) == (
        100,
        20,
        False,
        False,
    )
    assert result.cost_usd == llm.cost_usd(models()["large"], 100, 20)


def test_rejected_reasoning_effort_is_dropped_once(fake_provider: Install) -> None:
    def handler(r: httpx.Request) -> httpx.Response:
        if "reasoning_effort" in json.loads(r.content):
            return httpx.Response(
                400, json={"error": {"message": "reasoning_effort is not supported"}}
            )
        return httpx.Response(200, json=chat_body())

    seen = fake_provider(handler)
    llm.chat("small", [{"role": "user", "content": "q"}])
    llm.chat("small", [{"role": "user", "content": "q"}])
    assert len(seen) == 3  # one rejection, then two clean calls
    assert "small" in llm._no_reasoning_effort


def test_other_client_errors_are_not_retried(fake_provider: Install) -> None:
    seen = fake_provider(lambda r: httpx.Response(404, json={"error": "no such model"}))
    with pytest.raises(llm.ProviderError):
        llm.chat("small", [{"role": "user", "content": "q"}])
    assert len(seen) == 1


def test_server_errors_retry_then_raise_rate_limited(fake_provider: Install) -> None:
    seen = fake_provider(lambda r: httpx.Response(503, json={"error": "busy"}))
    with pytest.raises(llm.RateLimited):
        llm.chat("large", [{"role": "user", "content": "q"}])
    assert len(seen) == llm.MAX_ATTEMPTS


def test_embed_batches_normalizes_and_estimates(fake_provider: Install) -> None:
    def handler(r: httpx.Request) -> httpx.Response:
        texts = json.loads(r.content)["input"]
        data = [{"index": i, "embedding": [3.0] + [0.0] * 766 + [4.0]} for i in range(len(texts))]
        return httpx.Response(200, json={"data": list(reversed(data))})

    seen = fake_provider(handler)
    vecs = llm.embed([f"text {i}" for i in range(250)])
    assert len(seen) == 3
    assert json.loads(seen[0].content)["dimensions"] == 768
    assert vecs.shape == (250, 768) and vecs.dtype == np.float32
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0)
    assert vecs[0, 0] == pytest.approx(0.6)


def test_embed_wrong_dimension_is_an_error(fake_provider: Install) -> None:
    fake_provider(
        lambda r: httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0] * 3072}]})
    )
    with pytest.raises(llm.ProviderError):
        llm.embed(["x"])


def test_embed_keeps_order_when_index_is_missing(fake_provider: Install) -> None:
    def handler(r: httpx.Request) -> httpx.Response:
        texts = json.loads(r.content)["input"]
        return httpx.Response(
            200,
            json={
                "data": [{"embedding": [float(i), 1.0] + [0.0] * 766} for i in range(len(texts))]
            },
        )

    fake_provider(handler)
    vecs = llm.embed(["a", "b"])
    assert vecs[0, 0] == pytest.approx(0.0)  # first text keeps the first vector
    assert vecs[1, 0] == pytest.approx(2**-0.5)


def test_capped_trace_stops_before_the_provider_is_called(fake_provider: Install) -> None:
    from adaptiverag.telemetry.trace import Trace

    seen = fake_provider(lambda r: httpx.Response(200, json=chat_body()))
    t = Trace("q", "auto", "cli")
    for _ in range(4):
        llm.chat("small", [{"role": "user", "content": "q"}], trace=t)
    with pytest.raises(llm.BudgetExceeded):
        llm.chat("small", [{"role": "user", "content": "q"}], trace=t)
    assert len(seen) == 4


def test_missing_usage_is_estimated_and_flagged(fake_provider: Install) -> None:
    fake_provider(
        lambda r: httpx.Response(
            200, json={"choices": [{"message": {"content": "Answer: Ankara"}}]}
        )
    )
    r = llm.chat("small", [{"role": "user", "content": "x" * 400}])
    assert r.estimated
    assert r.tokens_in == 100 and r.tokens_out == 3  # 4 characters per token
    assert r.cost_usd > 0


def test_usage_present_is_not_estimated(fake_provider: Install) -> None:
    fake_provider(lambda r: httpx.Response(200, json=chat_body()))
    assert not llm.chat("small", [{"role": "user", "content": "q"}]).estimated


def test_json_mode_is_skipped_for_a_model_without_it(
    fake_provider: Install, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Gemma on the Gemini API answers JSON mode with a 500; models.toml says json_mode = false
    import dataclasses

    specs = dict(models())
    specs["judge"] = dataclasses.replace(specs["judge"], json_mode=False)
    monkeypatch.setattr(llm, "models", lambda: specs)
    seen = fake_provider(lambda r: httpx.Response(200, json=chat_body("{}")))
    llm.chat("judge", [{"role": "user", "content": "q"}], json_mode=True)
    assert "response_format" not in json.loads(seen[0].content)
