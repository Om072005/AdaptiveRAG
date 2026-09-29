import json
from collections.abc import Callable

import httpx
import numpy as np

from adaptiverag import llm

Install = Callable[[Callable[[httpx.Request], httpx.Response]], list[httpx.Request]]
USAGE = {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60}


def test_same_chat_twice_hits_cache_with_original_numbers(
    fake_provider: Install, memory_cache: dict[str, dict[str, object]]
) -> None:
    body = {"choices": [{"message": {"content": "Answer: 42"}}], "usage": USAGE}
    seen = fake_provider(lambda r: httpx.Response(200, json=body))
    msgs = [{"role": "user", "content": "q"}]
    first = llm.chat("small", msgs)
    second = llm.chat("small", msgs)
    assert len(seen) == 1
    assert not first.cached and second.cached
    assert (second.text, second.tokens_in, second.tokens_out) == ("Answer: 42", 50, 10)
    assert second.latency_ms == first.latency_ms
    assert second.cost_usd == first.cost_usd


def test_any_param_change_is_a_different_key(
    fake_provider: Install, memory_cache: dict[str, dict[str, object]]
) -> None:
    body = {"choices": [{"message": {"content": "x"}}], "usage": USAGE}
    seen = fake_provider(lambda r: httpx.Response(200, json=body))
    msgs = [{"role": "user", "content": "q"}]
    llm.chat("small", msgs)
    llm.chat("small", msgs, max_tokens=100)
    llm.chat("large", msgs)
    assert len(seen) == 3


def test_request_key_ignores_dict_order() -> None:
    assert llm.request_key({"a": 1, "b": [1, 2]}) == llm.request_key({"b": [1, 2], "a": 1})


def test_embed_only_sends_texts_not_in_cache(
    fake_provider: Install, memory_cache: dict[str, dict[str, object]]
) -> None:
    def handler(r: httpx.Request) -> httpx.Response:
        texts = json.loads(r.content)["input"]
        return httpx.Response(
            200, json={"data": [{"embedding": [1.0, float(len(t))] + [0.0] * 766} for t in texts]}
        )

    seen = fake_provider(handler)
    first = llm.embed(["a", "bb"])
    second = llm.embed(["bb", "ccc", "a"])
    prefix = llm.models()["embed"].document_prefix
    assert json.loads(seen[1].content)["input"] == [prefix + "ccc"]
    assert np.allclose(second[0], first[1]) and np.allclose(second[2], first[0])
    assert np.allclose(np.linalg.norm(second, axis=1), 1.0)


def test_cache_hit_keeps_the_estimated_flag(
    fake_provider: Install, memory_cache: dict[str, dict[str, object]]
) -> None:
    seen = fake_provider(
        lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    )
    msgs = [{"role": "user", "content": "no usage here"}]
    first, second = llm.chat("small", msgs), llm.chat("small", msgs)
    assert len(seen) == 1 and first.estimated and second.cached and second.estimated
