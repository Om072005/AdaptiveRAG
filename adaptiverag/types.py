"""Shared dataclasses from the contract (01_CONTRACTS.md section 2). Change only by announcement."""

from dataclasses import dataclass, field
from typing import Literal

Strategy = Literal["fixed", "sentence", "semantic"]
QType = Literal["single_hop", "multi_hop", "comparison"]
Route = Literal["vector", "graph", "hybrid"]
Mode = Literal["auto", "vector", "graph", "hybrid"]
Role = Literal["small", "large", "extract", "judge", "classify", "embed"]
ModelSize = Literal["small", "large"]


@dataclass(frozen=True)
class Document:
    doc_id: str
    source: str
    title: str
    text: str
    sentences: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    strategy: Strategy
    ord: int
    start: int
    end: int
    text: str
    n_words: int


@dataclass(frozen=True)
class Hit:
    """One retrieved chunk, whatever produced it."""

    chunk_id: str
    doc_id: str
    title: str
    text: str
    score: float  # cosine for vector, path score for graph, fused score for hybrid
    source: Route
    rank: int  # starts at 1


@dataclass(frozen=True)
class Triple:
    """Raw extraction output, before entity resolution."""

    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    chunk_id: str
    evidence_start: int
    evidence_end: int
    confidence: float


@dataclass(frozen=True)
class Edge:
    rel_id: str
    subject_id: str
    subject_name: str
    predicate: str
    object_id: str
    object_name: str
    chunk_id: str
    confidence: float


@dataclass(frozen=True)
class GraphPath:
    edges: tuple[Edge, ...]
    score: float
    connects_seeds: bool


@dataclass(frozen=True)
class Seed:
    canonical_id: str
    name: str
    type: str
    score: float
    matched: str


@dataclass
class Classification:
    label: QType
    confidence: float
    probs: dict[str, float]
    method: str
    cost_usd: float
    latency_ms: int


@dataclass
class Retrieved:
    hits: list[Hit]
    paths: list[GraphPath]
    seeds: list[Seed]
    top_score: float  # best vector cosine, or best path score for graph only
    path_found: bool
    latency_ms: int


@dataclass
class RouteDecision:
    requested: Mode
    classification: Classification | None
    initial: Route
    final: Route
    fallbacks: list[str] = field(default_factory=list)  # e.g. ['vector_low_score->hybrid']
    reasons: list[str] = field(default_factory=list)  # one short line per decision diamond passed


@dataclass(frozen=True)
class Citation:
    n: int
    chunk_id: str
    doc_id: str
    title: str
    snippet: str


@dataclass
class Answer:
    short: str  # the span used for EM/F1
    text: str  # short answer plus one or two sentences with [n] markers
    citations: list[Citation]
    model: str
    size: ModelSize
    select_reason: str
    confidence: float
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int


@dataclass(frozen=True)
class LLMResult:
    """latency_ms is the successful attempt only; 429 backoff goes to wait_ms."""

    text: str
    role: Role
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    cached: bool
    estimated: bool
    retries: int
    wait_ms: int


@dataclass
class QueryResult:
    trace_id: str
    decision: RouteDecision
    retrieved: Retrieved
    answer: Answer
    total_cost_usd: float
    total_latency_ms: int
    flagged: bool
