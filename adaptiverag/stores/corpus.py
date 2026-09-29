"""documents and chunks writes. Rows already stored are kept as they are, so a rerun is a no-op."""

from typing import Any, cast

import numpy as np
import psycopg
from psycopg.types.json import Jsonb

from adaptiverag.types import Chunk, Document, Strategy


def insert_documents(c: psycopg.Connection[Any], docs: list[Document]) -> int:
    """Insert documents that are not stored yet; returns how many were new."""
    cur = c.execute(
        "insert into documents (doc_id, source, title, text, sentences) "
        "select * from unnest(%s::text[], %s::text[], %s::text[], %s::text[], %s::jsonb[]) "
        "on conflict (doc_id) do nothing",
        (
            [d.doc_id for d in docs],
            [d.source for d in docs],
            [d.title for d in docs],
            [d.text for d in docs],
            [Jsonb([list(s) for s in d.sentences]) for d in docs],
        ),
    )
    return cur.rowcount


def insert_chunks(c: psycopg.Connection[Any], chunks: list[Chunk]) -> int:
    """Insert chunks that are not stored yet; returns how many were new."""
    cur = c.execute(
        "insert into chunks "
        "(chunk_id, doc_id, strategy, ord, start_offset, end_offset, text, n_words) "
        "select * from unnest(%s::text[], %s::text[], %s::text[], %s::int[], %s::int[], "
        "%s::int[], %s::text[], %s::int[]) on conflict (chunk_id) do nothing",
        (
            [ch.chunk_id for ch in chunks],
            [ch.doc_id for ch in chunks],
            [ch.strategy for ch in chunks],
            [ch.ord for ch in chunks],
            [ch.start for ch in chunks],
            [ch.end for ch in chunks],
            [ch.text for ch in chunks],
            [ch.n_words for ch in chunks],
        ),
    )
    return cur.rowcount


def chunked_doc_ids(c: psycopg.Connection[Any], strategy: Strategy, doc_ids: list[str]) -> set[str]:
    """Documents that already have chunks for this strategy."""
    rows = c.execute(
        "select distinct doc_id from chunks where strategy = %s and doc_id = any(%s)",
        (strategy, doc_ids),
    ).fetchall()
    return {r[0] for r in rows}


def chunk_ids(c: psycopg.Connection[Any], strategy: Strategy, doc_ids: list[str]) -> list[str]:
    """Every stored chunk id of these documents for one strategy."""
    rows = c.execute(
        "select chunk_id from chunks where strategy = %s and doc_id = any(%s) order by chunk_id",
        (strategy, doc_ids),
    ).fetchall()
    return [r[0] for r in rows]


def chunks_without_embedding(
    c: psycopg.Connection[Any], strategies: list[Strategy], doc_ids: list[str]
) -> list[Chunk]:
    """Stored chunks of these documents and strategies that have no embedding yet."""
    rows = c.execute(
        "select chunk_id, doc_id, strategy, ord, start_offset, end_offset, text, n_words "
        "from chunks where embedding is null and strategy = any(%s) and doc_id = any(%s) "
        "order by chunk_id",
        (strategies, doc_ids),
    ).fetchall()
    return [Chunk(r[0], r[1], cast(Strategy, r[2]), *r[3:]) for r in rows]


def set_embeddings(c: psycopg.Connection[Any], chunk_ids: list[str], vecs: np.ndarray) -> None:
    """Store one embedding per chunk id."""
    with c.cursor() as cur:
        cur.executemany(
            "update chunks set embedding = %s where chunk_id = %s",
            list(zip(vecs, chunk_ids, strict=True)),
        )
