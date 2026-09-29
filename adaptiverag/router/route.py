"""The router: classify, link, pick a route from the decision table, retrieve, fall back once."""

import math

import numpy as np

from adaptiverag import llm
from adaptiverag.config import router_cfg
from adaptiverag.router.classify import classify
from adaptiverag.router.hybrid import merge_rerank
from adaptiverag.router.policy import decide_initial, needs_fallback
from adaptiverag.stores import db, graph, vector
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Classification, Mode, Retrieved, Route, RouteDecision, Seed

# The only query budget in the plan is the live mode's daily one (a stretch goal, not built), so
# nothing else runs near a cap and decision table row 6 stays idle outside it.
NO_BUDGET_LIMIT = math.inf


def merged(v: Retrieved, g: Retrieved, qvec: np.ndarray, trace: Trace) -> Retrieved:
    """Hybrid: both backends fused and re-ranked; vector top score, graph paths and seeds."""
    hits = merge_rerank(v.hits, g.hits, qvec, int(router_cfg()["hybrid"]["k"]), trace)
    latency_ms = v.latency_ms + g.latency_ms
    trace.set(
        n_results=len(hits),
        top_score=v.top_score,
        path_found=g.path_found,
        retrieval_latency_ms=latency_ms,
    )
    return Retrieved(hits, g.paths, g.seeds, v.top_score, g.path_found, latency_ms)


def route_and_retrieve(question: str, mode: Mode, trace: Trace) -> tuple[RouteDecision, Retrieved]:
    """At most one fallback, always to hybrid."""
    cfg = router_cfg()
    k = int(cfg["vector"]["k"])
    qvec = llm.embed([question], trace=trace)[0]  # once, reused by every step below
    c: Classification | None = None
    seeds: list[Seed] | None = None

    def linked() -> list[Seed]:
        nonlocal seeds
        if seeds is None:
            seeds = graph.link_entities(question, qvec, trace)
        return seeds

    if mode == "auto":
        with trace.span("classify"):
            c = classify(question, qvec, trace)
        # classifier confidence has its own columns; answer confidence is set by the pipeline
        trace.set(
            classifier_label=c.label, classifier_confidence=c.confidence, classifier_method=c.method
        )
    initial, reasons = decide_initial(
        mode, c, linked() if mode == "auto" else [], NO_BUDGET_LIMIT, cfg
    )

    # each backend runs at most once: a fallback to hybrid reuses the result it already has
    have: dict[Route, Retrieved] = {}

    def run(route: Route) -> Retrieved:
        if route in have:
            return have[route]
        if route == "hybrid":
            have[route] = merged(run("vector"), run("graph"), qvec, trace)  # merge has its span
        elif route == "vector":
            with trace.span("retrieve"):
                have[route] = vector.retrieve(question, k, trace, qvec)
        else:
            found = linked()  # the link span stays outside the retrieve span
            with trace.span("retrieve"):
                have[route] = graph.retrieve_from_seeds(db.shared(), found, k, qvec, trace)
        return have[route]

    retrieved = run(initial)
    final, fallbacks = initial, []
    # forced routes never fall back (table row 1); hybrid is the fallback, so it never does either
    why = needs_fallback(initial, retrieved, cfg) if mode == "auto" else None
    if why:
        final, fallbacks = "hybrid", [f"{why}->hybrid"]
        retrieved = run("hybrid")
    trace.set(route_initial=initial, route_taken=final, fallbacks=fallbacks)
    return RouteDecision(mode, c, initial, final, fallbacks, reasons), retrieved
