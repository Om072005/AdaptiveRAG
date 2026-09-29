"""python -m adaptiverag.eval.tune --split dev [--auto RUN --vector RUN --graph RUN --hybrid RUN]

Replays the router's decision table offline over stored dev runs for a grid of thresholds and
prints the config change that scores best. It never writes config: the section owner applies it.
Each question is scored with the F1 its route really got in the forced run of that route.
"""

import argparse
from dataclasses import dataclass
from statistics import mean
from typing import Any

import psycopg

from adaptiverag.config import router_cfg

ROUTES = ("vector", "graph", "hybrid")
MIN_CONFIDENCE_GRID = [round(0.30 + 0.05 * i, 2) for i in range(13)]  # 0.30 .. 0.90
MIN_TOP_SCORE_GRID = [round(0.30 + 0.05 * i, 2) for i in range(11)]  # 0.30 .. 0.80


@dataclass(frozen=True)
class Question:
    label: str
    confidence: float
    top_score: float  # best vector cosine in the forced vector run
    path_found: bool  # from the forced graph run
    f1: dict[str, float]  # route -> F1 in that route's forced run
    cost: dict[str, float]


def route_for(q: Question, min_confidence: float, min_top_score: float) -> str:
    """The decision table (rows 2, 3, 5 and fallbacks F1, F2) for one question."""
    if q.confidence < min_confidence:
        return "hybrid"
    if q.label == "single_hop":
        return "vector" if q.top_score >= min_top_score else "hybrid"
    return "graph" if q.path_found else "hybrid"


def simulate(qs: list[Question], min_confidence: float, min_top_score: float) -> dict[str, Any]:
    routes = [route_for(q, min_confidence, min_top_score) for q in qs]
    return {
        "min_confidence": min_confidence,
        "min_top_score": min_top_score,
        "f1": mean(q.f1[r] for q, r in zip(qs, routes, strict=True)),
        "cost": mean(q.cost[r] for q, r in zip(qs, routes, strict=True)),
        "routes": {r: routes.count(r) for r in ROUTES},
    }


def grid(qs: list[Question]) -> list[dict[str, Any]]:
    """Every threshold pair, best mean F1 first, cheaper first on a tie."""
    results = [simulate(qs, c, t) for c in MIN_CONFIDENCE_GRID for t in MIN_TOP_SCORE_GRID]
    return sorted(results, key=lambda r: (-r["f1"], r["cost"]))


def diff_lines(current: dict[str, Any], best: dict[str, Any]) -> list[str]:
    """Config lines to change, in the order of config/router.toml; empty if nothing improves."""
    if best["f1"] <= current["f1"]:
        return []
    lines = []
    for section, key in (("classifier", "min_confidence"), ("vector", "min_top_score")):
        if best[key] != current[key]:
            lines.append(f"[{section}] {key} = {current[key]} -> {best[key]}")
    return lines


def latest_run(c: psycopg.Connection[Any], split: str, mode: str) -> str:
    row = c.execute(
        "select run_id from eval_runs where split = %s and mode = %s"
        " order by created_at desc limit 1",
        (split, mode),
    ).fetchone()
    if row is None:
        raise SystemExit(f"no {mode} run on {split}; run eval.run --mode {mode} first")
    return str(row[0])


def load_questions(c: psycopg.Connection[Any], runs: dict[str, str]) -> list[Question]:
    """Questions present in all four runs, with classifier signals from the auto run."""
    per_run: dict[str, dict[str, tuple[Any, ...]]] = {}
    for mode, run_id in runs.items():
        rows = c.execute(
            "select r.question_id, r.f1, r.cost_usd, t.classifier_label, t.classifier_confidence,"
            " t.top_score, t.path_found from eval_results r"
            " left join traces t on t.trace_id = r.trace_id where r.run_id = %s",
            (run_id,),
        ).fetchall()
        per_run[mode] = {r[0]: r[1:] for r in rows}
    shared = set.intersection(*(set(v) for v in per_run.values()))
    out = []
    for qid in sorted(shared):
        auto = per_run["auto"][qid]
        if auto[2] is None or auto[3] is None:
            continue  # no classifier signal stored for this question
        out.append(
            Question(
                label=auto[2],
                confidence=float(auto[3]),
                top_score=float(per_run["vector"][qid][4] or 0),
                path_found=bool(per_run["graph"][qid][5]),
                f1={r: float(per_run[r][qid][0]) for r in ROUTES},
                cost={r: float(per_run[r][qid][1]) for r in ROUTES},
            )
        )
    return out


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.tune")
    p.add_argument("--split", choices=["mini", "dev"], default="dev")  # never tuned on test
    for mode in ("auto", *ROUTES):
        p.add_argument(f"--{mode}", metavar="RUN_ID", help=f"{mode} run (default: latest)")
    args = p.parse_args(argv)
    from adaptiverag.stores import db

    cfg = router_cfg()
    with db.conn() as c:
        runs = {m: getattr(args, m) or latest_run(c, args.split, m) for m in ("auto", *ROUTES)}
        qs = load_questions(c, runs)
    if not qs:
        raise SystemExit("no question is present in all four runs")
    current = simulate(qs, cfg["classifier"]["min_confidence"], cfg["vector"]["min_top_score"])
    ranked = grid(qs)
    print("runs: " + ", ".join(f"{m} {r}" for m, r in runs.items()))
    print(f"{len(qs)} questions; graph seeds are assumed found (not stored per question)")
    print("min_confidence  min_top_score  mean_f1  cost_per_query  vector/graph/hybrid")
    for r in [current, *ranked[:10]]:
        tag = "  (current config)" if r is current else ""
        counts = "/".join(str(r["routes"][x]) for x in ROUTES)
        print(
            f"{r['min_confidence']:>14}  {r['min_top_score']:>13}  {r['f1']:.4f}"
            f"  {r['cost']:.6f}  {counts}{tag}"
        )
    lines = diff_lines(current, ranked[0])
    print("\nsuggested config/router.toml change (not applied):")
    print(
        "\n".join(lines) if lines else "none, the current thresholds are already best on this grid"
    )


if __name__ == "__main__":
    main()
