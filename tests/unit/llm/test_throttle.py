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
