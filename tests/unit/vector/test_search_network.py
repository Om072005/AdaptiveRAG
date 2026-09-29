"""Against the database in .env: needs stored chunks with embeddings for every strategy tested."""

import numpy as np
import pytest

from adaptiverag.stores import vector
from adaptiverag.stores.db import conn
from adaptiverag.types import Strategy

pytestmark = pytest.mark.network


@pytest.mark.parametrize("strategy", ["fixed", "sentence"])
def test_a_chunk_finds_itself_first(strategy: Strategy) -> None:
    with conn() as c:
        row = c.execute(
            "select chunk_id, embedding from chunks where strategy = %s and embedding is not null "
            "order by chunk_id limit 1",
            (strategy,),
        ).fetchone()
    assert row is not None, f"no embedded {strategy} chunks stored"
    hits = vector.search(row[1].to_numpy(), 8, strategy)
    assert hits[0].chunk_id == row[0] and hits[0].rank == 1
    assert hits[0].score == pytest.approx(1.0, abs=1e-4)
    assert all(h.chunk_id.split(":")[1] == strategy for h in hits)


def test_the_partial_hnsw_index_can_serve_the_search() -> None:
    # On a few hundred rows the planner rightly prefers an exact sort, so turn the other plans off
    # to prove the query shape matches the partial index of its strategy.
    query = vector.sql.SQL(vector.SEARCH).format(strategy=vector.sql.Literal("sentence"))
    with conn() as c:
        for setting in ("enable_seqscan", "enable_bitmapscan", "enable_sort"):
            c.execute(f"set {setting} = off")
        plan = c.execute(
            vector.sql.SQL("explain ") + query, {"q": np.ones(768, dtype=np.float32), "k": 8}
        ).fetchall()
    assert "chunks_hnsw_sentence" in "\n".join(r[0] for r in plan)


def test_chunk_vectors_returns_stored_embeddings() -> None:
    with conn() as c:
        ids = [
            r[0]
            for r in c.execute("select chunk_id from chunks where embedding is not null limit 3")
        ]
    vecs = vector.chunk_vectors([*ids, "missing:fixed:0"])
    assert sorted(vecs) == sorted(ids)
    assert all(
        v.shape == (768,) and abs(float(np.linalg.norm(v)) - 1) < 1e-3 for v in vecs.values()
    )
