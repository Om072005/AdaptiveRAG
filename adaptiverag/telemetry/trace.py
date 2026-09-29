"""Per query trace: spans, the LLM call ledger and the traces row."""

import time
import uuid
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from typing import Any

from adaptiverag.stores import traces as store
from adaptiverag.types import LLMResult, Mode

# traces columns a caller may set; trace_id, question, mode and source come from the constructor
SETTABLE = {
    "classifier_label",
    "classifier_confidence",
    "classifier_method",
    "route_initial",
    "route_taken",
    "fallbacks",
    "retrieval_latency_ms",
    "n_results",
    "top_score",
    "path_found",
    "model_selected",
    "select_reason",
    "total_latency_ms",
    "answer_confidence",
    "flagged",
    "git_sha",
    "git_dirty",
    "config_hash",
    "detail",
}
GENERATION_ROLES = {"small", "large"}


class Trace:
    def __init__(self, question: str, mode: Mode, source: str) -> None:
        self.trace_id = str(uuid.uuid4())
        self.question = question
        self.mode = mode
        self.source = source
        self.fields: dict[str, Any] = {}
        self.spans: list[dict[str, Any]] = []
        self.calls: list[LLMResult] = []
        self._started = time.perf_counter()

    @contextmanager
    def span(self, name: str) -> Iterator[None]:
        """Record {name, ms}. Names: classify, link, retrieve, merge, generate, judge."""
        started = time.perf_counter()
        try:
            yield
        finally:
            self.spans.append({"name": name, "ms": int((time.perf_counter() - started) * 1000)})

    def add_llm(self, r: LLMResult) -> None:
        """Append to the call ledger."""
        self.calls.append(r)

    def set(self, **fields: Any) -> None:
        """Set any traces column."""
        unknown = set(fields) - SETTABLE
        if unknown:
            raise ValueError(f"not a settable traces column: {', '.join(sorted(unknown))}")
        self.fields.update(fields)

    def cost_by(self, roles: Collection[str]) -> float:
        return round(sum(c.cost_usd for c in self.calls if c.role in roles), 8)

    def row(self) -> dict[str, Any]:
        """The traces row: what callers set plus totals computed from the ledger."""
        wait_ms = sum(c.wait_ms for c in self.calls)
        elapsed_ms = int((time.perf_counter() - self._started) * 1000)
        # A cache hit takes a few ms; count its original latency so a rerun never looks faster.
        cached_ms = sum(c.latency_ms for c in self.calls if c.cached)
        generation = [c for c in self.calls if c.role in GENERATION_ROLES]
        detail = {**self.fields.get("detail", {}), "spans": self.spans}
        row: dict[str, Any] = {
            "total_latency_ms": max(0, elapsed_ms - wait_ms) + cached_ms,
            **self.fields,
            "trace_id": self.trace_id,
            "question": self.question,
            "mode": self.mode,
            "source": self.source,
            "route_taken": self.fields.get("route_taken", self.mode if self.mode != "auto" else ""),
            "tokens_in": sum(c.tokens_in for c in generation),
            "tokens_out": sum(c.tokens_out for c in generation),
            "classifier_cost_usd": self.cost_by({"classify"}),
            "generation_cost_usd": self.cost_by(GENERATION_ROLES),
            "eval_cost_usd": self.cost_by({"judge"}),
            "total_cost_usd": round(sum(c.cost_usd for c in self.calls), 8),
            "throttle_wait_ms": wait_ms,
            "cached": bool(self.calls) and all(c.cached for c in self.calls),
            "detail": detail,
        }
        return row

    def call_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "trace_id": self.trace_id,
                "role": c.role,
                "model": c.model,
                "tokens_in": c.tokens_in,
                "tokens_out": c.tokens_out,
                "cost_usd": c.cost_usd,
                "latency_ms": c.latency_ms,
                "cached": c.cached,
                "estimated": c.estimated,
                "retries": c.retries,
                "wait_ms": c.wait_ms,
            }
            for c in self.calls
        ]

    def save(self) -> str:
        """Insert traces and llm_calls in one transaction, return the trace_id."""
        store.insert(self.row(), self.call_rows())
        return self.trace_id
