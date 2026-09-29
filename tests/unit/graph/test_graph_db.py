"""Linking against real Postgres (pg_trgm, pgvector) on your own dev branch.

A fixture graph is inserted in one transaction and rolled back, so nothing stays behind.
Run with: uv run pytest -m network tests/unit/graph/test_graph_db.py
"""

from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest
from psycopg import Connection

from adaptiverag.stores import db
from adaptiverag.stores.graph import seeds_for

pytestmark = pytest.mark.network

DOC = "fx0000000000doc0"
CHUNK = f"{DOC}:sentence:0"
TEXT = "Ed Wood is a film directed by Tim Burton, starring Johnny Depp. Burton was born in Burbank."
ENTITIES = [  # id, name, type, axis of its unit embedding
    ("e_fx_tb", "Tim Burton", "PERSON", 0),
    ("e_fx_ew", "Ed Wood", "WORK", 1),
    ("e_fx_jd", "Johnny Depp", "PERSON", 2),
    ("e_fx_ap", "Apple Inc.", "ORG", 3),
    ("e_fx_bu", "Burbank", "PLACE", 4),
]
ALIASES = [
    ("Tim Burton", "e_fx_tb", 1.0),
    ("Ed Wood", "e_fx_ew", 1.0),
    ("Johnny Depp", "e_fx_jd", 1.0),
    ("Apple Inc.", "e_fx_ap", 1.0),
    ("Apple", "e_fx_ap", 0.95),
    ("Burbank", "e_fx_bu", 1.0),
]
RELATIONS = [  # id, subject, predicate, object, axis of its embedding
    ("fx_r1", "e_fx_tb", "directed", "e_fx_ew", 1),
    ("fx_r2", "e_fx_jd", "starred_in", "e_fx_ew", 2),
    ("fx_r3", "e_fx_tb", "born_in", "e_fx_bu", 4),
]
MIN_SEED = 0.45


def unit(axis: int) -> np.ndarray:
    v = np.zeros(768, dtype=np.float32)
    v[axis] = 1.0
    return v


@pytest.fixture(scope="module")
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
            " n_words)"
            " values (%s, %s, 'sentence', 0, 0, %s, %s, 16)",
            (CHUNK, DOC, len(TEXT), TEXT),
        )
        for cid, name, type_, axis in ENTITIES:
            conn.execute(
                "insert into entities values (%s, %s, %s, %s)", (cid, name, type_, unit(axis))
            )
        for surface, cid, conf in ALIASES:
            conn.execute("insert into aliases values (%s, %s, %s)", (surface, cid, conf))
        for rid, s, p, o, axis in RELATIONS:
            conn.execute(
                "insert into relations values (%s, %s, %s, %s, %s, %s, 0, 10, 0.9, %s)",
                (rid, s, p, o, CHUNK, DOC, unit(axis)),
            )
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Who directed Ed Wood?", ["e_fx_ew"]),
        ("Which film did Tim Burton and Johnny Depp both work on?", ["e_fx_jd", "e_fx_tb"]),
        ("Where was Tim Burton born?", ["e_fx_tb"]),
        ("Who founded apple, the phone maker?", ["e_fx_ap"]),
        ("Is Burbank in California?", ["e_fx_bu"]),
    ],
)
def test_aliases_in_the_question_become_seeds(
    c: Connection[Any], question: str, expected: list[str]
) -> None:
    seeds = seeds_for(c, question, unit(700), MIN_SEED)
    assert sorted(s.canonical_id for s in seeds) == expected
    assert all(s.matched != "embedding" for s in seeds)


def test_embedding_fallback_when_no_alias_matches(c: Connection[Any]) -> None:
    (s,) = seeds_for(c, "the director of the 1994 biopic", unit(0), MIN_SEED)
    assert (
        s.canonical_id == "e_fx_tb" and s.matched == "embedding" and s.score == pytest.approx(1.0)
    )
    assert seeds_for(c, "the director of the 1994 biopic", unit(700), MIN_SEED) == []
