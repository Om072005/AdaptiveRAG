"""The README router flowchart as a pure decision table (no IO)."""

from typing import Any

from adaptiverag.types import Classification, Mode, Retrieved, Route, Seed


def decide_initial(
    mode: Mode,
    c: Classification | None,
    seeds: list[Seed],
    budget_left_usd: float,
    cfg: dict[str, Any],
) -> tuple[Route, list[str]]:
    raise NotImplementedError


def needs_fallback(route: Route, r: Retrieved, cfg: dict[str, Any]) -> str | None:
    """For example 'vector_low_score', or None."""
    raise NotImplementedError
