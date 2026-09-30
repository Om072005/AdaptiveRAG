"""python -m adaptiverag.eval.rejudge <run_id> [<run_id> ...]

Judges the questions of a judged run whose judge call failed (decision D22). Each answer is rebuilt
through the pipeline from the model cache, so the judge sees the same prompt it saw in the run; the
verdict is stored on the run's own trace and eval_results row. The rebuilt answer's trace is saved
with source "cli" (traces.source allows demo, eval, cli, example), so eval metrics never count it.
"""

import argparse
import sys
from collections.abc import Callable
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from adaptiverag.eval import gold, judge
from adaptiverag.eval.run import JUDGE_METRICS, result_rows, store_judgement, summarize
from adaptiverag.eval.spotcheck import answer_text
from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Mode, ModelSize

Missing = tuple[str, str, str]  # (question_id, the run's trace_id, the run's answer text)


def missing(c: psycopg.Connection[Any], run_id: str) -> list[Missing]:
    rows = c.execute(
        "select r.question_id, r.trace_id::text, t.detail from eval_results r"
        " join traces t on t.trace_id = r.trace_id"
        " where r.run_id = %s and r.faithfulness is null order by r.question_id",
        (run_id,),
    ).fetchall()
    return [(str(q), str(t), answer_text(d or {})) for q, t, d in rows]


def rejudge(
    todo: list[Missing],
    questions: dict[str, str],
    mode: Mode,
    size: ModelSize | None,
    answer: Callable[..., Any],
    judge_one: Callable[..., dict[str, Any]],
    store: Callable[[str, str, dict[str, Any], Trace], None],
) -> tuple[int, list[str]]:
    """Judge each missing question; store(question_id, trace_id, verdict, judge_trace). Returns
    (judged, question ids that failed again or whose rebuilt answer differs from the run's).
    A rebuilt answer that differs (a model cache miss, or a parser change) is never judged in the
    run's name: the verdict would score a different answer than the one the run recorded."""
    judged, failed = 0, []
    for qid, trace_id, original in todo:
        question = questions[qid]
        result = answer(question, mode, source="cli", force_size=size)
        if result.answer.text.strip() != original.strip():
            print(f"rebuilt answer differs from the run's on {qid}, not judged", file=sys.stderr)
            failed.append(qid)
            continue
        judge_trace = Trace(question, mode, "eval")
        try:
            verdict = judge_one(question, result.answer, result.retrieved, judge_trace)
        except judge.JudgeFailed as e:
            print(f"judge failed again on {qid}: {e}", file=sys.stderr)
            failed.append(qid)
            continue
        store(qid, trace_id, verdict, judge_trace)
        judged += 1
    return judged, failed


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.rejudge")
    p.add_argument("run_ids", nargs="+")
    args = p.parse_args(argv)
    from adaptiverag import pipeline
    from adaptiverag.stores import db

    for run_id in args.run_ids:
        with db.conn() as c:
            row = c.execute(
                "select split, mode, summary from eval_runs where run_id = %s", (run_id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"no run {run_id}")
            split, mode, summary = row
            options = (summary or {}).get("options", {})
            if not options.get("judge"):
                raise SystemExit(f"{run_id} is not a judged run")
            questions = {i.id: i.question for i in gold.load_split(split)}
            todo = missing(c, run_id)

            def store(
                qid: str, trace_id: str, verdict: dict[str, Any], jt: Trace, rid: str = run_id
            ) -> None:
                store_judgement(c, trace_id, verdict, jt)
                c.execute(
                    "update eval_results set faithfulness = %s, relevance = %s, completeness = %s"
                    " where run_id = %s and question_id = %s",
                    (*(verdict[m] for m in JUDGE_METRICS), rid, qid),
                )
                c.commit()

            judged, failed = 0, list[str]()
            try:
                judged, failed = rejudge(
                    todo,
                    questions,
                    mode,
                    options.get("size"),
                    pipeline.answer_query,
                    judge.judge,
                    store,
                )
            finally:  # the summary follows the stored rows even when the loop stops early
                summary = summarize(result_rows(c, run_id), True)
                c.execute(
                    "update eval_runs set summary = summary || %s where run_id = %s",
                    (Jsonb(summary), run_id),
                )
                c.commit()
        print(f"{run_id}: {len(todo)} unjudged, {judged} judged now, {len(failed)} not judged")


if __name__ == "__main__":
    main()
