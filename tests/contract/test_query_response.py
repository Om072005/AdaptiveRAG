"""The QueryResponse shape (contract section 6) built from a result, with and without a trace."""

import pytest
from pydantic import ValidationError

from adaptiverag.serialize import SNIPPET_CHARS, QueryResponse, graph_block, to_response
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import (
    Answer,
    Citation,
    Classification,
    Edge,
    GraphPath,
    Hit,
    LLMResult,
    QueryResult,
    Retrieved,
    RouteDecision,
    Seed,
)

LONG = "word " * 300


def result(with_graph: bool = False) -> QueryResult:
    hits = [
        Hit("d2:sentence:0", "d2", "Ankara", "Ankara is the capital.", 0.7, "vector", 2),
        Hit("d1:sentence:0", "d1", "Istanbul", LONG, 0.8, "vector", 1),
    ]
    edge = Edge("r1", "e_a", "Istanbul", "located_in", "e_b", "Turkey", "d1:sentence:0", 0.9)
    paths = [GraphPath((edge,), 0.8, True)] if with_graph else []
    seeds = [Seed("e_a", "Istanbul", "PLACE", 0.9, "Istanbul")] if with_graph else []
    c = Classification("multi_hop", 0.82, {"multi_hop": 0.82}, "logreg", 0.0, 1)
    decision = RouteDecision(
        "auto", c, "graph", "hybrid", ["graph_no_path->hybrid"], ["relational:multi_hop"]
    )
    answer = Answer(
        "Ankara",
        "Ankara. It is the capital [2].",
        [Citation(2, "d2:sentence:0", "d2", "Ankara", LONG)],
        "openai/gpt-oss-120b",
        "large",
        "large:route hybrid",
        0.8,
        900,
        40,
        0.0002,
        400,
    )
    return QueryResult(
        "t-1",
        decision,
        Retrieved(hits, paths, seeds, 0.8, with_graph, 20),
        answer,
        0.00021,
        1500,
        False,
    )


def test_response_validates_and_caps_snippets() -> None:
    body = to_response(result(), "What is the capital?")
    QueryResponse.model_validate(body)
    assert [h["rank"] for h in body["retrieval"]["hits"]] == [1, 2]
    assert len(body["retrieval"]["hits"][0]["snippet"]) == SNIPPET_CHARS
    assert len(body["answer"]["citations"][0]["snippet"]) == SNIPPET_CHARS
    assert body["route"] == {
        "requested": "auto",
        "label": "multi_hop",
        "label_confidence": 0.82,
        "method": "logreg",
        "initial": "graph",
        "final": "hybrid",
        "fallbacks": ["graph_no_path->hybrid"],
        "reasons": ["relational:multi_hop"],
    }
    assert body["live"] is None


def test_graph_block_flags_seeds_and_keeps_provenance() -> None:
    r = result(with_graph=True).retrieved
    g = graph_block(r.paths, r.seeds)
    assert {n["id"]: n["seed"] for n in g["nodes"]} == {"e_a": True, "e_b": False}
    assert g["edges"] == [
        {
            "source": "e_a",
            "target": "e_b",
            "predicate": "located_in",
            "chunk_id": "d1:sentence:0",
            "confidence": 0.9,
        }
    ]


def test_trace_block_comes_from_the_ledger() -> None:
    t = Trace("q", "auto", "cli")
    with t.span("retrieve"):
        pass
    t.add_llm(LLMResult("", "classify", "m", 5, 1, 0.00001, 10, False, False, 0, 0))
    t.add_llm(LLMResult("", "large", "m", 900, 40, 0.0002, 400, True, False, 1, 3000))
    body = to_response(result(), "q", t)
    assert body["trace"]["spans"][0]["name"] == "retrieve"
    assert body["trace"]["cost"]["classifier"] == pytest.approx(0.00001)
    assert body["trace"]["throttle_wait_ms"] == 3000
    assert (body["trace"]["tokens_in"], body["trace"]["tokens_out"]) == (900, 40)


def test_extra_notes_in_detail_are_ignored_but_bad_shapes_fail() -> None:
    body = to_response(result(), "q")
    assert (
        QueryResponse.model_validate({**body, "citation_errors": 1, "spans": []}).model_dump()
        == body
    )
    with pytest.raises(ValidationError):
        QueryResponse.model_validate({**body, "route": {**body["route"], "final": "web"}})
