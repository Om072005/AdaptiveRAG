from adaptiverag.types import Citation, Retrieved


def answer_confidence(answer_text: str, citations: list[Citation], retrieved: Retrieved) -> float:
    """Weighted citation coverage plus retrieval strength; 0 for not enough context."""
    raise NotImplementedError
