"""Question in, cited answer and saved trace out."""

from adaptiverag import llm
from adaptiverag.config import router_cfg
from adaptiverag.generate.answer import synthesize
from adaptiverag.llm import BudgetExceeded
from adaptiverag.router.hybrid import merge_rerank
from adaptiverag.serialize import to_response
from adaptiverag.stores import graph, vector
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Mode, ModelSize, QueryResult, Retrieved, Route, RouteDecision


def retrieve_forced(question: str, route: Route, trace: Trace) -> Retrieved:
    """One backend, or both merged for hybrid. The question is embedded once and reused."""
    cfg = router_cfg()
    k = int(cfg["vector"]["k"])
    qvec = llm.embed([question], trace=trace)[0]
    if route == "vector":
        return vector.retrieve(question, k, trace, qvec)
    if route == "graph":
        return graph.retrieve(question, k, trace, qvec)
    v = vector.retrieve(question, k, trace, qvec)
    g = graph.retrieve(question, k, trace, qvec)
    hits = merge_rerank(v.hits, g.hits, qvec, int(cfg["hybrid"]["k"]), trace)
    trace.set(n_results=len(hits), top_score=v.top_score, path_found=g.path_found)
    return Retrieved(hits, g.paths, g.seeds, v.top_score, g.path_found, v.latency_ms + g.latency_ms)


def route_baseline(question: str, mode: Mode, trace: Trace) -> tuple[RouteDecision, Retrieved]:
    """Forced modes go to their backend; auto stays on vector until the router lands (D8)."""
    route: Route = "vector" if mode == "auto" else mode
    reason = "baseline:router not wired yet" if mode == "auto" else f"forced:{mode}"
    decision = RouteDecision(mode, None, route, route, reasons=[reason])
    with trace.span("retrieve"):
        retrieved = retrieve_forced(question, route, trace)
    return decision, retrieved


def answer_query(
    question: str, mode: Mode = "auto", source: str = "cli", force_size: ModelSize | None = None
) -> QueryResult:
    """Route, retrieve, generate and save one trace."""
    trace = Trace(question, mode, source)
    try:
        decision, retrieved = route_baseline(question, mode, trace)
        answer = synthesize(question, decision, retrieved, trace, force_size)
    except BudgetExceeded:
        # the cost spiral guard fired: keep the evidence, then let the caller see it
        trace.note(budget_exceeded=True)
        trace.save()
        raise

    flagged = answer.confidence < float(router_cfg()["answer"]["min_confidence"])
    trace.set(
        route_initial=decision.initial,
        route_taken=decision.final,
        fallbacks=decision.fallbacks,
        answer_confidence=answer.confidence,
        flagged=flagged,
    )
    row = trace.row()
    result = QueryResult(
        trace_id=trace.trace_id,
        decision=decision,
        retrieved=retrieved,
        answer=answer,
        total_cost_usd=float(row["total_cost_usd"]),
        total_latency_ms=int(row["total_latency_ms"]),
        flagged=flagged,
    )
    # every trace carries the full API response, so any stored run replays without a model call
    trace.note(**to_response(result, question, trace))
    trace.save()
    return result
