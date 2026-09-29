"""The only module that talks to model providers: chat and embeddings, cached, priced, capped."""

import logging
import random
import time
from typing import TYPE_CHECKING, Any

import httpx
import numpy as np

from adaptiverag.config import ModelSpec, models, settings
from adaptiverag.types import LLMResult, Role

if TYPE_CHECKING:
    from adaptiverag.telemetry.trace import Trace

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
EMBED_BATCH = 100
BACKOFF_BASE_S = 1.0
BACKOFF_MAX_S = 30.0

_sleep = time.sleep  # swapped out in tests
_client: httpx.Client | None = None
_no_reasoning_effort: set[Role] = set()  # roles whose provider rejected reasoning_effort


class BudgetExceeded(Exception):
    """Raised on the 5th LLM call inside one trace (the cost spiral guard)."""


class RateLimited(Exception):
    """Raised after 5 failed attempts on 429 or 5xx; eval runs save progress and resume later."""


class ProviderError(Exception):
    """The provider refused the request for a reason a retry will not fix (model, params)."""


def client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0))
    return _client


def cost_usd(spec: ModelSpec, tokens_in: int, tokens_out: int) -> float:
    """List price cost, rounded to the 8 decimals the database keeps."""
    cost = tokens_in * spec.price_in_per_m / 1e6 + tokens_out * spec.price_out_per_m / 1e6
    return round(cost, 8)


def usage_tokens(usage: dict[str, Any]) -> tuple[int, int]:
    """(tokens_in, tokens_out) from an OpenAI style usage block.

    Hidden reasoning is billed as output. Groq counts it inside completion_tokens; Gemini leaves
    it out of completion_tokens but counts it in total_tokens, so output is the larger reading.
    """
    tokens_in = int(usage.get("prompt_tokens", 0))
    completion = int(usage.get("completion_tokens", 0))
    total = int(usage.get("total_tokens", 0))
    return tokens_in, max(completion, total - tokens_in)


def estimate_tokens(texts: list[str]) -> int:
    """Rough count (4 characters per token) for responses without a usage block."""
    return sum(max(1, len(t) // 4) for t in texts)


def backoff_s(attempt: int) -> float:
    """Exponential backoff with full jitter, capped."""
    return random.uniform(0, min(BACKOFF_MAX_S, BACKOFF_BASE_S * 2**attempt))


def _api_key(spec: ModelSpec) -> str:
    key = getattr(settings(), spec.key_env.lower(), "")
    if not key:
        raise ProviderError(f"{spec.key_env} is not set (see .env.example)")
    return str(key)


def _post(
    spec: ModelSpec, path: str, payload: dict[str, Any]
) -> tuple[dict[str, Any], int, int, int]:
    """POST, retrying 429 and 5xx. Returns (json, latency_ms of good attempt, retries, wait_ms)."""
    url = spec.base_url.rstrip("/") + "/" + path
    headers = {"Authorization": f"Bearer {_api_key(spec)}"}
    retries = wait_ms = 0
    for attempt in range(MAX_ATTEMPTS):
        started = time.perf_counter()
        r = client().post(url, headers=headers, json=payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if r.status_code == 429 or r.status_code >= 500:
            if attempt == MAX_ATTEMPTS - 1:
                raise RateLimited(f"{spec.model}: {r.status_code} after {MAX_ATTEMPTS} attempts")
            delay = backoff_s(attempt)
            _sleep(delay)
            retries += 1
            wait_ms += int(delay * 1000)
            continue
        if r.status_code >= 400:
            raise ProviderError(f"{spec.model}: {r.status_code} {r.text[:300]}")
        return r.json(), latency_ms, retries, wait_ms
    raise RateLimited(f"{spec.model}: no attempts left")  # not reached


def chat(
    role: Role,
    messages: list[dict[str, str]],
    *,
    json_mode: bool = False,
    trace: "Trace | None" = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> LLMResult:
    """One chat completion for a role from config/models.toml."""
    spec = models()[role]
    payload: dict[str, Any] = {
        "model": spec.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if spec.reasoning_effort and role not in _no_reasoning_effort:
        payload["reasoning_effort"] = spec.reasoning_effort
    try:
        body, latency_ms, retries, wait_ms = _post(spec, "chat/completions", payload)
    except ProviderError as e:
        if "reasoning_effort" not in payload or "reasoning" not in str(e).lower():
            raise
        log.warning("provider rejected reasoning_effort for role %s, dropping it: %s", role, e)
        _no_reasoning_effort.add(role)
        del payload["reasoning_effort"]
        body, latency_ms, retries, wait_ms = _post(spec, "chat/completions", payload)

    text = body["choices"][0]["message"].get("content") or ""
    tokens_in, tokens_out = usage_tokens(body.get("usage") or {})
    result = LLMResult(
        text=text,
        role=role,
        model=spec.model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd(spec, tokens_in, tokens_out),
        latency_ms=latency_ms,
        cached=False,
        estimated=False,
        retries=retries,
        wait_ms=wait_ms,
    )
    if trace is not None:
        trace.add_llm(result)
    return result


def normalize_rows(vecs: np.ndarray) -> np.ndarray:
    """L2 normalize each row; truncated 768 dim vectors from the provider are not unit length."""
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return (vecs / np.where(norms == 0, 1, norms)).astype(np.float32)


def embed(texts: list[str], *, trace: "Trace | None" = None) -> np.ndarray:
    """(n, 768) float32, L2 normalized, sent in batches of 100."""
    spec = models()["embed"]
    dims = spec.dims or 768
    out: list[np.ndarray] = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        payload = {"model": spec.model, "input": batch, "dimensions": dims}
        body, latency_ms, retries, wait_ms = _post(spec, "embeddings", payload)
        # Gemini omits "index"; a stable sort keeps the response order then
        rows = sorted(body["data"], key=lambda d: d.get("index", 0))
        vecs = np.array([row["embedding"] for row in rows], dtype=np.float32)
        if vecs.shape != (len(batch), dims):
            raise ProviderError(f"{spec.model}: expected {(len(batch), dims)}, got {vecs.shape}")
        out.append(normalize_rows(vecs))
        usage = body.get("usage")
        tokens_in = int(usage["prompt_tokens"]) if usage else estimate_tokens(batch)
        result = LLMResult(
            text="",
            role="embed",
            model=spec.model,
            tokens_in=tokens_in,
            tokens_out=0,
            cost_usd=cost_usd(spec, tokens_in, 0),
            latency_ms=latency_ms,
            cached=False,
            estimated=usage is None,
            retries=retries,
            wait_ms=wait_ms,
        )
        if trace is not None:
            trace.add_llm(result)
    return np.vstack(out) if out else np.zeros((0, dims), dtype=np.float32)
