"""The README router flowchart as a pure decision table (no IO). Rows are in 01_CONTRACTS.md."""

from typing import Any

from adaptiverag.types import Classification, Mode, Retrieved, Route, Seed

RELATIONAL = ("multi_hop", "comparison")


def decide_initial(
    mode: Mode,
    c: Classification | None,
    seeds: list[Seed],
    budget_left_usd: float,
    cfg: dict[str, Any],
) -> tuple[Route, list[str]]:
    """First route and one reason per decision diamond passed. cfg is router.toml."""
    if mode != "auto":
        return mode, [f"forced:{mode}"]  # row 1
    if c is None:
        raise ValueError("auto mode needs a classification")
    if c.confidence < cfg["classifier"]["min_confidence"]:
        return "hybrid", [f"ambiguous:{c.label} {c.confidence:.2f}"]  # row 2
    if c.label not in RELATIONAL:
        return "vector", ["no_relational_structure"]  # row 3
    if not any(s.score >= cfg["graph"]["min_seed_score"] for s in seeds):
        return "vector", ["entities_not_in_graph"]  # row 4
    return "graph", [f"relational:{c.label}"]  # row 5


def needs_fallback(route: Route, r: Retrieved, cfg: dict[str, Any]) -> str | None:
    """For example 'vector_low_score', or None. Hybrid is the fallback, so it never falls back."""
    if route == "vector" and r.top_score < cfg["vector"]["min_top_score"]:
        return "vector_low_score"  # row F1
    if route == "graph" and not r.path_found:
        return "graph_no_path"  # row F2
    return None
