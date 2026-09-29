import dataclasses
import json
import re
from pathlib import Path

from adaptiverag.ingest.extract import (
    ENTITY_TYPES,
    ITEM_SCHEMA,
    SYSTEM_PROMPT,
    build_messages,
    evidence_span,
    parse_response,
    snake_case,
)
from adaptiverag.types import Chunk, Triple

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = Path(__file__).parent / "snapshots" / "extract_prompt.txt"

ED_WOOD = (
    "Ed Wood is a 1994 American biographical period comedy-drama film directed and produced "
    "by Tim Burton, and starring Johnny Depp as cult filmmaker Ed Wood."
)
DERRICKSON = (
    "Scott Derrickson (born July 16, 1966) is an American director, screenwriter and producer. "
    "He lives in Los Angeles, California."
)
# the second chunk starts mid document, so its offsets do not start at 0
CHUNKS = [
    Chunk("d1:sentence:0", "d1", "sentence", 0, 0, len(ED_WOOD), ED_WOOD, 25),
    Chunk("d2:sentence:1", "d2", "sentence", 1, 40, 40 + len(DERRICKSON), DERRICKSON, 16),
]


def item(**overrides: object) -> dict[str, object]:
    good: dict[str, object] = {
        "chunk": 1,
        "subject": "Tim Burton",
        "subject_type": "PERSON",
        "predicate": "directed",
        "object": "Ed Wood",
        "object_type": "WORK",
        "evidence": "directed and produced by Tim Burton",
        "confidence": 0.9,
    }
    return good | overrides


def response(*items: object) -> str:
    return json.dumps({"triples": list(items)})


def render(messages: list[dict[str, str]]) -> str:
    return "".join(f"--- {m['role']}\n{m['content']}\n" for m in messages)


def test_prompt_matches_the_snapshot() -> None:
    # a prompt change changes every cache key and every extraction: review the diff, then
    # rewrite the snapshot on purpose
    assert render(build_messages(CHUNKS)) == SNAPSHOT.read_text(encoding="utf-8")


def test_prompt_numbers_the_passages_and_carries_the_schema() -> None:
    user = build_messages(CHUNKS)[1]["content"]
    assert f"[1] {ED_WOOD}" in user and f"[2] {DERRICKSON}" in user
    schema_in_prompt = json.loads(SYSTEM_PROMPT.split("Schema:\n", 1)[1])
    assert schema_in_prompt["properties"]["triples"]["items"] == ITEM_SCHEMA


def test_entity_types_match_the_database_check() -> None:
    sql = (ROOT / "db" / "migrations" / "0001_init.sql").read_text(encoding="utf-8")
    found = re.search(r"create table entities.*?check \(type in \(([^)]*)\)\)", sql, re.S)
    assert found is not None
    assert tuple(t.strip(" '") for t in found.group(1).split(",")) == ENTITY_TYPES
    assert ITEM_SCHEMA["properties"]["subject_type"]["enum"] == list(ENTITY_TYPES)
    assert ITEM_SCHEMA["properties"]["object_type"]["enum"] == list(ENTITY_TYPES)
    assert ", ".join(ENTITY_TYPES) in SYSTEM_PROMPT


def test_schema_fields_map_onto_triple() -> None:
    from_model = set(ITEM_SCHEMA["properties"])
    assert set(ITEM_SCHEMA["required"]) == from_model
    # the parser turns chunk into chunk_id and the evidence quote into offsets
    filled_in = (from_model - {"chunk", "evidence"}) | {
        "chunk_id",
        "evidence_start",
        "evidence_end",
    }
    assert filled_in == {f.name for f in dataclasses.fields(Triple)}


def test_parse_builds_triples_with_document_offsets() -> None:
    lives = item(
        chunk=2,
        subject="Scott Derrickson",
        predicate="lives in",
        object="Los Angeles, California",
        object_type="PLACE",
        evidence="He lives in Los Angeles, California.",
        confidence=1,
    )
    triples, rejects = parse_response(response(item(), lives), CHUNKS)
    assert rejects == []
    burton, derrickson = triples
    assert burton == Triple(
        "Tim Burton", "PERSON", "directed", "Ed Wood", "WORK", "d1:sentence:0", 65, 100, 0.9
    )
    assert ED_WOOD[burton.evidence_start : burton.evidence_end] == item()["evidence"]
    assert derrickson.chunk_id == "d2:sentence:1" and derrickson.predicate == "lives_in"
    doc_text = " " * 40 + DERRICKSON
    assert doc_text[derrickson.evidence_start : derrickson.evidence_end] == lives["evidence"]


def test_parse_rejects_output_that_is_not_the_schema() -> None:
    for text in ["not json", "[]", '{"facts": []}', '{"triples": {}}']:
        triples, rejects = parse_response(text, CHUNKS)
        assert triples == []
        assert [(r["chunk_id"], r["reason"]) for r in rejects] == [(None, "bad_json")]
        assert rejects[0]["raw"]["chunk_ids"] == ["d1:sentence:0", "d2:sentence:1"]


def test_parse_rejects_each_bad_item_and_keeps_the_rest() -> None:
    no_evidence = {k: v for k, v in item().items() if k != "evidence"}
    bad = [
        "Tim Burton directed Ed Wood",
        no_evidence,
        item(chunk=3),
        item(chunk=True),
        item(subject_type="COUNTRY"),
        item(object=None),
        item(confidence=1.5),
    ]
    triples, rejects = parse_response(response(item(), *bad), CHUNKS)
    assert len(triples) == 1
    assert [r["reason"] for r in rejects] == ["bad_json"] * len(bad)
    assert [r["chunk_id"] for r in rejects] == [None, "d1:sentence:0", None, None] + [
        "d1:sentence:0"
    ] * 3
    assert rejects[4]["raw"]["problem"] == "subject_type is not in the entity type list"


def test_empty_list_is_a_valid_answer() -> None:
    assert parse_response('{"triples": []}', CHUNKS) == ([], [])


def test_predicates_become_lower_snake_case() -> None:
    assert snake_case("Born In") == "born_in"
    assert snake_case("  member-of ") == "member_of"
    assert snake_case("founded") == "founded"
    assert snake_case("?!") == ""


def test_evidence_not_found_falls_back_to_the_whole_chunk() -> None:
    chunk = CHUNKS[1]
    assert evidence_span("he LIVES in los angeles", chunk) == (40 + 90, 40 + 113)
    assert evidence_span("born in Chicago", chunk) == (chunk.start, chunk.end)
    assert evidence_span("  ", chunk) == (chunk.start, chunk.end)
