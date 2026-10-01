"""Per query trace: spans, the LLM call ledger and the traces row."""

import logging
import subprocess
import time
import uuid
from collections.abc import Callable, Collection, Iterator
from contextlib import contextmanager
from typing import Any

from adaptiverag.config import ROOT, config_hash, limits
from adaptiverag.llm import BudgetExceeded
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

# Receives each step of a query as it finishes, and each piece of the streamed answer: the CLI
# prints them, the API streams them to the local page. Every event is a JSON ready dict.
Listener = Callable[[dict[str, Any]], None]
log = logging.getLogger(__name__)


class ListenerStop(Exception):
    """Raised by a listener to stop the query, for example when the page that asked has gone."""


class Trace:
    def __init__(
        self, question: str, mode: Mode, source: str, listener: Listener | None = None
    ) -> None:
        self.trace_id = str(uuid.uuid4())
        self.listener = listener
        self.question = question
        self.mode = mode
        self.source = source
        self.fields: dict[str, Any] = {}
        self.spans: list[dict[str, Any]] = []
        self.calls: list[LLMResult] = []
        self.max_calls = int(limits()["max_llm_calls_per_query"])
        self._started = time.perf_counter()

    @contextmanager
    def span(self, name: str) -> Iterator[None]:
        """Record {name, ms}. Names: classify, link, retrieve, merge, generate, judge."""
        started = time.perf_counter()
        try:
            yield
        finally:
            self.spans.append({"name": name, "ms": int((time.perf_counter() - started) * 1000)})

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._started) * 1000)

    def emit(self, step: str, **data: Any) -> None:
        """Tell the listener, if any, that a step finished and what it found."""
        self._tell({"type": "step", "step": step, "at_ms": self.elapsed_ms(), **data})

    def delta(self, kind: str, text: str) -> None:
        """Pass one streamed piece of the answer ('thinking' or 'answer') to the listener."""
        self._tell({"type": "delta", "kind": kind, "text": text})

    def _tell(self, event: dict[str, Any]) -> None:
        """A listener that fails is logged and the query goes on; only ListenerStop stops it."""
        if self.listener is None:
            return
        try:
            self.listener(event)
        except ListenerStop:
            raise
        except Exception:
            log.exception("a step listener failed on %s; the query goes on", event.get("type"))

    def last_call(self) -> LLMResult | None:
        return self.calls[-1] if self.calls else None

    def check_budget(self) -> None:
        """Raise BudgetExceeded if one more call would pass the per query cap."""
        if len(self.calls) >= self.max_calls:
            raise BudgetExceeded(f"trace {self.trace_id} already made {len(self.calls)} LLM calls")

    def add_llm(self, r: LLMResult) -> None:
        """Append to the call ledger; raises BudgetExceeded past the per query cap."""
        self.check_budget()
        self.calls.append(r)

    def set(self, **fields: Any) -> None:
        """Set any traces column."""
        unknown = set(fields) - SETTABLE
        if unknown:
            raise ValueError(f"not a settable traces column: {', '.join(sorted(unknown))}")
        self.fields.update(fields)

    def note(self, **values: Any) -> None:
        """Merge values into traces.detail (citation errors, a budget stop, and so on)."""
        self.fields["detail"] = {**self.fields.get("detail", {}), **values}

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
        row = self.row()  # latency is measured first, so the git calls below never count
        sha, dirty = git_state()
        row.setdefault("git_sha", sha)
        row.setdefault("git_dirty", dirty)
        row.setdefault("config_hash", config_hash())
        store.insert(row, self.call_rows())
        return self.trace_id


def git_state() -> tuple[str | None, bool | None]:
    """(commit sha, dirty tree) of the answering code, or (None, None) outside a checkout."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None, None
    return sha, bool(status.strip())
