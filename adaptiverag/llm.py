"""The only module that talks to model providers: chat and embeddings, cached, priced, capped."""

import base64
import hashlib
import json
import logging
import random
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Literal

import httpx
import numpy as np

from adaptiverag.config import ModelSpec, models, settings
from adaptiverag.stores import cache
from adaptiverag.types import LLMResult, Role

if TYPE_CHECKING:
    from adaptiverag.telemetry.trace import Trace

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
EMBED_BATCH = 100
BACKOFF_BASE_S = 1.0
BACKOFF_MAX_S = 30.0
MAX_RETRY_AFTER_S = (
    90.0  # per minute limits ask for up to ~60 s; longer means the daily quota is gone
)

_sleep = time.sleep  # swapped out in tests
_now = time.monotonic  # swapped out in tests
_sent: list[tuple[float, int]] = []  # (when, texts) of recent embedding requests, for pacing
_client: httpx.Client | None = None
_no_reasoning_effort: set[Role] = set()  # roles whose provider rejected reasoning_effort
use_cache = True  # unit tests with a fake provider turn it off
_loaded: str | None = None  # the model the local server last answered with
_installed: dict[str, set[str]] = {}  # local server url -> model names it has, asked once

# (kind, text) for each piece of a streamed answer: kind is "thinking" (the model's reasoning,
# when the server returns it) or "answer"
OnDelta = Callable[[str, str], None]


class BudgetExceeded(Exception):
    """Raised on the 5th LLM call inside one trace (the cost spiral guard)."""


class RateLimited(Exception):
    """Raised after 5 failed attempts on 429 or 5xx; eval runs save progress and resume later."""


class ProviderError(Exception):
    """The provider refused the request for a reason a retry will not fix (model, params)."""


def client() -> httpx.Client:
    global _client
    if _client is None:
        # a local model may think for minutes on a long context, so reads wait up to 10 minutes
        _client = httpx.Client(timeout=httpx.Timeout(600.0, connect=15.0))
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


def request_key(payload: dict[str, Any]) -> str:
    """sha256 of the canonical JSON of what is sent: model, messages or input, and every param."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def estimate_tokens(texts: list[str]) -> int:
    """Rough count (4 characters per token) for responses without a usage block."""
    return sum(max(1, len(t) // 4) for t in texts)


def backoff_s(attempt: int) -> float:
    """Exponential backoff with full jitter, capped."""
    return random.uniform(0, min(BACKOFF_MAX_S, BACKOFF_BASE_S * 2**attempt))


def retry_after_s(r: httpx.Response) -> float | None:
    """Seconds the provider asked us to wait: the retry-after header, or Gemini's retryDelay."""
    header = r.headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            return None
    try:
        body = r.json()
    except ValueError:
        return None
    errors = body if isinstance(body, list) else [body]
    for err in errors:
        inner = err.get("error") if isinstance(err, dict) else None
        details = inner.get("details", []) if isinstance(inner, dict) else []
        for d in details:
            delay = str(d.get("retryDelay", "")) if isinstance(d, dict) else ""
            if delay.endswith("s"):
                return float(delay[:-1])
    return None


def _error_bodies(r: httpx.Response) -> list[dict[str, Any]]:
    try:
        body = r.json()
    except ValueError:
        return []
    items = body if isinstance(body, list) else [body]
    inner = [i.get("error") for i in items if isinstance(i, dict)]
    return [e for e in inner if isinstance(e, dict)]


def daily_quota(r: httpx.Response) -> str | None:
    """The quota name if a 429 is a per day limit: retrying cannot help until the day resets.

    Gemini names it in QuotaFailure (quotaId ...PerDay...); Groq says "per day" in the message.
    """
    for err in _error_bodies(r):
        for d in err.get("details", []):
            for v in d.get("violations", []) if isinstance(d, dict) else []:
                if "perday" in str(v.get("quotaId", "")).lower():
                    return str(v["quotaId"])
        if "per day" in str(err.get("message", "")).lower():
            return "per day limit"
    return None


def _api_key(spec: ModelSpec) -> str:
    """The provider key from the environment; empty for a local provider that needs none."""
    if not spec.key_env:
        return ""
    key = getattr(settings(), spec.key_env.lower(), "")
    if not key:
        raise ProviderError(f"{spec.key_env} is not set (see .env.example)")
    return str(key)


def load_local(spec: ModelSpec) -> int:
    """Load a local model before timing a call; returns the ms spent, reported as wait.

    Two local models do not fit in memory together, so switching costs minutes of disk reads.
    Counting that as latency would make whichever model ran second look slow."""
    global _loaded
    if not spec.load_url or _loaded == spec.model:
        return 0
    started = time.perf_counter()
    try:
        client().post(spec.load_url, json={"model": spec.model}).raise_for_status()
    except httpx.HTTPError as e:
        raise RateLimited(f"{spec.model}: local model server did not load it ({e!r})") from e
    _loaded = spec.model
    return int((time.perf_counter() - started) * 1000)


def _server_url(spec: ModelSpec) -> str:
    """The local model server's root (http://host:port), from its load url."""
    return spec.load_url.split("/api/", 1)[0]


def installed(spec: ModelSpec) -> bool:
    """Whether the local model server has this model pulled. Hosted models count as installed;
    a local server that does not answer counts as having none."""
    if not spec.load_url:
        return True
    root = _server_url(spec)
    if root not in _installed:
        try:
            r = client().get(root + "/api/tags", timeout=5.0)
            r.raise_for_status()
            names = {m["name"] for m in r.json().get("models", [])}
        except (httpx.HTTPError, ValueError):
            return False  # not remembered, so a server started later is seen
        _installed[root] = names | {n.removesuffix(":latest") for n in names}
    return spec.model in _installed[root]


def missing(spec: ModelSpec) -> bool:
    """True only when the local server answered and does not have the model: a server that is
    down is a failure for the call itself to report, not a reason to switch models."""
    if installed(spec):
        return False
    return _server_url(spec) in _installed


def processor(spec: ModelSpec) -> str | None:
    """Where the local server holds the model right now, as `ollama ps` puts it: '100% GPU',
    '42% GPU, 58% CPU' or '100% CPU'. None for a hosted model or one not loaded."""
    if not spec.load_url:
        return None
    try:
        r = client().get(_server_url(spec) + "/api/ps", timeout=5.0)
        r.raise_for_status()
        running = r.json().get("models", [])
    except (httpx.HTTPError, ValueError):
        return None
    for m in running:
        if m.get("name") in (spec.model, spec.model + ":latest") and m.get("size"):
            gpu = round(100 * int(m.get("size_vram", 0)) / int(m["size"]))
            if gpu >= 100:
                return "100% GPU"
            return "100% CPU" if gpu <= 0 else f"{gpu}% GPU, {100 - gpu}% CPU"
    return None


@contextmanager
def fresh() -> Iterator[None]:
    """Neither read nor write the cache inside the block: every result comes from the model."""
    global use_cache
    was, use_cache = use_cache, False
    try:
        yield
    finally:
        use_cache = was


def _post(
    spec: ModelSpec, path: str, payload: dict[str, Any]
) -> tuple[dict[str, Any], int, int, int]:
    """POST, retrying 429 and 5xx. Returns (json, latency_ms of good attempt, retries, wait_ms)."""
    url = spec.base_url.rstrip("/") + "/" + path
    loaded_ms = load_local(spec) if path == "chat/completions" else 0
    key = _api_key(spec)
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    retries, wait_ms = 0, loaded_ms
    for attempt in range(MAX_ATTEMPTS):
        started = time.perf_counter()
        try:
            r = client().post(url, headers=headers, json=payload)
        except httpx.TransportError as e:
            # timeouts and dropped connections: retried like a busy provider, same attempt limits
            if attempt + 1 >= min(MAX_ATTEMPTS, spec.server_error_attempts):
                raise RateLimited(f"{spec.model}: network error ({e!r}), resume later") from e
            delay = backoff_s(attempt)
            _sleep(delay)
            retries += 1
            wait_ms += int(delay * 1000)
            continue
        latency_ms = int((time.perf_counter() - started) * 1000)
        if r.status_code == 429 and (quota := daily_quota(r)):
            # a refused retry can still count against the quota, so stop at once
            raise RateLimited(f"{spec.model}: daily quota used up ({quota}), resume tomorrow")
        if r.status_code >= 500 and attempt + 1 >= spec.server_error_attempts:
            # every refused attempt counts against a small daily quota (the judge has 20)
            raise RateLimited(f"{spec.model}: provider busy ({r.status_code}), resume later")
        if r.status_code == 429 or r.status_code >= 500:
            if attempt == MAX_ATTEMPTS - 1:
                raise RateLimited(f"{spec.model}: {r.status_code} after {MAX_ATTEMPTS} attempts")
            asked = retry_after_s(r)
            if asked is not None and asked > MAX_RETRY_AFTER_S:
                raise RateLimited(
                    f"{spec.model}: provider asks to wait {asked:.0f}s, quota exhausted"
                )
            delay = asked if asked is not None else backoff_s(attempt)
            _sleep(delay)
            retries += 1
            wait_ms += int(delay * 1000)
            continue
        if r.status_code >= 400:
            raise ProviderError(f"{spec.model}: {r.status_code} {r.text[:300]}")
        return r.json(), latency_ms, retries, wait_ms
    raise RateLimited(f"{spec.model}: no attempts left")  # not reached


class _NotStarted(Exception):
    """A stream failed before any piece was passed on, so the plain request (with its retries)
    can still answer in its place."""


def replay(message: dict[str, Any], on_delta: OnDelta) -> None:
    """Pass a whole answer on as streamed pieces: the reasoning, if any, then the text."""
    if message.get("reasoning"):
        on_delta("thinking", str(message["reasoning"]))
    on_delta("answer", str(message.get("content") or ""))


def _pass_on(delta: dict[str, Any], on_delta: OnDelta, parts: dict[str, list[str]]) -> None:
    for kind, field in (("thinking", "reasoning"), ("answer", "content")):
        if delta.get(field):
            parts[kind].append(delta[field])
            on_delta(kind, delta[field])


def _stream(
    spec: ModelSpec, payload: dict[str, Any], on_delta: OnDelta
) -> tuple[dict[str, Any], int, int, int]:
    """One streamed chat completion, passed on piece by piece. Returns the same (json, latency_ms,
    retries, wait_ms) as _post, the json in the non streamed shape so the cache stores one form.
    Pieces already shown cannot be taken back: a failure before the first piece raises _NotStarted,
    after it the call fails, and a stream that never says it finished is never returned (so a cut
    off answer is never cached)."""
    url = spec.base_url.rstrip("/") + "/chat/completions"
    wait_ms = load_local(spec)
    key = _api_key(spec)
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    body = {**payload, "stream": True, "stream_options": {"include_usage": True}}
    parts: dict[str, list[str]] = {"thinking": [], "answer": []}
    usage: dict[str, Any] | None = None
    finished = False
    started = time.perf_counter()
    try:
        with client().stream("POST", url, headers=headers, json=body) as r:
            if r.status_code == 429 or r.status_code >= 500:
                raise _NotStarted(f"status {r.status_code}")
            if r.status_code >= 400:
                raise ProviderError(f"{spec.model}: {r.status_code} {r.read().decode()[:300]}")
            for line in r.iter_lines():
                data = line.removeprefix("data:").strip()
                if not line.startswith("data:") or not data:
                    continue
                if data == "[DONE]":
                    finished = True
                    continue
                piece = json.loads(data)
                if piece.get("error"):
                    raise ProviderError(f"{spec.model}: stream error {str(piece['error'])[:300]}")
                usage = piece.get("usage") or usage
                for choice in piece.get("choices") or []:
                    finished = finished or bool(choice.get("finish_reason"))
                    _pass_on(choice.get("delta") or {}, on_delta, parts)
    except httpx.TransportError as e:
        if not parts["thinking"] and not parts["answer"]:
            raise _NotStarted(repr(e)) from e
        raise RateLimited(f"{spec.model}: network error mid answer ({e!r}), resume later") from e
    if not finished:
        raise RateLimited(f"{spec.model}: the answer stream ended early; nothing was cached")
    latency_ms = int((time.perf_counter() - started) * 1000)
    message: dict[str, Any] = {"role": "assistant", "content": "".join(parts["answer"])}
    if parts["thinking"]:
        message["reasoning"] = "".join(parts["thinking"])
    out: dict[str, Any] = {"choices": [{"message": message}]}
    if usage:
        out["usage"] = usage
    return out, latency_ms, 0, wait_ms


def _stream_or_post(
    spec: ModelSpec, payload: dict[str, Any], on_delta: OnDelta
) -> tuple[dict[str, Any], int, int, int]:
    """Stream; if the stream fails before its first piece, ask the plain way (which retries) and
    pass the whole answer on."""
    try:
        return _stream(spec, payload, on_delta)
    except _NotStarted as e:
        log.warning("%s: stream not available (%s), asking without streaming", spec.model, e)
        body, latency_ms, retries, wait_ms = _post(spec, "chat/completions", payload)
        replay(body["choices"][0]["message"], on_delta)
        return body, latency_ms, retries + 1, wait_ms


def chat(
    role: Role,
    messages: list[dict[str, str]],
    *,
    json_mode: bool = False,
    trace: "Trace | None" = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    on_delta: OnDelta | None = None,
) -> LLMResult:
    """One chat completion for a role from config/models.toml.

    With on_delta the answer streams: each piece of reasoning and answer text is passed on as it
    arrives. A cached answer is passed on whole. The cache key is the same either way."""
    spec = models()[role]
    payload: dict[str, Any] = {
        "model": spec.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode and spec.json_mode:
        payload["response_format"] = {"type": "json_object"}
    if spec.reasoning_effort and role not in _no_reasoning_effort:
        payload["reasoning_effort"] = spec.reasoning_effort
    if trace is not None:
        trace.check_budget()  # before the provider is paid, not after
    key = request_key(payload)
    hit = cache.get_many([key]).get(key) if use_cache else None
    if hit is not None:
        message = hit["response"]["choices"][0]["message"]
        if on_delta is not None:
            replay(message, on_delta)
        result = LLMResult(
            text=message.get("content") or "",
            role=role,
            model=spec.model,
            tokens_in=hit["tokens_in"],
            tokens_out=hit["tokens_out"],
            cost_usd=cost_usd(spec, hit["tokens_in"], hit["tokens_out"]),
            latency_ms=hit["latency_ms"],
            cached=True,
            estimated=not hit["response"].get("usage"),
            retries=0,
            wait_ms=0,
        )
    else:
        result = _chat_uncached(role, spec, payload, on_delta)
    if trace is not None:
        trace.add_llm(result)
    return result


def _chat_uncached(
    role: Role, spec: ModelSpec, payload: dict[str, Any], on_delta: OnDelta | None = None
) -> LLMResult:
    def send() -> tuple[dict[str, Any], int, int, int]:
        if on_delta is not None:
            return _stream_or_post(spec, payload, on_delta)
        return _post(spec, "chat/completions", payload)

    try:
        body, latency_ms, retries, wait_ms = send()
    except ProviderError as e:
        if "reasoning_effort" not in payload or "reasoning" not in str(e).lower():
            raise
        log.warning("provider rejected reasoning_effort for role %s, dropping it: %s", role, e)
        _no_reasoning_effort.add(role)
        del payload["reasoning_effort"]
        body, latency_ms, retries, wait_ms = send()

    usage = body.get("usage")
    text = body["choices"][0]["message"].get("content") or ""
    if usage:
        tokens_in, tokens_out = usage_tokens(usage)
    else:
        # no usage block: estimate so the call is never counted as free, and say so on the ledger
        tokens_in = estimate_tokens([m.get("content", "") for m in payload["messages"]])
        tokens_out = estimate_tokens([text])
    if use_cache:
        row = {"key": request_key(payload), "role": role, "model": spec.model, "response": body}
        cache.put_many(
            [{**row, "tokens_in": tokens_in, "tokens_out": tokens_out, "latency_ms": latency_ms}]
        )
    return LLMResult(
        text=text,
        role=role,
        model=spec.model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd(spec, tokens_in, tokens_out),
        latency_ms=latency_ms,
        cached=False,
        estimated=not usage,
        retries=retries,
        wait_ms=wait_ms,
    )


def normalize_rows(vecs: np.ndarray) -> np.ndarray:
    """L2 normalize each row; truncated 768 dim vectors from the provider are not unit length."""
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return (vecs / np.where(norms == 0, 1, norms)).astype(np.float32)


def embed(
    texts: list[str],
    *,
    trace: "Trace | None" = None,
    kind: Literal["document", "query"] = "document",
) -> np.ndarray:
    """(n, 768) float32, L2 normalized, sent in batches of 100. Cached per text.

    kind says whether the texts are searched ("document") or are questions ("query"); models that
    embed the two differently get their prefix from models.toml, others ignore it.
    """
    if trace is not None:
        trace.check_budget()
    spec = models()["embed"]
    prefix = spec.query_prefix if kind == "query" else spec.document_prefix
    texts = [prefix + t for t in texts]
    dims = spec.dims or 768
    keys = [request_key({"model": spec.model, "input": t, "dimensions": dims}) for t in texts]
    hits = cache.get_many(keys) if use_cache else {}
    out = np.zeros((len(texts), dims), dtype=np.float32)

    cached_idx = [i for i, k in enumerate(keys) if k in hits]
    for i in cached_idx:
        out[i] = np.frombuffer(base64.b64decode(hits[keys[i]]["response"]["b64"]), dtype=np.float32)
    if cached_idx and trace is not None:
        tokens_in = sum(hits[keys[i]]["tokens_in"] for i in cached_idx)
        latency_ms = sum(hits[keys[i]]["latency_ms"] for i in cached_idx)
        trace.add_llm(_embed_result(spec, tokens_in, latency_ms, cached=True, retries=0, wait_ms=0))

    missing = [i for i, k in enumerate(keys) if k not in hits]
    size = min(EMBED_BATCH, spec.texts_per_minute or EMBED_BATCH)
    for start in range(0, len(missing), size):
        idx = missing[start : start + size]
        batch = [texts[i] for i in idx]
        paced_ms = pace(len(batch), spec.texts_per_minute)
        body, latency_ms, retries, wait_ms = _post(
            spec, "embeddings", {"model": spec.model, "input": batch, "dimensions": dims}
        )
        wait_ms += paced_ms  # pacing is throttle wait, never latency
        # Gemini omits "index"; a stable sort keeps the response order then
        rows = sorted(body["data"], key=lambda d: d.get("index", 0))
        vecs = np.array([row["embedding"] for row in rows], dtype=np.float32)
        if vecs.shape != (len(batch), dims):
            raise ProviderError(f"{spec.model}: expected {(len(batch), dims)}, got {vecs.shape}")
        vecs = normalize_rows(vecs)
        out[idx] = vecs
        usage = body.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens") or 0) or estimate_tokens(batch)
        if use_cache:
            per_text_ms = latency_ms // len(batch)
            cache.put_many(
                [
                    {
                        "key": keys[i],
                        "role": "embed",
                        "model": spec.model,
                        "response": {"b64": base64.b64encode(vec.tobytes()).decode()},
                        "tokens_in": estimate_tokens([texts[i]]),
                        "tokens_out": 0,
                        "latency_ms": per_text_ms,
                    }
                    for i, vec in zip(idx, vecs, strict=True)
                ]
            )
        if trace is not None:
            result = _embed_result(spec, tokens_in, latency_ms, False, retries, wait_ms)
            trace.add_llm(replace(result, estimated=not usage.get("prompt_tokens")))
    return out


def pace(n_texts: int, per_minute: int | None) -> int:
    """Wait until n_texts more stay under the per minute budget over 60 s; returns ms waited.

    A refused request still counts against the free tier's daily quota, so waiting before a
    batch is cheaper than a 429 and a retry.
    """
    if not per_minute:
        return 0
    waited = 0.0
    while True:
        now = _now()
        _sent[:] = [(at, n) for at, n in _sent if now - at < 60.0]
        if sum(n for _, n in _sent) + n_texts <= per_minute or not _sent:
            _sent.append((now, n_texts))
            return int(waited * 1000)
        delay = 60.0 - (now - _sent[0][0]) + 0.5
        _sleep(delay)
        waited += delay


def _embed_result(
    spec: ModelSpec, tokens_in: int, latency_ms: int, cached: bool, retries: int, wait_ms: int
) -> LLMResult:
    return LLMResult(
        text="",
        role="embed",
        model=spec.model,
        tokens_in=tokens_in,
        tokens_out=0,
        cost_usd=cost_usd(spec, tokens_in, 0),
        latency_ms=latency_ms,
        cached=cached,
        estimated=True,
        retries=retries,
        wait_ms=wait_ms,
    )
