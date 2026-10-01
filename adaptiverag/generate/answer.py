"""Generation: pick the model, ask it, bind citations, score confidence."""

from adaptiverag import llm
from adaptiverag.config import models, router_cfg
from adaptiverag.generate.cite import bind_citations, invalid_markers
from adaptiverag.generate.confidence import answer_confidence
from adaptiverag.generate.prompts import NOT_ENOUGH, build_prompt, context_blocks
from adaptiverag.generate.select import choose_model
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Answer, ModelSize, Retrieved, RouteDecision


def pick_size(
    decision: RouteDecision, retrieved: Retrieved, force_size: ModelSize | None
) -> tuple[ModelSize, str]:
    """The selector's choice, or the forced size. When the local server answers and lacks the
    large model (a demo machine without it), the small one answers and the reason says so; a
    forced size is never changed, so an eval run fails rather than measure the wrong model."""
    if force_size:
        return force_size, f"forced:{force_size}"
    context_tokens = llm.estimate_tokens([context_blocks(retrieved)])
    size, reason = choose_model(decision, retrieved, context_tokens)
    if size == "large" and llm.missing(models()["large"]):
        return "small", f"small:{models()['large'].model} not installed ({reason})"
    return size, reason


def synthesize(
    question: str,
    decision: RouteDecision,
    retrieved: Retrieved,
    trace: Trace,
    force_size: ModelSize | None = None,
) -> Answer:
    """Pick the model, generate, bind citations and score answer confidence."""
    if not retrieved.hits:
        # nothing to ground an answer in: say so without paying for a model call
        trace.set(select_reason="no_context")
        trace.emit("model", size=None, model=None, reason="no_context")
        return Answer(NOT_ENOUGH, NOT_ENOUGH, [], "", "small", "no_context", 0.0, 0, 0, 0.0, 0)

    messages = build_prompt(question, retrieved)
    size, reason = pick_size(decision, retrieved, force_size)
    trace.emit("model", size=size, model=models()[size].model, reason=reason)

    with trace.span("generate"):
        r = llm.chat(
            size,
            messages,
            trace=trace,
            max_tokens=int(router_cfg()["answer"]["max_tokens"]),
            on_delta=trace.delta if trace.listener else None,
        )
    if trace.listener:
        trace.emit(
            "generated",
            model=r.model,
            tokens_in=r.tokens_in,
            tokens_out=r.tokens_out,
            ms=r.latency_ms,
            cached=r.cached,
            processor=llm.processor(models()[size]),
        )
    short, text, citations = bind_citations(r.text, retrieved)
    errors = invalid_markers(r.text, len(retrieved.hits))
    if errors:
        trace.note(citation_errors=errors)
    trace.set(model_selected=r.model, select_reason=reason)
    return Answer(
        short=short,
        text=text,
        citations=citations,
        model=r.model,
        size=size,
        select_reason=reason,
        confidence=answer_confidence(text, citations, retrieved),
        tokens_in=r.tokens_in,
        tokens_out=r.tokens_out,
        cost_usd=r.cost_usd,
        latency_ms=r.latency_ms,
    )
