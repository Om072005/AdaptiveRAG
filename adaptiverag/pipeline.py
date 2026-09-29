"""Question in, cited answer and saved trace out; and judging a stored answer."""

from typing import Any

from adaptiverag.config import router_cfg
from adaptiverag.eval import judge
from adaptiverag.eval.run import store_judgement
from adaptiverag.generate.answer import synthesize
from adaptiverag.llm import BudgetExceeded
from adaptiverag.router.route import route_and_retrieve
from adaptiverag.serialize import response_from_trace, to_response
from adaptiverag.stores.db import conn
from adaptiverag.stores.traces import chunk_texts, queue_review, read_judgement
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import (
    Answer,
    Citation,
    Edge,
    GraphPath,
    Hit,
    Mode,
    ModelSize,
    QueryResult,
    Retrieved,
)


def answer_query(
    question: str, mode: Mode = "auto", source: str = "cli", force_size: ModelSize | None = None
) -> QueryResult:
    """Route, retrieve, generate and save one trace."""
    trace = Trace(question, mode, source)
    try:
        decision, retrieved = route_and_retrieve(question, mode, trace)
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


def answer_from_response(response: dict[str, Any]) -> tuple[Answer, Retrieved]:
    """Rebuild the Answer and Retrieved a stored response describes, with full chunk texts."""
    a, r = response["answer"], response["retrieval"]
    texts = chunk_texts([h["chunk_id"] for h in r["hits"]])
    hits = [
        Hit(
            h["chunk_id"],
            h["chunk_id"].split(":")[0],
            h["title"],
            texts.get(h["chunk_id"], h["snippet"]),
            h["score"],
            h["source"],
            h["rank"],
        )
        for h in r["hits"]
    ]
    names = {n["id"]: n["name"] for n in r["graph"]["nodes"]}
    edges = tuple(
        Edge(
            "",
            e["source"],
            names.get(e["source"], e["source"]),
            e["predicate"],
            e["target"],
            names.get(e["target"], e["target"]),
            e["chunk_id"],
            e["confidence"],
        )
        for e in r["graph"]["edges"]
    )
    paths = [GraphPath(edges, 0.0, r["path_found"])] if edges else []
    citations = [
        Citation(c["n"], c["chunk_id"], c["chunk_id"].split(":")[0], c["title"], c["snippet"])
        for c in a["citations"]
    ]
    answer = Answer(
        a["short"],
        a["text"],
        citations,
        a["model"],
        a["size"],
        a["select_reason"],
        a["confidence"],
        0,
        0,
        0.0,
        0,
    )
    return answer, Retrieved(hits, paths, [], r["top_score"], r["path_found"], 0)


def judge_answer(trace_id: str) -> dict[str, Any]:
    """Judge a stored answer once. A second call returns the stored judgement, no model call."""
    stored = read_judgement(trace_id)
    flag_below = float(router_cfg()["judge"]["flag_below"])
    if stored is None:
        response = response_from_trace(trace_id)  # KeyError if the trace does not exist
        answer, retrieved = answer_from_response(response)
        judge_trace = Trace(response["question"], response["route"]["requested"], "demo")
        verdict = judge.judge(response["question"], answer, retrieved, judge_trace)
        low = [
            ("judge_below_threshold", m, float(verdict[m]))
            for m in ("faithfulness", "relevance", "completeness")
            if verdict[m] < flag_below
        ]
        with conn() as c:
            store_judgement(c, trace_id, verdict, judge_trace)
            queue_review(c, trace_id, low)
            if low:
                c.execute("update traces set flagged = true where trace_id = %s", (trace_id,))
        stored = read_judgement(trace_id)
        assert stored is not None
    scores = [stored[m] for m in ("faithfulness", "relevance", "completeness")]
    return {
        **stored,
        "cost_usd": float(stored["cost_usd"]),
        "flagged": any(s < flag_below for s in scores),
    }
