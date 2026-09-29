from typing import Any

from adaptiverag.types import Triple


def normalize_name(s: str) -> str:
    raise NotImplementedError


def blocking_key(s: str) -> str:
    raise NotImplementedError


def resolve(
    triples: list[Triple],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """(entities, aliases, relations) rows."""
    raise NotImplementedError
