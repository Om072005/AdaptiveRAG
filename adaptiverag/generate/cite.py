from adaptiverag.types import Citation, Retrieved


def bind_citations(raw: str, retrieved: Retrieved) -> tuple[str, str, list[Citation]]:
    """Parse the model output into (short, text, citations), dropping out of range markers."""
    raise NotImplementedError
