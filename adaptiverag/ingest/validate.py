from adaptiverag.types import Triple


def validate(t: Triple, source_text: str) -> str | None:
    """None = ok, else a reject reason from the extraction_rejects schema."""
    raise NotImplementedError
