"""The one builder of the QueryResponse shape (contract section 6)."""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from adaptiverag.types import GraphPath, Mode, QType, QueryResult, Route, Seed

if TYPE_CHECKING:
    from adaptiverag.telemetry.trace import Trace

SNIPPET_CHARS = 600


class Strict(BaseModel):
    # traces.detail also carries notes (citation_errors, spans); validation keeps only the contract
    model_config = ConfigDict(extra="ignore")


class CitationOut(Strict):
    n: int
    title: str
    snippet: str = Field(max_length=SNIPPET_CHARS)
    chunk_id: str


class AnswerOut(Strict):
    short: str
    text: str
    model: str
    size: Literal["small", "large"]
    select_reason: str
    confidence: float
    flagged: bool
    citations: list[CitationOut]


class RouteOut(Strict):
    requested: Mode
    label: QType | None
    label_confidence: float | None
    method: str | None
    initial: Route
    final: Route
    fallbacks: list[str]
    reasons: list[str]


class HitOut(Strict):
    rank: int
    title: str
    snippet: str = Field(max_length=SNIPPET_CHARS)
    score: float
    source: Route
    chunk_id: str


class NodeOut(Strict):
    id: str
    name: str
    type: str
    seed: bool


class EdgeOut(Strict):
    source: str
    target: str
    predicate: str
    chunk_id: str
    confidence: float


class GraphOut(Strict):
    nodes: list[NodeOut]
    edges: list[EdgeOut]


class RetrievalOut(Strict):
    hits: list[HitOut]
    graph: GraphOut
    top_score: float
    path_found: bool


class SpanOut(Strict):
    name: str
    ms: int


class CostOut(Strict):
    classifier: float
    generation: float
    total: float


class TraceOut(Strict):
    spans: list[SpanOut]
    tokens_in: int
    tokens_out: int
    cost: CostOut
    total_ms: int
    throttle_wait_ms: int
    cached: bool


class LiveOut(Strict):
    budget_left_usd: float


class QueryResponse(Strict):
    trace_id: str
    question: str
    answer: AnswerOut
    route: RouteOut
    retrieval: RetrievalOut
    trace: TraceOut
    live: LiveOut | None = None


def graph_block(paths: list[GraphPath], seeds: list[Seed]) -> dict[str, Any]:
    """Nodes and edges of the returned paths; seed entities are flagged."""
    seed_types = {s.canonical_id: s.type for s in seeds}
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for path in paths:
        for e in path.edges:
            for node_id, name in ((e.subject_id, e.subject_name), (e.object_id, e.object_name)):
                nodes.setdefault(
                    node_id,
                    {
                        "id": node_id,
                        "name": name,
                        "type": seed_types.get(node_id, ""),
                        "seed": node_id in seed_types,
                    },
                )
            edge = {
                "source": e.subject_id,
                "target": e.object_id,
                "predicate": e.predicate,
                "chunk_id": e.chunk_id,
                "confidence": e.confidence,
            }
            if edge not in edges:
                edges.append(edge)
    for s in seeds:  # a seed with no path is still shown, marked as a seed
        nodes.setdefault(
            s.canonical_id, {"id": s.canonical_id, "name": s.name, "type": s.type, "seed": True}
        )
    return {"nodes": list(nodes.values()), "edges": edges}


def to_response(result: QueryResult, question: str, trace: "Trace | None" = None) -> dict[str, Any]:
    """QueryResponse dict, stored in traces.detail. `trace` adds spans, waits and cost split."""
    a, d, r = result.answer, result.decision, result.retrieved
    c = d.classification
    row = trace.row() if trace is not None else {}
    response = {
        "trace_id": result.trace_id,
        "question": question,
        "answer": {
            "short": a.short,
            "text": a.text,
            "model": a.model,
            "size": a.size,
            "select_reason": a.select_reason,
            "confidence": a.confidence,
            "flagged": result.flagged,
            "citations": [
                {
                    "n": x.n,
                    "title": x.title,
                    "snippet": x.snippet[:SNIPPET_CHARS],
                    "chunk_id": x.chunk_id,
                }
                for x in a.citations
            ],
        },
        "route": {
            "requested": d.requested,
            "label": c.label if c else None,
            "label_confidence": c.confidence if c else None,
            "method": c.method if c else None,
            "initial": d.initial,
            "final": d.final,
            "fallbacks": list(d.fallbacks),
            "reasons": list(d.reasons),
        },
        "retrieval": {
            "hits": [
                {
                    "rank": h.rank,
                    "title": h.title,
                    "snippet": h.text[:SNIPPET_CHARS],
                    "score": h.score,
                    "source": h.source,
                    "chunk_id": h.chunk_id,
                }
                for h in sorted(r.hits, key=lambda h: h.rank)
            ],
            "graph": graph_block(r.paths, r.seeds),
            "top_score": r.top_score,
            "path_found": r.path_found,
        },
        "trace": {
            "spans": list(trace.spans) if trace is not None else [],
            "tokens_in": row.get("tokens_in", a.tokens_in),
            "tokens_out": row.get("tokens_out", a.tokens_out),
            "cost": {
                "classifier": float(row.get("classifier_cost_usd", c.cost_usd if c else 0.0)),
                "generation": float(row.get("generation_cost_usd", a.cost_usd)),
                "total": result.total_cost_usd,
            },
            "total_ms": result.total_latency_ms,
            "throttle_wait_ms": row.get("throttle_wait_ms", 0),
            "cached": row.get("cached", False),
        },
        "live": None,
    }
    return QueryResponse.model_validate(response).model_dump()


def response_from_trace(trace_id: str) -> dict[str, Any]:
    """Read traces.detail and validate it, used by the replay export."""
    from adaptiverag.stores.traces import read_detail

    detail = read_detail(trace_id)
    if detail is None:
        raise KeyError(f"no trace {trace_id}")
    return QueryResponse.model_validate(detail).model_dump()
