"""Answer confidence: is the answer grounded? A different signal from classifier confidence."""

import re

from adaptiverag.config import router_cfg
from adaptiverag.generate.cite import marker_numbers
from adaptiverag.generate.prompts import NOT_ENOUGH
from adaptiverag.types import Citation, Retrieved

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
NO_PATH_STRENGTH = 0.3


def citation_coverage(answer_text: str, citations: list[Citation]) -> float:
    """Share of explanation sentences carrying at least one valid [n] marker."""
    valid = {c.n for c in citations}
    explanation = answer_text.split(". ", 1)[1] if ". " in answer_text else ""
    sentences = [s for s in SENTENCE_END.split(explanation) if s.strip()]
    if not sentences:
        return 0.0
    cited = sum(1 for s in sentences if valid & set(marker_numbers(s)))
    return cited / len(sentences)


def retrieval_strength(retrieved: Retrieved, min_top_score: float) -> float:
    """Vector: top score against the threshold. Graph: did a path connect. Hybrid: the mean."""
    sources = {h.source for h in retrieved.hits}
    vector = min(1.0, retrieved.top_score / min_top_score) if min_top_score > 0 else 0.0
    graph = 1.0 if retrieved.path_found else NO_PATH_STRENGTH
    if "hybrid" in sources or {"vector", "graph"} <= sources:
        return (vector + graph) / 2
    if sources == {"graph"}:
        return graph
    return vector if retrieved.hits else 0.0


def answer_confidence(answer_text: str, citations: list[Citation], retrieved: Retrieved) -> float:
    """w_citation * citation coverage + w_retrieval * retrieval strength (0 if no answer)."""
    if answer_text.strip().lower().startswith(NOT_ENOUGH):
        return 0.0
    cfg = router_cfg()
    w = cfg["answer"]
    strength = retrieval_strength(retrieved, float(cfg["vector"]["min_top_score"]))
    score = (
        w["w_citation"] * citation_coverage(answer_text, citations) + w["w_retrieval"] * strength
    )
    return round(float(score), 4)
