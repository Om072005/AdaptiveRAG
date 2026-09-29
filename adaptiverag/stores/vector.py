import time
from typing import Any, LiteralString, cast, get_args

import numpy as np
import psycopg
from psycopg import sql

from adaptiverag import llm
from adaptiverag.config import router_cfg
from adaptiverag.stores import db
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Hit, Retrieved, Strategy

# The strategy goes in as a literal, not a parameter, so the planner can match the partial
# HNSW index of that strategy (chunks_hnsw_fixed, _sentence, _semantic).
SEARCH = """
select h.chunk_id, h.doc_id, d.title, h.text, 1 - h.distance
from (
  select chunk_id, doc_id, text, embedding <=> %(q)s as distance
  from chunks
  where strategy = {strategy} and embedding is not null
  order by embedding <=> %(q)s
  limit %(k)s
) h
join documents d using (doc_id)
order by h.distance
"""


def to_hits(rows: list[tuple[Any, ...]]) -> list[Hit]:
    """Rows of (chunk_id, doc_id, title, text, cosine) in rank order."""
    return [
        Hit(r[0], r[1], r[2], r[3], float(r[4]), "vector", rank) for rank, r in enumerate(rows, 1)
    ]


def search(qvec: np.ndarray, k: int, strategy: Strategy) -> list[Hit]:
    """pgvector HNSW, cosine."""
    if strategy not in get_args(Strategy):
        raise ValueError(f"unknown chunk strategy: {strategy}")
    query = sql.SQL(SEARCH).format(strategy=sql.Literal(strategy))
    return to_hits(read(query, {"q": np.asarray(qvec, dtype=np.float32), "k": k}))


def chunk_vectors(chunk_ids: list[str]) -> dict[str, np.ndarray]:
    """Stored embeddings by chunk id, for the ids that have one."""
    if not chunk_ids:
        return {}
    rows = read(
        "select chunk_id, embedding from chunks where chunk_id = any(%s) and embedding is not null",
        (chunk_ids,),
    )
    return {r[0]: r[1].to_numpy().astype(np.float32) for r in rows}


def read(query: LiteralString | sql.Composed, params: Any) -> list[tuple[Any, ...]]:
    """Rows of one read on the shared connection, reconnecting once if Neon closed it idle."""
    for attempt in range(2):
        try:
            return db.shared().execute(query, params).fetchall()
        except psycopg.OperationalError:
            db.reset_shared()
            if attempt == 1:
                raise
    return []


def retrieve(question: str, k: int, trace: Trace, qvec: np.ndarray | None = None) -> Retrieved:
    """Top k chunks of the serving strategy; the query embedding is its own ledger row."""
    if qvec is None:
        qvec = llm.embed([question], trace=trace)[0]
    started = time.perf_counter()
    hits = search(qvec, k, cast(Strategy, router_cfg()["serving"]["chunk_strategy"]))
    latency_ms = int((time.perf_counter() - started) * 1000)
    top_score = hits[0].score if hits else 0.0
    trace.set(retrieval_latency_ms=latency_ms, n_results=len(hits), top_score=top_score)
    return Retrieved(hits, [], [], top_score, False, latency_ms)
