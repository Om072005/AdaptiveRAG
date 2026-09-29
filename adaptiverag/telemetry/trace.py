"""Per query trace: spans, the LLM call ledger and the traces row."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from adaptiverag.types import LLMResult, Mode


class Trace:
    def __init__(self, question: str, mode: Mode, source: str) -> None:
        self.question = question
        self.mode = mode
        self.source = source

    @contextmanager
    def span(self, name: str) -> Iterator[None]:
        """Record {name, ms}. Names: classify, link, retrieve, merge, generate, judge."""
        raise NotImplementedError
        yield

    def add_llm(self, r: LLMResult) -> None:
        """Append to the call ledger; raises BudgetExceeded past the per query cap."""
        raise NotImplementedError

    def set(self, **fields: Any) -> None:
        """Set any traces column."""
        raise NotImplementedError

    def save(self) -> str:
        """Insert traces and llm_calls in one transaction, return the trace_id."""
        raise NotImplementedError
