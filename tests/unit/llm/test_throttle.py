import time
from collections.abc import Callable

import httpx
import pytest

from adaptiverag import llm

Install = Callable[[Callable[[httpx.Request], httpx.Response]], list[httpx.Request]]
OK = {
    "choices": [{"message": {"content": "ok"}}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
}


def test_429_then_200_keeps_latency_and_wait_apart(
    fake_provider: Install, monkeypatch: pytest.MonkeyPatch
) -> None:
    slept: list[float] = []
    monkeypatch.setattr(llm, "_sleep", slept.append)
    calls = {"n": 0}

    def handler(r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            time.sleep(0.3)  # a slow failed attempt must not count as latency
            return httpx.Response(429, headers={"retry-after": "2"})
        return httpx.Response(200, json=OK)

    fake_provider(handler)
    r = llm.chat("small", [{"role": "user", "content": "q"}])
    assert slept == [2.0]  # retry-after honoured
    assert (r.retries, r.wait_ms) == (1, 2000)
    assert r.latency_ms < 250  # the successful attempt only


def test_gemini_retry_delay_in_body_is_honoured() -> None:
    body = [{"error": {"code": 429, "details": [{"@type": "RetryInfo", "retryDelay": "7s"}]}}]
    assert llm.retry_after_s(httpx.Response(429, json=body)) == 7.0
    assert llm.retry_after_s(httpx.Response(503, json={"error": {"message": "busy"}})) is None


def test_five_throttled_attempts_raise_rate_limited(fake_provider: Install) -> None:
    seen = fake_provider(lambda r: httpx.Response(429, headers={"retry-after": "1"}))
    with pytest.raises(llm.RateLimited):
        llm.chat("large", [{"role": "user", "content": "q"}])
    assert len(seen) == 5


def test_long_retry_after_stops_at_once(fake_provider: Install) -> None:
    seen = fake_provider(lambda r: httpx.Response(429, headers={"retry-after": "3600"}))
    with pytest.raises(llm.RateLimited, match="quota exhausted"):
        llm.chat("large", [{"role": "user", "content": "q"}])
    assert len(seen) == 1


GEMINI_DAILY = {
    "error": {
        "code": 429,
        "status": "RESOURCE_EXHAUSTED",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                "violations": [
                    {
                        "quotaId": "EmbedContentRequestsPerDayPerProjectPerModel-FreeTier",
                        "quotaValue": "1000",
                    }
                ],
            },
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "51s"},
        ],
    }
}
GEMINI_MINUTE = {
    "error": {
        "code": 429,
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                "violations": [
                    {"quotaId": "EmbedContentRequestsPerMinutePerUserPerProjectPerModel-FreeTier"}
                ],
            },
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "47s"},
        ],
    }
}


def test_daily_quota_stops_without_retrying(fake_provider: Install) -> None:
    seen = fake_provider(lambda r: httpx.Response(429, json=GEMINI_DAILY))
    with pytest.raises(llm.RateLimited, match="daily quota"):
        llm.embed(["a"])
    assert len(seen) == 1  # even though retryDelay (51 s) is under the cap


def test_per_minute_quota_is_still_waited_out() -> None:
    assert llm.daily_quota(httpx.Response(429, json=GEMINI_MINUTE)) is None
    assert llm.retry_after_s(httpx.Response(429, json=GEMINI_MINUTE)) == 47.0


def test_groq_tokens_per_day_message_is_daily() -> None:
    body = {
        "error": {"message": "Rate limit reached for model on tokens per day (TPD): Limit 200000"}
    }
    assert llm.daily_quota(httpx.Response(429, json=body)) == "per day limit"


def test_judge_does_not_retry_a_busy_provider(fake_provider: Install) -> None:
    seen = fake_provider(lambda r: httpx.Response(503, json={"error": {"message": "high demand"}}))
    with pytest.raises(llm.RateLimited, match="provider busy"):
        llm.chat("judge", [{"role": "user", "content": "q"}])
    assert len(seen) == 1


def test_other_roles_still_retry_server_errors(fake_provider: Install) -> None:
    calls = {"n": 0}

    def handler(r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] == 1 else httpx.Response(200, json=OK)

    fake_provider(handler)
    assert llm.chat("large", [{"role": "user", "content": "q"}]).retries == 1


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0
        self.slept: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.t += s


def test_embeddings_are_paced_under_the_per_minute_budget(
    fake_provider: Install, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = Clock()
    monkeypatch.setattr(llm, "_now", clock.now)
    monkeypatch.setattr(llm, "_sleep", clock.sleep)
    monkeypatch.setattr(llm, "_sent", [])
    sizes: list[int] = []

    def handler(r: httpx.Request) -> httpx.Response:
        import json

        texts = json.loads(r.content)["input"]
        sizes.append(len(texts))
        return httpx.Response(
            200, json={"data": [{"embedding": [1.0] + [0.0] * 767} for _ in texts]}
        )

    fake_provider(handler)
    budget = llm.models()["embed"].texts_per_minute
    assert budget and budget < 100
    llm.embed([f"t{i}" for i in range(250)])
    assert all(s <= budget for s in sizes) and sum(sizes) == 250
    assert len(clock.slept) == len(sizes) - 1  # every batch after the first waited for the window
    assert all(55 <= s <= 61 for s in clock.slept)


def test_pace_counts_only_the_last_minute() -> None:
    clock = Clock()
    llm._now, llm._sleep, llm._sent[:] = clock.now, clock.sleep, []
    try:
        assert llm.pace(50, 90) == 0
        clock.t += 61
        assert llm.pace(80, 90) == 0  # the first 50 left the window
        assert llm.pace(20, 90) > 0
    finally:
        import time

        llm._now, llm._sleep = time.monotonic, time.sleep
        llm._sent[:] = []


def test_read_timeout_is_retried_then_succeeds(fake_provider: Install) -> None:
    calls = {"n": 0}

    def handler(r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("read timed out", request=r)
        return httpx.Response(200, json=OK)

    fake_provider(handler)
    result = llm.chat("extract", [{"role": "user", "content": "q"}])
    assert result.retries == 1 and calls["n"] == 2


def test_network_errors_every_time_raise_rate_limited_so_runs_resume(
    fake_provider: Install,
) -> None:
    def handler(r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=r)

    seen = fake_provider(handler)
    with pytest.raises(llm.RateLimited, match="network error"):
        llm.chat("large", [{"role": "user", "content": "q"}])
    assert len(seen) == llm.MAX_ATTEMPTS


def test_judge_does_not_retry_a_network_error_either(fake_provider: Install) -> None:
    def handler(r: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out", request=r)

    seen = fake_provider(handler)
    with pytest.raises(llm.RateLimited):
        llm.chat("judge", [{"role": "user", "content": "q"}])
    assert len(seen) == 1
