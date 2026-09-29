"""python -m adaptiverag.ingest run --corpus mini|full [--strategies fixed,sentence,semantic]"""

import argparse
from typing import Any, cast, get_args

from psycopg import Connection

from adaptiverag.config import ingest_cfg
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


def store_embeddings(c: Connection[Any], strategy: Strategy, doc_ids: list[str]) -> None:
    """Embed the chunks of this strategy that have no embedding yet, committing per batch."""
    missing = corpus.chunks_without_embedding(c, [strategy], doc_ids)
    for start in range(0, len(missing), EMBED_BATCH):
        batch = missing[start : start + EMBED_BATCH]
        corpus.set_embeddings(c, [ch.chunk_id for ch in batch], embed_chunks(batch))
        c.commit()
        print(f"embeddings {strategy}: {start + len(batch)}/{len(missing)}")
    print(f"embeddings {strategy}: {len(missing)} were missing, all stored")


def run(name: str, strategies: list[Strategy]) -> None:
    """Store documents, then chunks and embeddings one strategy at a time, in the order given."""
    cfg = ingest_cfg()["chunk"]
    docs, _ = loader.corpus(name)
    with conn() as c:
        new = corpus.insert_documents(c, docs)
        c.commit()
        print(f"documents: {new} new, {len(docs) - new} already stored")
        for strategy in strategies:
            store_chunks(c, docs, strategy, cfg)
            store_embeddings(c, strategy, [d.doc_id for d in docs])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.ingest run")
    parser.add_argument("--corpus", choices=sorted(loader.CORPUS_QUESTIONS), required=True)
    parser.add_argument("--strategies", type=parse_strategies, default="fixed,sentence,semantic")
    args = parser.parse_args(argv)
    try:
        run(args.corpus, args.strategies)
    except RateLimited as e:
        raise SystemExit(f"stopped by the provider quota ({e}); rerun later to resume") from e
