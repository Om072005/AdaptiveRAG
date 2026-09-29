"""python -m adaptiverag.ingest graph --corpus mini|full [--dry-run] | relink

Until the graph writes land, this runs extraction, stores the rejects and prints the summary.
"""

import argparse
import json

from adaptiverag.config import ROOT, router_cfg
from adaptiverag.ingest.extract import extract_batches, summarize
from adaptiverag.llm import RateLimited
from adaptiverag.stores import graph as store


def corpus_doc_ids(corpus: str) -> list[str]:
    """doc_ids from data/corpus/<corpus>.json."""
    path = ROOT / "data" / "corpus" / f"{corpus}.json"
    return list(json.loads(path.read_text(encoding="utf-8"))["doc_ids"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.ingest graph")
    parser.add_argument("--corpus", choices=["mini", "full"], required=True)
    # keep it a multiple of chunks_per_call so the batches match a full run and stay cached
    parser.add_argument("--limit", type=int, help="first N chunks only, for development")
    args = parser.parse_args(argv)

    strategy = router_cfg()["serving"]["chunk_strategy"]
    doc_ids = corpus_doc_ids(args.corpus)
    chunks, doc_text = store.corpus_chunks(doc_ids, strategy)
    missing = len(set(doc_ids) - {c.doc_id for c in chunks})
    if args.limit:
        chunks = chunks[: args.limit]
    print(f"{args.corpus}: {len(chunks)} {strategy} chunks, {missing} documents without chunks")
    try:
        kept, rejects, calls = extract_batches(chunks, doc_text)
    except RateLimited as e:
        # finished batches are in the cache, so a rerun later picks up where this stopped
        raise SystemExit(f"rate limited, rerun later to resume: {e}") from e
    summary = summarize(chunks, kept, rejects, calls)
    ids = [c.chunk_id for c in chunks]
    store.save_rejects(rejects, ids)
    # read back from the table, so the printed rate and the stored log cannot drift apart
    summary["stored_rejects_by_reason"] = store.reject_counts(ids)
    summary["stored_matches_run"] = (
        summary["stored_rejects_by_reason"] == summary["rejects_by_reason"]
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
