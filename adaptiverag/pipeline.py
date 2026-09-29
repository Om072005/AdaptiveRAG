"""Question in, cited answer and saved trace out."""

from adaptiverag.config import router_cfg
from adaptiverag.generate.answer import synthesize
from adaptiverag.llm import BudgetExceeded
from adaptiverag.serialize import to_response
from adaptiverag.stores import vector
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Mode, ModelSize, QueryResult, Retrieved, RouteDecision


def route_baseline(question: str, mode: Mode, trace: Trace) -> tuple[RouteDecision, Retrieved]:
    """Vector search only, until the router lands (graph on D6, auto on D8)."""
    if mode in ("graph", "hybrid"):
        raise NotImplementedError(f"mode {mode} arrives with the graph layer and the router")
    reason = "forced:vector" if mode == "vector" else "baseline:router not wired yet"
    decision = RouteDecision(mode, None, "vector", "vector", reasons=[reason])
    with trace.span("retrieve"):
        retrieved = vector.retrieve(question, int(router_cfg()["vector"]["k"]), trace)
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
