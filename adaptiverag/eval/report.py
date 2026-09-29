"""python -m adaptiverag.eval.report <run_id> [--vs <run_id>] | bake | replays"""

import argparse
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

import psycopg

from adaptiverag.config import ROOT

RESULTS_DIR = ROOT / "docs" / "results"
METRICS = (
    "em",
    "f1",
    "recall_at_k",
    "mrr",
    "sp_precision",
    "faithfulness",
    "relevance",
    "completeness",
)
QTYPES = ("single_hop", "multi_hop", "comparison")


def percentile(values: list[float], p: float) -> float | None:
    """Nearest rank percentile (the smallest value with at least p percent at or below it)."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Means per metric (unscored rows left out), cost per query and latency percentiles."""

    def means(sub: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {"n": len(sub)}
        for m in METRICS:
            vals = [float(r[m]) for r in sub if r.get(m) is not None]
            out[m] = mean(vals) if vals else None
        return out

    latencies = [float(r["latency_ms"]) for r in rows]
    return {
        **means(rows),
        "cost_per_query_usd": mean(float(r["cost_usd"]) for r in rows) if rows else None,
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "by_type": {
            t: means(sub) for t in QTYPES if (sub := [r for r in rows if r["gold_type"] == t])
        },
    }


def delta(new: float | None, old: float | None) -> float | None:
    return None if new is None or old is None else new - old


def diff(new: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    """new minus old for every metric, overall and per type present in both runs."""
    keys = (*METRICS, "cost_per_query_usd", "p50_ms", "p95_ms")
    return {
        "overall": {k: delta(new.get(k), old.get(k)) for k in keys},
        "by_type": {
            t: {m: delta(new["by_type"][t][m], old["by_type"][t][m]) for m in METRICS}
            for t in QTYPES
            if t in new["by_type"] and t in old["by_type"]
        },
    }


def fmt(v: float | None, signed: bool = False) -> str:
    if v is None:
        return "n/a"
    return f"{v:+.3f}" if signed else f"{v:.3f}"


def render_md(run: dict[str, Any], agg: dict[str, Any], vs: dict[str, Any] | None) -> str:
    """The run report: header with provenance, overall table, per type table, diffs if any."""
    d = diff(agg, vs["aggregate"]) if vs else None
    lines = [
        f"# {run['run_id']}",
        "",
        f"split `{run['split']}` · mode `{run['mode']}` · variant `{run['variant']}` · "
        f"git `{run['git_sha'][:12]}`{' (dirty)' if run['git_dirty'] else ''} · "
        f"config `{run['config_hash']}` · {agg['n']} of {run['n']} questions stored",
        "",
        f"Compared with: `{vs['run']['run_id']}`"
        if vs
        else "Compared with: no earlier comparable run",
        "",
        "| metric | value | change |",
        "|---|---|---|",
    ]
    for k in (*METRICS, "cost_per_query_usd", "p50_ms", "p95_ms"):
        change = fmt(d["overall"][k], signed=True) if d else ""
        lines.append(f"| {k} | {fmt(agg[k])} | {change} |")
    lines += [
        "",
        "| type | n | em | f1 | recall_at_k | faithfulness | f1 change |",
        "|---|---|---|---|---|---|---|",
    ]
    for t, s in agg["by_type"].items():
        change = fmt(d["by_type"][t]["f1"], signed=True) if d and t in d["by_type"] else ""
        lines.append(
            f"| {t} | {s['n']} | {fmt(s['em'])} | {fmt(s['f1'])} | {fmt(s['recall_at_k'])} | "
            f"{fmt(s['faithfulness'])} | {change} |"
        )
    return "\n".join(lines) + "\n"


def load(c: psycopg.Connection[Any], run_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cur = c.execute(
        "select run_id, created_at, split, mode, variant, git_sha, git_dirty, config_hash, n"
        " from eval_runs where run_id = %s",
        (run_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"no run {run_id}")
    run = dict(zip([d.name for d in cur.description or []], row, strict=True))
    cur = c.execute(
        "select question_id, gold_type, em, f1, recall_at_k, mrr, sp_precision, faithfulness,"
        " relevance, completeness, cost_usd, latency_ms from eval_results where run_id = %s",
        (run_id,),
    )
    names = [d.name for d in cur.description or []]
    return run, [dict(zip(names, r, strict=True)) for r in cur.fetchall()]


def previous_run(c: psycopg.Connection[Any], run: dict[str, Any]) -> str | None:
    """The latest earlier run on the same split and mode."""
    row = c.execute(
        "select run_id from eval_runs where split = %s and mode = %s and created_at < %s"
        " order by created_at desc limit 1",
        (run["split"], run["mode"], run["created_at"]),
    ).fetchone()
    return row[0] if row else None


def report(c: psycopg.Connection[Any], run_id: str, vs_id: str | None, out_dir: Path) -> str:
    """Write docs/results/<run_id>.md and .json and return the markdown."""
    run, rows = load(c, run_id)
    agg = aggregate(rows)
    vs_id = vs_id or previous_run(c, run)
    vs = None
    if vs_id:
        vs_run, vs_rows = load(c, vs_id)
        vs = {"run": vs_run, "aggregate": aggregate(vs_rows)}
    md = render_md(run, agg, vs)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.md").write_text(md, encoding="utf-8")
    body = {
        "run": {**run, "created_at": run["created_at"].isoformat()},
        "aggregate": agg,
        "vs": vs_id,
        "diff": diff(agg, vs["aggregate"]) if vs else None,
    }
    (out_dir / f"{run_id}.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m adaptiverag.eval.report")
    p.add_argument("run_id")
    p.add_argument("--vs", metavar="RUN_ID")
    args = p.parse_args(argv)
    from adaptiverag.stores import db

    with db.conn() as c:
        print(report(c, args.run_id, args.vs, RESULTS_DIR))


if __name__ == "__main__":
    main()
