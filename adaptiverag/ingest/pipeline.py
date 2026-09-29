"""python -m adaptiverag.ingest run --corpus mini|full [--strategies ...] [--no-embed]
python -m adaptiverag.ingest embed --corpus mini|full --strategy sentence [--slice K/N]"""

import argparse
import hashlib
from typing import Any, cast, get_args

from psycopg import Connection

from adaptiverag.config import ingest_cfg, settings
from adaptiverag.ingest import loader
from adaptiverag.ingest.chunking import chunk_fixed, chunk_semantic, chunk_sentence
from adaptiverag.ingest.embed import embed_chunks, embed_sentences
from adaptiverag.llm import RateLimited
from adaptiverag.stores import corpus
from adaptiverag.stores.db import conn
from adaptiverag.types import Chunk, Document, Strategy

# Embedded and committed together, so a stopped run keeps what it finished. Half of the Gemini
# free tier minute (100 texts), so a retried batch fits once part of that minute has cleared.
EMBED_BATCH = 50
DOC_BATCH = 200  # documents chunked and committed together; semantic embeds their sentences


def parse_strategies(text: str) -> list[Strategy]:
    """'fixed,sentence' -> ['fixed', 'sentence'], refusing unknown names."""
    names = [s.strip() for s in text.split(",") if s.strip()]
    unknown = [s for s in names if s not in get_args(Strategy)]
    if unknown or not names:
        raise argparse.ArgumentTypeError(f"strategies must be from {get_args(Strategy)}")
    return [cast(Strategy, s) for s in dict.fromkeys(names)]


def chunk_docs(docs: list[Document], strategy: Strategy, cfg: dict[str, Any]) -> list[Chunk]:
    """Chunks of these documents with the [chunk.<strategy>] settings of config/ingest.toml."""
    if strategy == "fixed":
        n, overlap = cfg["fixed"]["n_words"], cfg["fixed"]["overlap"]
        return [ch for d in docs for ch in chunk_fixed(d, n, overlap)]
    if strategy == "sentence":
        return [ch for d in docs for ch in chunk_sentence(d, cfg["sentence"]["max_words"])]
    vecs = embed_sentences(docs)  # cached per sentence, so a stopped run does not pay twice
    pct = cfg["semantic"]["percentile"]
    return [ch for d, v in zip(docs, vecs, strict=True) for ch in chunk_semantic(d, v, pct)]


def store_chunks(
    c: Connection[Any], docs: list[Document], strategy: Strategy, cfg: dict[str, Any]
) -> None:
    """Chunk the documents that have no chunks of this strategy yet, committing per batch."""
    done = corpus.chunked_doc_ids(c, strategy, [d.doc_id for d in docs])
    todo = [d for d in docs if d.doc_id not in done]
    new = 0
    for start in range(0, len(todo), DOC_BATCH):
        new += corpus.insert_chunks(c, chunk_docs(todo[start : start + DOC_BATCH], strategy, cfg))
        c.commit()
        print(f"chunks {strategy}: {min(start + DOC_BATCH, len(todo))}/{len(todo)} documents")
    print(f"chunks {strategy}: {new} new, {len(done)} documents were done before")


def store_embeddings(c: Connection[Any], label: str, missing: list[Chunk]) -> None:
    """Embed these chunks in batches, committing each, so a stopped run keeps what it finished."""
    for start in range(0, len(missing), EMBED_BATCH):
        batch = missing[start : start + EMBED_BATCH]
        corpus.set_embeddings(c, [ch.chunk_id for ch in batch], embed_chunks(batch))
        c.commit()
        print(f"embeddings {label}: {start + len(batch)}/{len(missing)}")
    print(f"embeddings {label}: {len(missing)} were missing, all stored")


def run(name: str, strategies: list[Strategy], embed: bool = True) -> None:
    """Store documents, then chunks and embeddings one strategy at a time, in the order given."""
    cfg = ingest_cfg()["chunk"]
    docs, _ = loader.corpus(name)
    doc_ids = [d.doc_id for d in docs]
    with conn() as c:
        print(f"database: {endpoint()}")
        new = corpus.insert_documents(c, docs)
        c.commit()
        print(f"documents: {new} new, {len(docs) - new} already stored")
        for strategy in strategies:
            store_chunks(c, docs, strategy, cfg)
            if embed:
                missing = corpus.chunks_without_embedding(c, [strategy], doc_ids)
                store_embeddings(c, strategy, missing)


def endpoint() -> str:
    """The Neon endpoint id of DATABASE_URL, so a run shows which branch it writes to."""
    return settings().database_url.split("@")[-1].split(".")[0]


def in_slice(chunk_id: str, k: int, n: int) -> bool:
    """Slice k of n (from 1) by a stable hash of the chunk id: every chunk is in exactly one."""
    return int(hashlib.sha1(chunk_id.encode()).hexdigest()[:8], 16) % n == k - 1


def parse_slice(text: str) -> tuple[int, int]:
    """'2/4' -> (2, 4)."""
    try:
        k, n = (int(x) for x in text.split("/"))
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"slice must look like 2/4, got {text!r}") from e
    if not 1 <= k <= n:
        raise argparse.ArgumentTypeError(f"slice must have 1 <= K <= N, got {text!r}")
    return k, n


def embed_slice(name: str, strategy: Strategy, k: int, n: int) -> None:
    """Fill the missing embeddings of one slice of a corpus; a rerun continues where it stopped."""
    doc_ids = loader.manifest_doc_ids(name)
    with conn() as c:
        print(f"database: {endpoint()}")
        ids = [i for i in corpus.chunk_ids(c, strategy, doc_ids) if in_slice(i, k, n)]
        if not ids:
            raise SystemExit(f"no {strategy} chunks stored for the {name} corpus; run ingest first")
        missing = [
            ch
            for ch in corpus.chunks_without_embedding(c, [strategy], doc_ids)
            if in_slice(ch.chunk_id, k, n)
        ]
        done = len(ids) - len(missing)
        print(f"slice {k}/{n}: {len(ids)} {strategy} chunks, {done} embedded before")
        store_embeddings(c, f"slice {k}/{n}", missing)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.ingest run")
    parser.add_argument("--corpus", choices=sorted(loader.CORPUS_QUESTIONS), required=True)
    parser.add_argument("--strategies", type=parse_strategies, default="fixed,sentence,semantic")
    parser.add_argument("--no-embed", action="store_true", help="documents and chunks only")
    args = parser.parse_args(argv)
    try:
        run(args.corpus, args.strategies, embed=not args.no_embed)
    except RateLimited as e:
        raise SystemExit(f"stopped by the provider quota ({e}); rerun later to resume") from e


def embed_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.ingest embed")
    parser.add_argument("--corpus", choices=sorted(loader.CORPUS_QUESTIONS), required=True)
    parser.add_argument("--strategy", choices=get_args(Strategy), required=True)
    parser.add_argument("--slice", type=parse_slice, default="1/1", help="K/N, for example 2/4")
    args = parser.parse_args(argv)
    k, n = args.slice
    try:
        embed_slice(args.corpus, args.strategy, k, n)
    except RateLimited as e:
        raise SystemExit(f"slice {k}/{n} stopped by the quota ({e}); rerun after the reset") from e
