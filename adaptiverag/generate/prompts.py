from adaptiverag.types import Retrieved


def build_prompt(question: str, retrieved: Retrieved) -> list[dict[str, str]]:
    """Messages with numbered context blocks [1]..[k] in hit rank order."""
    raise NotImplementedError
