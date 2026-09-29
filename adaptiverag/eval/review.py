"""python -m adaptiverag.eval.review queue <run_id> | list | label <id> <status> [--notes ...]

The README feedback loop: judged answers below threshold wait in review_queue as 'open'; a reviewer
labels each one ok, misroute (router tuning), bad_chunks (retrieval tuning), bad_triples
(extraction tuning) or bad_generation.
"""

import argparse
import subprocess
from typing import Any

import psycopg

from adaptiverag.config import ROOT, router_cfg

JUDGE_METRICS = ("faithfulness", "relevance", "completeness")
STATUSES = ("open", "ok", "misroute", "bad_chunks", "bad_triples", "bad_generation")


def flag_reasons(
    row: dict[str, Any], flag_below: float, min_answer_confidence: float
) -> list[tuple[str, str, float]]:
    """(reason, metric, score) for every reason one eval result needs a human look."""
    found = [
        ("judge_below_threshold", m, float(row[m]))
        for m in JUDGE_METRICS
        if row.get(m) is not None and float(row[m]) < flag_below
    ]
    conf = row.get("answer_confidence")
    if conf is not None and float(conf) < min_answer_confidence:
        found.append(("answer_confidence_low", "answer_confidence", float(conf)))
    predicted = row.get("predicted_type")
    if predicted is not None and predicted != row["gold_type"]:
        found.append(
            ("misroute", "classifier_confidence", float(row.get("classifier_confidence") or 0))
        )
    return found


def queue_run(c: psycopg.Connection[Any], run_id: str) -> int:
    """Insert review_queue rows for a run; a rerun adds nothing new. Returns the count."""
    cfg = router_cfg()
    cur = c.execute(
        "select r.trace_id, r.gold_type, r.predicted_type, r.faithfulness, r.relevance,"
        " r.completeness, t.answer_confidence, t.classifier_confidence"
        " from eval_results r left join traces t on t.trace_id = r.trace_id where r.run_id = %s",
        (run_id,),
    )
    names = [d.name for d in cur.description or []]
    added = 0
    for values in cur.fetchall():
        row = dict(zip(names, values, strict=True))
        reasons = flag_reasons(row, cfg["judge"]["flag_below"], cfg["answer"]["min_confidence"])
        for reason, metric, score in reasons:
            added += c.execute(
                "insert into review_queue (trace_id, run_id, reason, metric, score)"
                " select %s, %s, %s, %s, %s where not exists (select 1 from review_queue"
                " where trace_id = %s and run_id = %s and reason = %s and metric = %s)",
                (
                    row["trace_id"],
                    run_id,
                    reason,
                    metric,
                    score,
                    row["trace_id"],
                    run_id,
                    reason,
                    metric,
                ),
            ).rowcount
    c.commit()
    return added


def list_items(c: psycopg.Connection[Any], status: str | None) -> list[tuple[Any, ...]]:
    return c.execute(
        "select q.id, q.run_id, q.reason, q.metric, q.score, q.status, t.question"
        " from review_queue q left join traces t on t.trace_id = q.trace_id"
        " where %s::text is null or q.status = %s order by q.id",
        (status, status),
    ).fetchall()


def label(
    c: psycopg.Connection[Any], item_id: int, status: str, reviewer: str, notes: str | None
) -> None:
    """Record a reviewer's verdict; a status back to open clears the resolution time."""
    if status not in STATUSES:
        raise SystemExit(f"status must be one of {', '.join(STATUSES)}")
    n = c.execute(
        "update review_queue set status = %s, reviewer = %s, notes = coalesce(%s, notes),"
        " resolved_at = case when %s = 'open' then null else now() end where id = %s",
        (status, reviewer, notes, status, item_id),
    ).rowcount
    if n == 0:
        raise SystemExit(f"no review item {item_id}")
    c.commit()


def default_reviewer() -> str:
    name = subprocess.run(
        ["git", "config", "user.name"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    return name.split(" ")[0].lower() if name else ""


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.review")
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("queue", help="queue a judged run's low scores and misroutes")
    q.add_argument("run_id")
    ls = sub.add_parser("list", help="review items, open ones by default")
    ls.add_argument("--status", choices=STATUSES, default="open")
    ls.add_argument("--all", action="store_true")
    lb = sub.add_parser("label", help="set an item's status")
    lb.add_argument("id", type=int)
    lb.add_argument("status", choices=STATUSES)
    lb.add_argument("--notes")
    lb.add_argument("--reviewer", default=default_reviewer())
    args = p.parse_args(argv)
    from adaptiverag.stores import db

    with db.conn() as c:
        if args.cmd == "queue":
            print(f"queued {queue_run(c, args.run_id)} new items from {args.run_id}")
        elif args.cmd == "list":
            for item_id, run_id, reason, metric, score, status, question in list_items(
                c, None if args.all else args.status
            ):
                flag = f"{reason} {metric}={score:.2f}"
                print(f"{item_id:>5}  {status:<14} {flag}  {run_id}  {question}")
        else:
            label(c, args.id, args.status, args.reviewer, args.notes)
            print(f"item {args.id} is now {args.status}")


if __name__ == "__main__":
    main()
