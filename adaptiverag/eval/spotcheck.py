"""python -m adaptiverag.eval.spotcheck sample|score|agreement <run_id> [--reviewer X] [--n 20]

The README's second judge mitigation: a person scores a fixed sample of a judged run with the same
rubric (docs/eval-protocol.md), and the judge is compared with them.
"""

import argparse
import random
from statistics import mean
from typing import Any

import psycopg

from adaptiverag.config import router_cfg
from adaptiverag.eval.judge import RUBRIC, SCORES
from adaptiverag.eval.review import default_reviewer

SAMPLE_SIZE = 20  # per pinned run, as the evaluation protocol states
CLOSE = 0.25  # one step on the 1 to 5 scale


def sample_ids(question_ids: list[str], run_id: str, n: int = SAMPLE_SIZE) -> list[str]:
    """The same n questions for a run every time, whoever asks."""
    ids = sorted(question_ids)
    return sorted(random.Random(run_id).sample(ids, min(n, len(ids))))


def agreement(
    pairs: list[tuple[dict[str, float], dict[str, float]]], flag_below: float
) -> dict[str, Any]:
    """Judge against manual scores per metric: mean absolute gap, share within one scale step, and
    how often both sides make the same flag decision."""
    out: dict[str, Any] = {"n": len(pairs)}
    for m in SCORES:
        gaps = [abs(j[m] - h[m]) for j, h in pairs]
        out[m] = {
            "mean_abs_gap": mean(gaps) if gaps else None,
            "within_one_step": mean(g <= CLOSE + 1e-9 for g in gaps) if gaps else None,
        }
    flags = [
        any(j[m] < flag_below for m in SCORES) == any(h[m] < flag_below for m in SCORES)
        for j, h in pairs
    ]
    out["same_flag_decision"] = mean(flags) if flags else None
    return out


def answer_text(detail: dict[str, Any]) -> str:
    """The answer from traces.detail, stored either as text or inside a QueryResponse."""
    a = detail.get("answer", "")
    return str(a.get("text", "") if isinstance(a, dict) else a)


def parse_score(raw: str) -> float | None:
    """1..5 typed by a person, mapped to 0..1 like the judge; None if not a valid score."""
    raw = raw.strip()
    return (int(raw) - 1) / 4 if raw in {"1", "2", "3", "4", "5"} else None


def judged(c: psycopg.Connection[Any], run_id: str) -> list[tuple[Any, ...]]:
    return c.execute(
        "select r.question_id, r.faithfulness, r.relevance, r.completeness, t.question, t.detail"
        " from eval_results r join traces t on t.trace_id = r.trace_id"
        " where r.run_id = %s and r.faithfulness is not null order by r.question_id",
        (run_id,),
    ).fetchall()


def score(c: psycopg.Connection[Any], run_id: str, reviewer: str, n: int, ask: Any = input) -> int:
    """Walk the sample, skipping what this reviewer already scored. Returns the count added."""
    rows = {r[0]: r for r in judged(c, run_id)}
    done = {
        r[0]
        for r in c.execute(
            "select question_id from manual_scores where run_id = %s and reviewer = %s",
            (run_id, reviewer),
        )
    }
    added = 0
    print(RUBRIC)
    for qid in sample_ids(list(rows), run_id, n):
        if qid in done:
            continue
        _, _, _, _, question, detail = rows[qid]
        print(f"\n{qid}\nQ: {question}\nAnswer:\n{answer_text(detail)}")
        for h in (detail.get("retrieval") or {}).get("hits", []):
            print(f"  [{h['rank']}] {h['title']}: {h['snippet']}")
        got: dict[str, float] = {}
        for m in SCORES:
            value = None
            while value is None:
                value = parse_score(ask(f"  {m} 1-5: "))
            got[m] = value
        c.execute(
            "insert into manual_scores (run_id, question_id, reviewer, faithfulness, relevance,"
            " completeness, notes) values (%s, %s, %s, %s, %s, %s, %s)",
            (
                run_id,
                qid,
                reviewer,
                got["faithfulness"],
                got["relevance"],
                got["completeness"],
                ask("  notes (optional): ").strip() or None,
            ),
        )
        c.commit()
        added += 1
    return added


def load_pairs(
    c: psycopg.Connection[Any], run_id: str
) -> list[tuple[dict[str, float], dict[str, float]]]:
    rows = c.execute(
        "select r.faithfulness, r.relevance, r.completeness, m.faithfulness, m.relevance,"
        " m.completeness from manual_scores m join eval_results r"
        " on r.run_id = m.run_id and r.question_id = m.question_id"
        " where m.run_id = %s and r.faithfulness is not null",
        (run_id,),
    ).fetchall()
    return [
        (
            dict(zip(SCORES, map(float, r[:3]), strict=True)),
            dict(zip(SCORES, map(float, r[3:]), strict=True)),
        )
        for r in rows
    ]


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.spotcheck")
    p.add_argument("cmd", choices=["sample", "score", "agreement"])
    p.add_argument("run_id")
    p.add_argument("--n", type=int, default=SAMPLE_SIZE)
    p.add_argument("--reviewer", default=default_reviewer())
    args = p.parse_args(argv)
    from adaptiverag.stores import db

    with db.conn() as c:
        if args.cmd == "sample":
            print(
                "\n".join(sample_ids([r[0] for r in judged(c, args.run_id)], args.run_id, args.n))
            )
        elif args.cmd == "score":
            print(f"scored {score(c, args.run_id, args.reviewer, args.n)} answers")
        else:
            a = agreement(load_pairs(c, args.run_id), router_cfg()["judge"]["flag_below"])
            print(f"{a['n']} judge and manual score pairs on {args.run_id}")
            for m in SCORES:
                gap, step = a[m]["mean_abs_gap"], a[m]["within_one_step"]
                print(f"  {m}: mean gap {gap}, within one step {step}")
            print(f"  same flag decision: {a['same_flag_decision']}")


if __name__ == "__main__":
    main()
