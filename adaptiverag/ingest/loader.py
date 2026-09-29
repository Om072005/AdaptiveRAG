from typing import Any

from adaptiverag.types import Document


def load_hotpot(n_questions: int, seed: int = 7) -> tuple[list[Document], list[dict[str, Any]]]:
    """Documents = union of the sampled questions' context paragraphs, plus the questions."""
    raise NotImplementedError
