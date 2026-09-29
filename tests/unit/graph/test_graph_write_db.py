"""Graph writes against real Postgres on your own dev branch: foreign keys, vectors, aliases.

Everything runs in one transaction that is rolled back, so the branch is left as it was.
Run with: uv run pytest -m network tests/unit/graph/test_graph_write_db.py
"""

from collections.abc import Iterator
from typing import Any

import numpy as np
import psycopg
import pytest
from psycopg import Connection

from adaptiverag.ingest.resolve import build_rows
from adaptiverag.stores import db
from adaptiverag.stores.graph import graph_counts, replace_graph
from adaptiverag.types import Triple

pytestmark = pytest.mark.network

DOC = "fx0000000000doc1"
CHUNK = f"{DOC}:sentence:0"
TEXT = "Tim Burton directed Ed Wood. John Smith was born in Ohio. John Smith sat in Parliament."
CFG = {"name_sim": 0.92, "embed_sim": 0.88, "person_needs_shared_neighbor": True}


def triple(s: str, st: str, p: str, o: str, ot: str, chunk: str = CHUNK) -> Triple:
    return Triple(s, st, p, o, ot, chunk, 0, 10, 0.9)


def rows(chunk_ids: tuple[str, str] = (CHUNK, CHUNK)) -> tuple[Any, Any, Any]:
    triples = [
        triple("Tim Burton", "PERSON", "directed", "Ed Wood", "WORK"),
        triple("John Smith", "PERSON", "born_in", "Ohio", "PLACE", chunk_ids[0]),
        triple("John Smith", "PERSON", "member_of", "Parliament", "ORG", chunk_ids[1]),
    ]
    entities, aliases, relations = build_rows(triples, {}, CFG)
    for row in [*entities, *relations]:
        row["embedding"] = np.ones(768, dtype=np.float32) / np.sqrt(768)
    return entities, aliases, relations


@pytest.fixture
def c() -> Iterator[Connection[Any]]:
    conn = db.conn()
    try:
        conn.execute(
            "insert into documents (doc_id, source, title, text, sentences)"
            " values (%s, 'test', 'Fixture', %s, '[]')",
            (DOC, TEXT),
        )
        conn.execute(
            "insert into chunks (chunk_id, doc_id, strategy, ord, start_offset, end_offset, text,"
            " n_words) values (%s, %s, 'sentence', 0, 0, %s, %s, 16)",
            (CHUNK, DOC, len(TEXT), TEXT),
        )
        yield conn
    finally:
        conn.rollback()
        conn.close()


def test_the_graph_is_written_with_provenance_and_vectors(c: Connection[Any]) -> None:
    entities, aliases, relations = rows()
    replace_graph(c, entities, aliases, relations)
    counts = graph_counts(c)
    assert counts["entities"] == len(entities) and counts["relations"] == len(relations) == 3
    assert counts["relations_without_chunk"] == 0 and counts["relations_without_vector"] == 0
    stored = c.execute("select chunk_id from relations").fetchall()
    assert {r[0] for r in stored} == {CHUNK}


def test_merged_mentions_share_one_alias_row(c: Connection[Any]) -> None:
    # both John Smiths are in one document, so they merge into one entity
    replace_graph(c, *rows())
    n = c.execute("select count(*) from aliases where surface_form = 'John Smith'").fetchone()
    assert n is not None and n[0] == 1


def test_a_relation_without_its_chunk_is_refused_and_nothing_is_kept(c: Connection[Any]) -> None:
    replace_graph(c, *rows())
    before = graph_counts(c)
    with pytest.raises(psycopg.errors.ForeignKeyViolation), c.transaction():
        replace_graph(c, *rows((CHUNK, "no-such-doc:sentence:9")))
    assert graph_counts(c) == before
