"""Question in, cited answer and saved trace out."""

from adaptiverag.types import Mode, ModelSize, QueryResult


def answer_query(
    question: str, mode: Mode = "auto", source: str = "cli", force_size: ModelSize | None = None
) -> QueryResult:
    """Route, retrieve, generate and save one trace."""
    raise NotImplementedError
