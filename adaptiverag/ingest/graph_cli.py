"""python -m adaptiverag.ingest graph --corpus mini|dev|gold|full [--limit N] [--dry-run]
python -m adaptiverag.ingest graph embed --corpus mini|dev|gold|full [--slice K/N]

The build extracts triples (cached), stores the rejects, resolves entities and replaces the graph.
The embed step fills the cache with the texts a build embeds, one slice at a time, so helpers can
spread them over their own keys; a rerun skips what is cached.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from adaptiverag import llm
from adaptiverag.config import ROOT, router_cfg
from adaptiverag.ingest.extract import extract_batches, summarize
from adaptiverag.ingest.loader import SOURCE, read_raw
from adaptiverag.ingest.normalize import doc_id
from adaptiverag.ingest.pipeline import endpoint, in_slice, parse_slice
from adaptiverag.ingest.resolve import graph_texts, relation_texts, resolve
from adaptiverag.llm import RateLimited
from adaptiverag.stores import graph as store
from adaptiverag.types import Chunk, LLMResult, Triple

CORPORA = ["mini", "dev", "gold", "full"]


def gold_doc_ids(items: list[dict[str, Any]], raw: dict[str, dict[str, Any]]) -> list[str]:
    """Documents of gold questions: a HotpotQA item brings all its context paragraphs, distractors
    included; a generated single hop item ('sh_<doc_id>_<n>') brings its one paragraph."""
    ids: set[str] = set()
    for item in items:
        if item["id"].startswith("hp_"):
            ids |= {doc_id(SOURCE, title) for title, _ in raw[item["id"][3:]]["context"]}
        else:
            ids.add(item["id"].split("_")[1])
    return sorted(ids)


def corpus_doc_ids(corpus: str) -> list[str]:
    """mini and full: the corpus manifests. dev: documents of the dev gold questions (the G2 graph).
    gold: dev and test questions together; reading test items asks no test question."""
    if corpus in ("mini", "full"):
        path = ROOT / "data" / "corpus" / f"{corpus}.json"
        return list(json.loads(path.read_text(encoding="utf-8"))["doc_ids"])
    splits = ["dev"] if corpus == "dev" else ["dev", "test"]
    items = [i for s in splits for i in read_jsonl_dicts(ROOT / "data" / "gold" / f"{s}.jsonl")]
    return gold_doc_ids(items, {r["_id"]: r for r in read_raw()})


def read_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def extract_corpus(
    corpus: str, limit: int | None
) -> tuple[list[Chunk], list[Triple], list[dict[str, Any]], list[LLMResult]]:
    """Serving chunks of the corpus and their triples; stored extraction calls are cache hits."""
    strategy = router_cfg()["serving"]["chunk_strategy"]
    doc_ids = corpus_doc_ids(corpus)
    chunks, doc_text = store.corpus_chunks(doc_ids, strategy)
    missing = len(set(doc_ids) - {c.doc_id for c in chunks})
    if limit:
        chunks = chunks[:limit]
    print(f"database: {endpoint()}")
    print(f"{corpus}: {len(chunks)} {strategy} chunks, {missing} documents without chunks")
    try:
        kept, rejects, calls = extract_batches(chunks, doc_text)
    except RateLimited as e:
        # finished batches are in the cache, so a rerun later picks up where this stopped
        raise SystemExit(f"rate limited, rerun later to resume: {e}") from e
    return chunks, kept, rejects, calls


def embed_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.ingest graph embed")
    parser.add_argument("--corpus", choices=CORPORA, required=True)
    parser.add_argument("--slice", type=parse_slice, default="1/1", help="K/N, for example 2/4")
    args = parser.parse_args(argv)
    k, n = args.slice
    _, kept, _, calls = extract_corpus(args.corpus, None)
    texts = graph_texts(kept)
    mine = [t for t in texts if in_slice(t, k, n)]
    print(f"extraction calls from the cache: {sum(c.cached for c in calls)} of {len(calls)}")
    print(f"graph embed slice {k}/{n}: {len(mine)} of {len(texts)} texts")
    try:
        llm.embed(mine)
    except RateLimited as e:
        raise SystemExit(
            f"graph embed slice {k}/{n} stopped by the quota ({e}); rerun later"
        ) from e
    print(f"graph embed slice {k}/{n}: all {len(mine)} texts embedded or already cached")


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["embed"]:
        return embed_main(argv[1:])
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.ingest graph")
    parser.add_argument("--corpus", choices=CORPORA, required=True)
    # keep it a multiple of chunks_per_call so the batches match a full run and stay cached
    parser.add_argument("--limit", type=int, help="first N chunks only, for development")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the rows it would write, write nothing"
    )
    args = parser.parse_args(argv)

    chunks, kept, rejects, calls = extract_corpus(args.corpus, args.limit)
    summary = summarize(chunks, kept, rejects, calls)
    if not args.dry_run:
        ids = [c.chunk_id for c in chunks]
        store.save_rejects(rejects, ids)
        # read back from the table, so the printed rate and the stored log cannot drift apart
        summary["stored_rejects_by_reason"] = store.reject_counts(ids)
        summary["stored_matches_run"] = (
            summary["stored_rejects_by_reason"] == summary["rejects_by_reason"]
        )
    print(json.dumps({"extraction": summary}, indent=2))

    try:
        entities, aliases, relations = resolve(kept)
        # a kept triple that is not a relation repeated one already kept, or both its ends
        # resolved to one entity
        graph: dict[str, Any] = {"triples_folded_by_resolution": len(kept) - len(relations)}
        if args.dry_run:
            counts = {
                "entities": len(entities),
                "aliases": len(aliases),
                "relations": len(relations),
            }
            graph["would_write"] = counts | {"extraction_rejects": len(rejects)}
        else:
            vecs = llm.embed(relation_texts(entities, relations))
            for rel, vec in zip(relations, vecs, strict=True):
                rel["embedding"] = vec
            store.write_graph(entities, aliases, relations)
            graph |= store.graph_counts()
    except RateLimited as e:
        # embeddings are cached per text, so a rerun later continues where this stopped
        raise SystemExit(f"rate limited while embedding, rerun later to resume: {e}") from e
    print(json.dumps({"graph": graph}, indent=2))


if __name__ == "__main__":
    main()
