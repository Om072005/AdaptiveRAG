"""Generation: pick the model, ask it, bind citations, score confidence."""

from adaptiverag import llm
from adaptiverag.config import router_cfg
from adaptiverag.generate.cite import bind_citations, invalid_markers
from adaptiverag.generate.confidence import answer_confidence
from adaptiverag.generate.prompts import NOT_ENOUGH, build_prompt, context_blocks
from adaptiverag.generate.select import choose_model
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Answer, ModelSize, Retrieved, RouteDecision


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
        return Answer(NOT_ENOUGH, NOT_ENOUGH, [], "", "small", "no_context", 0.0, 0, 0, 0.0, 0)

    messages = build_prompt(question, retrieved)
    context_tokens = llm.estimate_tokens([context_blocks(retrieved)])
    if force_size:
        size, reason = force_size, f"forced:{force_size}"
    else:
        size, reason = choose_model(decision, retrieved, context_tokens)

    with trace.span("generate"):
        r = llm.chat(
            size, messages, trace=trace, max_tokens=int(router_cfg()["answer"]["max_tokens"])
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
