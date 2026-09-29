"""python -m adaptiverag.eval.run --split dev --mode auto --variant <name> [options]

Options: --judge, --limit N, --size small|large, --questions <file.toml>,
--resume <run_id>, --pin (contract section 3).
"""

import argparse
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from statistics import mean
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from adaptiverag.config import ROOT, config_hash, router_cfg, settings
from adaptiverag.eval import gold, metrics
from adaptiverag.eval.gold import GoldItem
from adaptiverag.llm import RateLimited
from adaptiverag.stores import db
from adaptiverag.types import Mode, ModelSize, QueryResult

AnswerFn = Callable[..., QueryResult]
MODES = ("auto", "vector", "graph", "hybrid")
SIZE_VARIANTS = {"always-small": "small", "always-large": "large"}
METRICS = ("em", "f1", "recall_at_k", "mrr", "sp_precision")
MINI_QUESTIONS = 30  # the mini corpus size from contract section 4


def make_run_id(now: datetime, split: str, mode: str, variant: str) -> str:
    return f"{now:%Y%m%d-%H%M}-{split}-{mode}-{variant}"


def check_args(split: str, variant: str, size: str | None, allow_test: bool) -> None:
    """Refuse a locked test split, or a size that contradicts the variant name."""
    if split == "test" and not allow_test:
        raise SystemExit("the test split is locked, set ALLOW_TEST=1 (D13 pinned runs only)")
    want = SIZE_VARIANTS.get(variant)
    if want and size != want:
        raise SystemExit(f"variant {variant} needs --size {want}")


def git_state() -> tuple[str, bool]:
    """(HEAD sha, whether the working tree has uncommitted changes)."""
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    return sha, bool(dirty)


def chunk_spans(
    doc_spans: list[tuple[str, int, int]], chunks: dict[str, tuple[str, int, int]]
) -> list[tuple[str, int, int]]:
    """Document level sentence spans to chunk relative spans, clipped; spans off a chunk dropped."""
    out = []
    for chunk_id, (doc_id, c_start, c_end) in chunks.items():
        for d, s, e in doc_spans:
            start, end = max(s, c_start), min(e, c_end)
            if d == doc_id and start < end:
                out.append((chunk_id, start - c_start, end - c_start))
    return out


def score(
    item: GoldItem, result: QueryResult, spans: list[tuple[str, int, int]], k: int
) -> dict[str, Any]:
    """One eval_results row (without run_id) from a gold item and a query result."""
    hits = result.retrieved.hits
    c = result.decision.classification
    return {
        "question_id": item.id,
        "trace_id": result.trace_id,
        "gold_type": item.type,
        "predicted_type": c.label if c else None,
        "route_taken": result.decision.final,
        "em": metrics.em(result.answer.short, item.answer),
        "f1": metrics.f1(result.answer.short, item.answer),
        "recall_at_k": metrics.recall_at_k(hits, item.supporting_titles, k),
        "mrr": metrics.mrr(hits, item.supporting_titles),
        "sp_precision": metrics.sp_precision(hits, spans),
        "cost_usd": result.total_cost_usd,
        "latency_ms": result.total_latency_ms,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Means per metric overall and per gold type, plus the count."""
    if not rows:
        return {"n_done": 0}
    by_type = {}
    for t in sorted({r["gold_type"] for r in rows}):
        sub = [r for r in rows if r["gold_type"] == t]
        by_type[t] = {"n": len(sub), **{m: mean(float(r[m]) for r in sub) for m in METRICS}}
    return {
        "n_done": len(rows),
        **{m: mean(float(r[m]) for r in rows) for m in METRICS},
        "cost_usd": mean(float(r["cost_usd"]) for r in rows),
        "by_type": by_type,
    }


def supporting_spans(
    c: psycopg.Connection[Any], item: GoldItem, hit_ids: list[str]
) -> list[tuple[str, int, int]]:
    """Chunk relative spans of the item's supporting sentences inside the retrieved chunks."""
    rows = c.execute(
        "select doc_id, title, sentences from documents where title = any(%s)",
        (item.supporting_titles,),
    ).fetchall()
    sentences = {title: (doc_id, spans) for doc_id, title, spans in rows}
    doc_spans = [
        (sentences[t][0], *sentences[t][1][i])
        for t, i in item.supporting_sentences
        if t in sentences and i < len(sentences[t][1])
    ]
    chunks = c.execute(
        "select chunk_id, doc_id, start_offset, end_offset from chunks where chunk_id = any(%s)",
        (hit_ids,),
    ).fetchall()
    return chunk_spans(doc_spans, {cid: (d, s, e) for cid, d, s, e in chunks})


def execute(
    c: psycopg.Connection[Any],
    items: list[GoldItem],
    run_id: str,
    mode: Mode,
    size: ModelSize | None,
    answer: AnswerFn,
) -> list[dict[str, Any]]:
    """Answer and score each item, committing one eval_results row per question.

    RateLimited propagates after the rows so far are committed, so the run can resume."""
    k = router_cfg()["vector"]["k"]
    rows = []
    for item in items:
        result = answer(item.question, mode, source="eval", force_size=size)
        spans = supporting_spans(c, item, [h.chunk_id for h in result.retrieved.hits])
        row = score(item, result, spans, k)
        c.execute(
            "insert into eval_results (run_id, question_id, trace_id, gold_type, predicted_type,"
            " route_taken, em, f1, recall_at_k, mrr, sp_precision, cost_usd, latency_ms) values"
            " (%(run_id)s, %(question_id)s, %(trace_id)s, %(gold_type)s, %(predicted_type)s,"
            " %(route_taken)s, %(em)s, %(f1)s, %(recall_at_k)s, %(mrr)s, %(sp_precision)s,"
            " %(cost_usd)s, %(latency_ms)s)",
            {"run_id": run_id, **row},
        )
        c.commit()
        rows.append(row)
    return rows


def select_items(split: str, limit: int | None) -> list[GoldItem]:
    if split == "mini":
        # mini = dev questions whose supporting paragraphs are all in the mini corpus
        from adaptiverag.ingest.loader import load_hotpot

        titles = {d.title for d in load_hotpot(MINI_QUESTIONS)[0]}
        items = [i for i in gold.load_split("dev") if set(i.supporting_titles) <= titles]
    else:
        items = gold.load_split(split)
    return items[:limit] if limit else items


def main(argv: list[str] | None = None, answer: AnswerFn | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.run")
    p.add_argument("--split", choices=["mini", "dev", "test"], required=True)
    p.add_argument("--mode", choices=MODES, required=True)
    p.add_argument("--variant", required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--size", choices=["small", "large"])
    p.add_argument("--judge", action="store_true")
    p.add_argument("--questions")
    p.add_argument("--resume")
    p.add_argument("--pin", action="store_true")
    args = p.parse_args(argv)
    check_args(args.split, args.variant, args.size, settings().allow_test)
    for flag in ("judge", "questions", "resume", "pin"):
        if getattr(args, flag):
            raise SystemExit(f"--{flag} is not built yet")
    if answer is None:
        from adaptiverag.pipeline import answer_query

        answer = answer_query

    items = select_items(args.split, args.limit)
    sha, dirty = git_state()
    run_id = make_run_id(datetime.now(), args.split, args.mode, args.variant)
    with db.conn() as c:
        c.execute("select 1")  # wake a suspended Neon compute before anything is timed
        c.execute(
            "insert into eval_runs (run_id, split, mode, variant, git_sha, git_dirty,"
            " config_hash, n) values (%s, %s, %s, %s, %s, %s, %s, %s)",
            (run_id, args.split, args.mode, args.variant, sha, dirty, config_hash(), len(items)),
        )
        c.commit()
        try:
            rows = execute(c, items, run_id, args.mode, args.size, answer)
        except RateLimited:
            print(f"rate limited, progress saved: resume with --resume {run_id}", file=sys.stderr)
            raise SystemExit(2) from None
        summary = summarize(rows)
        c.execute("update eval_runs set summary = %s where run_id = %s", (Jsonb(summary), run_id))
        c.commit()
    print(f"{run_id}: {len(rows)} questions, f1 {summary.get('f1', 0):.3f}")


if __name__ == "__main__":
    main()
