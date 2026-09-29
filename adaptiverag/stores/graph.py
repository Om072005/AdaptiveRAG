"""Graph reads and writes on Postgres: corpus chunks for extraction, linking, traversal."""

import numpy as np

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


def link_entities(question: str, qvec: np.ndarray, trace: Trace) -> list[Seed]:
    raise NotImplementedError


def traverse(
    seeds: list[Seed], qvec: np.ndarray, depth: int, fanout: int, max_paths: int
) -> list[GraphPath]:
    raise NotImplementedError


def retrieve(question: str, k: int, trace: Trace, qvec: np.ndarray | None = None) -> Retrieved:
    """Hits are the provenance chunks of the best paths."""
    raise NotImplementedError
