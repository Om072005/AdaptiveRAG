"""python -m adaptiverag.ingest graph --corpus mini|dev|gold|full [--limit N] [--dry-run]
python -m adaptiverag.ingest graph embed --corpus mini|dev|gold|full [--slice K/N]
python -m adaptiverag.ingest graph merges --corpus dev [--n 100] | --label | --precision
python -m adaptiverag.ingest relink [--dry-run]

The build extracts triples (cached), stores the rejects, resolves entities and replaces the graph.
The embed step fills the cache with the texts a build embeds, one slice at a time, so helpers can
spread them over their own keys; a rerun skips what is cached.
"""

import argparse
import json
import random
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from adaptiverag import llm
from adaptiverag.config import ROOT, ingest_cfg, router_cfg
from adaptiverag.ingest.extract import extract_batches, summarize
from adaptiverag.ingest.loader import SOURCE, read_raw
from adaptiverag.ingest.normalize import doc_id
from adaptiverag.ingest.pipeline import endpoint, in_slice, parse_slice
from adaptiverag.ingest.resolve import (
    graph_texts,
    merge_decisions,
    name_texts,
    normalize_name,
    relation_id,
    relation_texts,
    resolve,
)
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


LABELS_PATH = ROOT / "data" / "graph" / "merge_labels.jsonl"


def sample_merges(decisions: list[dict[str, str]], n: int, seed: int = 7) -> list[dict[str, str]]:
    """A seeded sample of n merge decisions (all of them when there are fewer), numbered from 1."""
    pool = sorted(decisions, key=lambda d: (d["type"], d["a"], d["a_doc"], d["b"], d["b_doc"]))
    random.Random(seed).shuffle(pool)
    return [{"n": str(i), **d, "label": ""} for i, d in enumerate(pool[:n], 1)]


def precision(items: list[dict[str, str]]) -> dict[str, Any]:
    """Share of labelled merges that joined one real entity, overall and per rule kind."""
    labelled = [i for i in items if i["label"] in ("same", "different")]

    def share(rows: list[dict[str, str]]) -> dict[str, Any]:
        same = sum(r["label"] == "same" for r in rows)
        rate = same / len(rows) if rows else None
        return {"labelled": len(rows), "same": same, "precision": rate}

    kinds = {
        "name": [i for i in labelled if i["rule"].startswith("name")],
        "embedding": [i for i in labelled if i["rule"].startswith("embedding")],
        "person": [i for i in labelled if i["type"] == "PERSON"],
    }
    return (
        share(labelled)
        | {"unlabelled": len(items) - len(labelled)}
        | {k: share(v) for k, v in kinds.items()}
    )


def label(items: list[dict[str, str]], ask: Callable[[str], str], save: Callable[[], None]) -> None:
    """Walk the unlabelled items: y same entity, n different, s skip, q quit. Saves every answer."""
    for item in items:
        if item["label"]:
            continue
        print(f"\n#{item['n']} {item['type']}, merged by {item['rule']}")
        print(f"  A: {item['a']} ({item['a_title']}): {item['a_context']}")
        print(f"  B: {item['b']} ({item['b_title']}): {item['b_context']}")
        choice = ""
        while choice not in ("y", "n", "s", "q"):
            choice = ask("  same entity? [y/n/s/q] ").strip().lower()
        if choice == "q":
            return
        if choice in ("y", "n"):
            item["label"] = "same" if choice == "y" else "different"
            save()


def merges_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.ingest graph merges")
    parser.add_argument("--corpus", choices=CORPORA, default="dev")
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--label", action="store_true", help="label the sampled decisions")
    parser.add_argument("--precision", action="store_true", help="precision over the labels")
    args = parser.parse_args(argv)

    def save(items: list[dict[str, str]]) -> None:
        LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(i, ensure_ascii=False) + "\n" for i in items]
        LABELS_PATH.write_text("".join(lines), encoding="utf-8")

    if args.label or args.precision:
        items = read_jsonl_dicts(LABELS_PATH)
        if args.label:
            label(items, input, lambda: save(items))
        print(json.dumps(precision(items), indent=2))
        return
    chunks, kept, _, _ = extract_corpus(args.corpus, None)
    names, texts = name_texts(kept)
    try:
        vecs = dict(zip(names, llm.embed(texts), strict=True))
    except RateLimited as e:
        raise SystemExit(f"name embeddings stopped by the quota ({e}); run embed slices") from e
    text = {c.chunk_id: c.text for c in chunks}
    context: dict[tuple[str, str, str], str] = {}
    for t in kept:
        doc = t.chunk_id.split(":", 1)[0]
        for name, type_ in ((t.subject, t.subject_type), (t.object, t.object_type)):
            context.setdefault((type_, normalize_name(name), doc), text[t.chunk_id])
    sample = sample_merges(merge_decisions(kept, vecs, ingest_cfg()["resolve"]), args.n)
    titles = store.doc_titles(sorted({s[k] for s in sample for k in ("a_doc", "b_doc")}))
    for s in sample:
        for side in ("a", "b"):
            s[f"{side}_title"] = titles.get(s[f"{side}_doc"], "")
            key = (s["type"], normalize_name(s[side]), s[f"{side}_doc"])
            s[f"{side}_context"] = context.get(key, "")
    save(sample)
    print(f"wrote {len(sample)} merge decisions to {LABELS_PATH}; label them with --label")


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["embed"]:
        return embed_main(argv[1:])
    if argv[:1] == ["merges"]:
        return merges_main(argv[1:])
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


def best_chunk(start: int, end: int, chunks: list[store.Span]) -> str | None:
    """The chunk sharing the most characters with the evidence span; a tie goes to the earlier."""
    best, most = None, 0
    for cid, lo, hi in chunks:
        overlap = min(end, hi) - max(start, lo)
        if overlap > most:
            best, most = cid, overlap
    return best


def relink_plan(
    rels: list[store.RelationRow], chunks: dict[str, list[store.Span]]
) -> tuple[list[tuple[str, str, str]], list[str], list[str]]:
    """(moves as (old id, new id, new chunk), duplicates dropped, relations left where they were).

    A relation moves to the serving chunk its evidence overlaps most, and its id follows its chunk.
    Two relations that land on one id are the same fact: the more confident one stays."""
    keep: dict[str, tuple[float, str, str]] = {}  # new id -> (confidence, old id, chunk)
    unmatched: list[str] = []
    for rel_id, s, p, o, chunk, doc, start, end, conf in rels:
        target = best_chunk(start, end, chunks.get(doc, []))
        if target is None:
            unmatched.append(rel_id)
            target = chunk
        # a relation that keeps its chunk keeps its id; a moved one takes the id of its new chunk
        new_id = rel_id if target == chunk else relation_id(s, p, o, target)
        if new_id not in keep or (conf, keep[new_id][1]) > (keep[new_id][0], rel_id):
            keep[new_id] = (conf, rel_id, target)
    kept = {old for _, old, _ in keep.values()}
    dropped = sorted(r[0] for r in rels if r[0] not in kept)
    moves = sorted((old, new, chunk) for new, (_, old, chunk) in keep.items() if new != old)
    return moves, dropped, unmatched


def relink_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="python -m adaptiverag.ingest relink")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    args = parser.parse_args(argv)
    strategy = router_cfg()["serving"]["chunk_strategy"]
    print(f"database: {endpoint()}, serving strategy: {strategy}")
    rels, chunks = store.relations_and_chunks(strategy)
    moves, dropped, unmatched = relink_plan(rels, chunks)
    summary: dict[str, Any] = {
        "relations": len(rels),
        "moved": len(moves),
        "merged_as_duplicates": len(dropped),
        "left_in_place_no_serving_chunk": len(unmatched),
    }
    if not args.dry_run:
        store.apply_relink(moves, dropped)
        summary["citing_another_strategy_after"] = store.off_strategy(strategy)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
