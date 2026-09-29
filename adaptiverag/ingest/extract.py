from typing import Any

from adaptiverag.types import Chunk, Triple


def extract_triples(
    chunks: list[Chunk], doc_text: dict[str, str]
) -> tuple[list[Triple], list[dict[str, Any]]]:
    """(kept, rejects); 4 chunks per call, role 'extract', json mode."""
    raise NotImplementedError
