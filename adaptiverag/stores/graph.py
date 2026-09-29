"""Graph reads and writes on Postgres: corpus chunks for extraction, linking, traversal."""

from typing import Any

import numpy as np
from psycopg.types.json import Jsonb

from adaptiverag.stores import db
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Chunk, GraphPath, Retrieved, Seed, Strategy


def corpus_chunks(doc_ids: list[str], strategy: Strategy) -> tuple[list[Chunk], dict[str, str]]:
    """Chunks of one strategy for these documents in (doc_id, ord) order, and each doc's text."""
    with db.conn() as c:
        rows = c.execute(
            "select chunk_id, doc_id, strategy, ord, start_offset, end_offset, text, n_words "
            "from chunks where doc_id = any(%s) and strategy = %s order by doc_id, ord",
            (doc_ids, strategy),
        ).fetchall()
        docs = c.execute(
            "select doc_id, text from documents where doc_id = any(%s)", (doc_ids,)
        ).fetchall()
    return [Chunk(*row) for row in rows], {doc_id: text for doc_id, text in docs}


# rejects of these chunks, including whole responses (chunk_id null) that covered one of them
OF_CHUNKS = "chunk_id = any(%s) or (chunk_id is null and raw->'chunk_ids' ?| %s)"


def save_rejects(rejects: list[dict[str, Any]], chunk_ids: list[str]) -> None:
    """Replace the stored rejects of these chunks, so a rerun does not count them twice."""
    with db.conn() as c:
        c.execute(f"delete from extraction_rejects where {OF_CHUNKS}", (chunk_ids, chunk_ids))
        with c.cursor() as cur:
            cur.executemany(
                "insert into extraction_rejects (chunk_id, raw, reason) values (%s, %s, %s)",
                [(r["chunk_id"], Jsonb(r["raw"]), r["reason"]) for r in rejects],
            )


def reject_counts(chunk_ids: list[str]) -> dict[str, int]:
    """Stored rejects of these chunks by reason."""
    with db.conn() as c:
        rows = c.execute(
            f"select reason, count(*) from extraction_rejects where {OF_CHUNKS} "
            "group by reason order by reason",
            (chunk_ids, chunk_ids),
        ).fetchall()
    return {reason: n for reason, n in rows}


def link_entities(question: str, qvec: np.ndarray, trace: Trace) -> list[Seed]:
    raise NotImplementedError


def traverse(
    seeds: list[Seed], qvec: np.ndarray, depth: int, fanout: int, max_paths: int
) -> list[GraphPath]:
    raise NotImplementedError


def retrieve(question: str, k: int, trace: Trace, qvec: np.ndarray | None = None) -> Retrieved:
    """Hits are the provenance chunks of the best paths."""
    raise NotImplementedError
