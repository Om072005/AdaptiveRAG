"""web/src/fixtures/query.json is a real stored response, and the pydantic QueryResponse, the page's
TypeScript QueryResponse and the fixture all name the same fields. Any drift fails here."""

import json
import re
import uuid
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from adaptiverag.config import ROOT
from adaptiverag.serialize import QueryResponse

FIXTURE = ROOT / "web" / "src" / "fixtures" / "query.json"
TYPES_TS = ROOT / "web" / "src" / "types.ts"


def model_fields(model: type[BaseModel], prefix: str = "") -> set[str]:
    """Dotted field paths of a pydantic model, following nested models and lists of models."""
    paths: set[str] = set()
    for name, field in model.model_fields.items():
        path = f"{prefix}{name}"
        paths.add(path)
        for arg in [field.annotation, *get_args(field.annotation)]:
            inner = get_args(arg)[0] if get_origin(arg) is list else arg
            if isinstance(inner, type) and issubclass(inner, BaseModel):
                paths |= model_fields(inner, f"{path}.")
    return paths


def json_fields(value: Any, prefix: str = "") -> set[str]:
    """Dotted key paths of a JSON value; list items share one path."""
    if isinstance(value, list):
        return set().union(*(json_fields(v, prefix) for v in value)) if value else set()
    if not isinstance(value, dict):
        return set()
    paths: set[str] = set()
    for key, v in value.items():
        paths.add(f"{prefix}{key}")
        paths |= json_fields(v, f"{prefix}{key}.")
    return paths


def ts_field_names() -> set[str]:
    """Every field name declared in the QueryResponse type of web/src/types.ts."""
    source = TYPES_TS.read_text(encoding="utf-8")
    block = source[source.index("export type QueryResponse") :]
    block = block[: block.index("\n}\n") + 2]
    block = re.sub(r"//.*", "", block)
    return set(re.findall(r"(\w+)\??\s*:", block))


def test_fixture_is_a_real_response_that_validates() -> None:
    body = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert QueryResponse.model_validate(body).model_dump() == body
    uuid.UUID(body["trace_id"])  # taken from a stored trace, not written by hand
    assert body["retrieval"]["hits"] and body["answer"]["citations"]


def test_fixture_uses_exactly_the_model_fields() -> None:
    body = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # the fixture has no graph nodes or edges and live is null, so only compare what it contains
    assert json_fields(body) <= model_fields(QueryResponse)
    assert model_fields(QueryResponse) - json_fields(body) <= {
        "retrieval.graph.nodes.id",
        "retrieval.graph.nodes.name",
        "retrieval.graph.nodes.type",
        "retrieval.graph.nodes.seed",
        "retrieval.graph.edges.source",
        "retrieval.graph.edges.target",
        "retrieval.graph.edges.predicate",
        "retrieval.graph.edges.chunk_id",
        "retrieval.graph.edges.confidence",
        "live.budget_left_usd",
    }


def test_page_type_names_the_same_fields_as_the_model() -> None:
    python_names = {path.rsplit(".", 1)[-1] for path in model_fields(QueryResponse)}
    assert ts_field_names() == python_names
