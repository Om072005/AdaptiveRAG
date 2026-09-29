"""The one builder of the QueryResponse shape (contract section 6)."""

from typing import Any

from adaptiverag.types import QueryResult


def to_response(result: QueryResult, question: str) -> dict[str, Any]:
    """QueryResponse dict, also stored in traces.detail."""
    raise NotImplementedError


def response_from_trace(trace_id: str) -> dict[str, Any]:
    """Read traces.detail and validate it, used by the replay export."""
    raise NotImplementedError
