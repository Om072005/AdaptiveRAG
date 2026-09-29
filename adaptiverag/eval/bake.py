"""python -m adaptiverag.eval.report bake: docs/results/pinned.toml -> web/public/data/results.json

Only runs listed in pinned.toml reach the page. Eval tables are computed from the pinned runs in
the database; the other members' tables come from their docs/results/<name>.json ("rows").
"""

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

from adaptiverag.config import ROOT, models, router_cfg
from adaptiverag.eval import report

PINNED = ROOT / "docs" / "results" / "pinned.toml"
FAILURE_LOG = ROOT / "docs" / "failure-log.md"
RESULTS_JSON = ROOT / "web" / "public" / "data" / "results.json"
EVAL_LISTS = ("routes", "by_type", "quality_per_cost", "selector")
FILE_TABLES = ("classifier", "hnsw", "chunking", "graph")
REQUIRED = (*EVAL_LISTS, "confusion", *FILE_TABLES)


def parse_failures(markdown: str) -> list[dict[str, Any]]:
    """Rows of the failure log table: #, Symptom, Root cause, Fix, Status, Run."""
    rows = []
    for line in markdown.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0].isdigit():
            run = cells[5].strip("`").strip()
            rows.append(
                {
                    "n": int(cells[0]),
                    "symptom": cells[1],
                    "root_cause": cells[2],
                    "fix": cells[3],
                    "status": cells[4],
                    "run_id": run or None,
                }
            )
    return rows


def eligible(faithfulness: float | None, flag_below: float) -> bool:
    """A variant under the faithfulness floor is not a win at any cost; unjudged is not eligible."""
    return faithfulness is not None and faithfulness >= flag_below


def eval_rows(
    run: dict[str, Any], agg: dict[str, Any], large_share: float, flag_below: float
) -> dict[str, list[dict[str, Any]]]:
    """The four eval tables' rows for one pinned run."""
    rid, cost = run["run_id"], agg["cost_per_query_usd"]
    return {
        "routes": [
            {
                "run_id": rid,
                "mode": run["mode"],
                "em": agg["em"],
                "f1": agg["f1"],
                "recall_at_k": agg["recall_at_k"],
                "faithfulness": agg["faithfulness"],
                "cost_per_query_usd": cost,
                "p50_ms": agg["p50_ms"],
                "p95_ms": agg["p95_ms"],
            }
        ],
        "by_type": [
            {
                "run_id": rid,
                "mode": run["mode"],
                "type": t,
                "f1": s["f1"],
                "recall_at_k": s["recall_at_k"],
            }
            for t, s in agg["by_type"].items()
        ],
        "quality_per_cost": [
            {
                "run_id": rid,
                "variant": run["variant"],
                "f1": agg["f1"],
                "faithfulness": agg["faithfulness"],
                "cost_per_query_usd": cost,
                "eligible": eligible(agg["faithfulness"], flag_below),
            }
        ],
        "selector": [
            {
                "run_id": rid,
                "variant": run["variant"],
                "f1": agg["f1"],
                "cost_per_query_usd": cost,
                "large_share": large_share,
            }
        ],
    }


def file_rows(name: str, results_dir: Path) -> tuple[str, Any]:
    """(run_id, rows) from another member's result file."""
    body = json.loads((results_dir / f"{name}.json").read_text(encoding="utf-8"))
    return body["run_id"], body["rows"]


def large_share(c: psycopg.Connection[Any], run_id: str) -> float:
    large = models()["large"].model
    row = c.execute(
        "select avg((t.model_selected = %s)::int) from eval_results r"
        " join traces t on t.trace_id = r.trace_id where r.run_id = %s",
        (large, run_id),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else 0.0


def bake(
    c: psycopg.Connection[Any],
    pinned: dict[str, Any],
    results_dir: Path,
    failures_md: str,
    git_sha: str,
) -> dict[str, Any]:
    """The Results document of contract 6b, built from pinned runs only."""
    missing = [k for k in REQUIRED if not pinned.get(k)]
    if missing:
        raise SystemExit(f"pinned.toml has no run for: {', '.join(missing)}")
    flag_below = router_cfg()["judge"]["flag_below"]
    tables: dict[str, Any] = {k: [] for k in EVAL_LISTS}
    runs: dict[str, Any] = {}
    loaded: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for key in (*EVAL_LISTS, "confusion"):
        ids = pinned[key] if isinstance(pinned[key], list) else [pinned[key]]
        for rid in ids:
            if rid not in loaded:
                run, rows = report.load(c, rid)
                if run["split"] not in ("dev", "test"):
                    raise SystemExit(
                        f"{rid} is a {run['split']} run; only dev and test runs are pinned"
                    )
                if run["git_dirty"]:
                    raise SystemExit(f"{rid} ran on a dirty tree; pinned runs come from --pin runs")
                loaded[rid] = (run, report.aggregate(rows))
                runs[rid] = {
                    "split": run["split"],
                    "mode": run["mode"],
                    "variant": run["variant"],
                    "n": run["n"],
                    "created_at": run["created_at"].isoformat(),
                    "config_hash": run["config_hash"],
                }
            if key in EVAL_LISTS:
                run, agg = loaded[rid]
                tables[key] += eval_rows(run, agg, large_share(c, rid), flag_below)[key]
    run, agg = loaded[pinned["confusion"]]
    if not agg["confusion"]:
        raise SystemExit(f"{pinned['confusion']} has no classifier predictions (pin an auto run)")
    tables["confusion"] = {"run_id": run["run_id"], **agg["confusion"]}
    for key in FILE_TABLES:
        rid, rows = file_rows(pinned[key], results_dir)
        if key == "graph":
            tables[key] = {"run_id": rid, **(rows if isinstance(rows, dict) else rows[0])}
        else:
            tables[key] = [{"run_id": rid, **r} for r in rows]
    tables["failures"] = parse_failures(failures_md)
    return {
        "sample": False,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": git_sha,
        "runs": runs,
        "tables": tables,
    }


def main() -> None:
    from adaptiverag.eval.run import git_state
    from adaptiverag.stores import db

    pinned = tomllib.loads(PINNED.read_text(encoding="utf-8"))
    with db.conn() as c:
        body = bake(
            c, pinned, PINNED.parent, FAILURE_LOG.read_text(encoding="utf-8"), git_state()[0]
        )
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {RESULTS_JSON} from {len(body['runs'])} pinned eval runs")
