"""python -m adaptiverag.eval.run --split dev --mode auto --variant <name> [options]

Options: --judge, --limit N, --size small|large, --questions <file.toml>,
--resume <run_id>, --pin (contract section 3). A run always covers its whole split; --limit N
answers at most N more questions in this call, and --resume continues from there.
"""

import argparse
import subprocess
import sys
import tomllib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any
from urllib.parse import urlparse

import psycopg
from psycopg.types.json import Jsonb

from adaptiverag.config import ROOT, config_hash, router_cfg, settings
from adaptiverag.eval import gold, judge, metrics
from adaptiverag.eval.gold import GoldItem
from adaptiverag.llm import RateLimited
from adaptiverag.stores import db
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Mode, ModelSize, QueryResult

AnswerFn = Callable[..., QueryResult]
MODES = ("auto", "vector", "graph", "hybrid")
SIZE_VARIANTS = {"always-small": "small", "always-large": "large"}
METRICS = ("em", "f1", "recall_at_k", "mrr", "sp_precision")
JUDGE_METRICS = ("faithfulness", "relevance", "completeness")
# Neon main's endpoint (contract section 1): pinned runs are the only ones the README and page quote
NEON_MAIN_HOST_PREFIX = "ep-patient-wave-b3c33ztv"
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


def pin_problems(dirty: bool, database_url: str) -> list[str]:
    """Why a run may not be pinned: a dirty working tree or a database other than Neon main."""
    found = []
    if dirty:
        found.append("the working tree has uncommitted changes")
    if not (urlparse(database_url).hostname or "").startswith(NEON_MAIN_HOST_PREFIX):
        found.append("DATABASE_URL is not Neon main")
    return found


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


def summarize(rows: list[dict[str, Any]], judged: bool = False) -> dict[str, Any]:
    """Means per metric overall and per gold type, plus judge means and failures if judged."""
    if not rows:
        return {"n_done": 0}
    by_type = {}
    for t in sorted({r["gold_type"] for r in rows}):
        sub = [r for r in rows if r["gold_type"] == t]
        by_type[t] = {"n": len(sub), **{m: mean(float(r[m]) for r in sub) for m in METRICS}}
    out = {
        "n_done": len(rows),
        **{m: mean(float(r[m]) for r in rows) for m in METRICS},
        "cost_usd": mean(float(r["cost_usd"]) for r in rows),
        "by_type": by_type,
    }
    if judged:
        scored = [r for r in rows if r.get("faithfulness") is not None]
        out |= {m: mean(float(r[m]) for r in scored) if scored else None for m in JUDGE_METRICS}
        # in a judged run a missing score means the judge failed twice on that question
        out["judge_failures"] = [r["question_id"] for r in rows if r.get("faithfulness") is None]
    return out


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


def store_judgement(
    c: psycopg.Connection[Any], trace_id: str, verdict: dict[str, Any], judge_trace: Trace
) -> None:
    """judgements row, the judge calls on the answer's llm_calls ledger, and the trace's costs."""
    c.execute(
        "insert into judgements (trace_id, faithfulness, relevance, completeness, rationale,"
        " model, cost_usd) values (%s, %s, %s, %s, %s, %s, %s)",
        (
            trace_id,
            *(verdict[m] for m in JUDGE_METRICS),
            verdict["rationale"],
            verdict["model"],
            verdict["cost_usd"],
        ),
    )
    for call in judge_trace.call_rows():
        c.execute(
            "insert into llm_calls (trace_id, role, model, tokens_in, tokens_out, cost_usd,"
            " latency_ms, cached, estimated, retries, wait_ms) values (%(trace_id)s, %(role)s,"
            " %(model)s, %(tokens_in)s, %(tokens_out)s, %(cost_usd)s, %(latency_ms)s, %(cached)s,"
            " %(estimated)s, %(retries)s, %(wait_ms)s)",
            {**call, "trace_id": trace_id},
        )
    c.execute(
        "update traces set eval_cost_usd = eval_cost_usd + %s,"
        " total_cost_usd = total_cost_usd + %s where trace_id = %s",
        (verdict["cost_usd"], verdict["cost_usd"], trace_id),
    )


def execute(
    c: psycopg.Connection[Any],
    items: list[GoldItem],
    run_id: str,
    mode: Mode,
    size: ModelSize | None,
    answer: AnswerFn,
    judged: bool = False,
) -> list[dict[str, Any]]:
    """Answer and score each item, committing one eval_results row per question.

    RateLimited propagates after the rows so far are committed, so the run can resume."""
    k = router_cfg()["vector"]["k"]
    rows = []
    for item in items:
        result = answer(item.question, mode, source="eval", force_size=size)
        spans = supporting_spans(c, item, [h.chunk_id for h in result.retrieved.hits])
        row = score(item, result, spans, k) | dict.fromkeys(JUDGE_METRICS)
        if judged:
            judge_trace = Trace(item.question, mode, "eval")
            try:
                verdict = judge.judge(item.question, result.answer, result.retrieved, judge_trace)
                row |= {m: verdict[m] for m in JUDGE_METRICS}
                store_judgement(c, result.trace_id, verdict, judge_trace)
            except judge.JudgeFailed as e:
                print(f"judge failed on {item.id}: {e}", file=sys.stderr)
        c.execute(
            "insert into eval_results (run_id, question_id, trace_id, gold_type, predicted_type,"
            " route_taken, em, f1, recall_at_k, mrr, sp_precision, faithfulness, relevance,"
            " completeness, cost_usd, latency_ms) values (%(run_id)s, %(question_id)s,"
            " %(trace_id)s, %(gold_type)s, %(predicted_type)s, %(route_taken)s, %(em)s, %(f1)s,"
            " %(recall_at_k)s, %(mrr)s, %(sp_precision)s, %(faithfulness)s, %(relevance)s,"
            " %(completeness)s, %(cost_usd)s, %(latency_ms)s)",
            {"run_id": run_id, **row},
        )
        c.commit()
        rows.append(row)
    return rows


def question_ids(path: str) -> list[str]:
    """The [[question]] ids of a questions file such as docs/results/replays.toml."""
    return [
        q["id"] for q in tomllib.loads(Path(path).read_text(encoding="utf-8")).get("question", [])
    ]


def only(items: list[GoldItem], ids: list[str] | None) -> list[GoldItem]:
    """The items named in ids, refusing ids that are not in the split."""
    if ids is None:
        return items
    missing = set(ids) - {i.id for i in items}
    if missing:
        raise SystemExit(f"not in this split: {', '.join(sorted(missing))}")
    return [i for i in items if i.id in set(ids)]


def select_items(split: str) -> list[GoldItem]:
    if split == "mini":
        # mini = dev questions whose supporting paragraphs are all in the mini corpus
        from adaptiverag.ingest.loader import load_hotpot

        titles = {d.title for d in load_hotpot(MINI_QUESTIONS)[0]}
        items = [i for i in gold.load_split("dev") if set(i.supporting_titles) <= titles]
    else:
        items = gold.load_split(split)
    return items


def result_rows(c: psycopg.Connection[Any], run_id: str) -> list[dict[str, Any]]:
    cur = c.execute(
        "select question_id, gold_type, em, f1, recall_at_k, mrr, sp_precision, faithfulness,"
        " relevance, completeness, cost_usd from eval_results where run_id = %s"
        " order by question_id",
        (run_id,),
    )
    names = [d.name for d in cur.description or []]
    return [dict(zip(names, r, strict=True)) for r in cur.fetchall()]


def start_run(c: psycopg.Connection[Any], args: argparse.Namespace) -> tuple[str, list[GoldItem]]:
    """Insert a new eval_runs row; the options needed to resume go into its summary."""
    ids = question_ids(args.questions) if args.questions else None
    items = only(select_items(args.split), ids)
    sha, dirty = git_state()
    run_id = make_run_id(datetime.now(), args.split, args.mode, args.variant)
    options = {"size": args.size, "judge": args.judge, "questions": ids}
    c.execute(
        "insert into eval_runs (run_id, split, mode, variant, git_sha, git_dirty, config_hash, n,"
        " summary) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            run_id,
            args.split,
            args.mode,
            args.variant,
            sha,
            dirty,
            config_hash(),
            len(items),
            Jsonb({"options": options}),
        ),
    )
    c.commit()
    return run_id, items


def resume_run(c: psycopg.Connection[Any], args: argparse.Namespace) -> tuple[str, list[GoldItem]]:
    """Reload a stopped run's options and return the questions it has not stored yet."""
    row = c.execute(
        "select split, mode, variant, config_hash, summary from eval_runs where run_id = %s",
        (args.resume,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"no run {args.resume}")
    split, mode, variant, cfg_hash, summary = row
    if cfg_hash != config_hash():
        raise SystemExit(f"config changed since {args.resume} started; start a new run instead")
    options = summary["options"]
    check_args(split, variant, options["size"], settings().allow_test)
    args.split, args.mode, args.variant, args.size = split, mode, variant, options["size"]
    args.judge = options.get("judge", False)
    done = {r["question_id"] for r in result_rows(c, args.resume)}
    items = only(select_items(split), options.get("questions"))
    return args.resume, [i for i in items if i.id not in done]


def main(argv: list[str] | None = None, answer: AnswerFn | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.run")
    p.add_argument("--split", choices=["mini", "dev", "test"])
    p.add_argument("--mode", choices=MODES)
    p.add_argument("--variant")
    p.add_argument("--limit", type=int)
    p.add_argument("--size", choices=["small", "large"])
    p.add_argument("--judge", action="store_true")
    p.add_argument("--questions")
    p.add_argument("--resume", metavar="RUN_ID")
    p.add_argument("--pin", action="store_true")
    args = p.parse_args(argv)
    if not args.resume and not (args.split and args.mode and args.variant):
        p.error("--split, --mode and --variant are required unless --resume is given")
    if not args.resume:
        # refuse before any connection is opened; a resumed run is checked once its row is read
        check_args(args.split, args.variant, args.size, settings().allow_test)
    if args.pin and (found := pin_problems(git_state()[1], settings().database_url)):
        raise SystemExit("--pin refused: " + "; ".join(found))
    if answer is None:
        from adaptiverag.pipeline import answer_query

        answer = answer_query

    with db.conn() as c:
        c.execute("select 1")  # wake a suspended Neon compute before anything is timed
        run_id, items = resume_run(c, args) if args.resume else start_run(c, args)
        try:
            execute(c, items[: args.limit], run_id, args.mode, args.size, answer, args.judge)
        except RateLimited:
            print(f"rate limited, progress saved: resume with --resume {run_id}", file=sys.stderr)
            raise SystemExit(2) from None
        summary = summarize(result_rows(c, run_id), args.judge)
        c.execute(
            "update eval_runs set summary = summary || %s where run_id = %s",
            (Jsonb(summary), run_id),
        )
        c.commit()
    print(f"{run_id}: {summary['n_done']} questions stored, f1 {summary.get('f1', 0):.3f}")


if __name__ == "__main__":
    main()
