"""python -m bench.econ <run_id> [<run_id> ...]

The economics report of stored eval runs: cost and latency per query type and per route, quality
per unit cost with the faithfulness floor, and the model selector table. List price cost and
original latency from the traces. Writes docs/results/econ-<report_id>.md and .json.
"""

import argparse
from typing import Any

from adaptiverag.telemetry.aggregate import economics
from bench import results


def usd(x: float | None) -> str:
    return "" if x is None else f"{x:.6f}"


def num(x: float | None, digits: int = 3) -> str:
    return "" if x is None else f"{x:.{digits}f}"


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
        *("| " + " | ".join(r) + " |" for r in rows),
        "",
    ]


def markdown(report_id: str, e: dict[str, Any]) -> str:
    runs = e["runs"]
    lines = [
        f"# Economics ({report_id})",
        "",
        "{header}"
        "List price cost and original call latency from the traces, so cache hits never look "
        "cheaper or faster. Cost per query is the cost of answering; the judge's cost is its own "
        "column. A run is eligible only if it was judged and its mean faithfulness is at least "
        f"{e['faithfulness_floor']} (judge.flag_below).",
        "",
        "## Runs",
        "",
    ]
    lines += table(
        [
            "Run",
            "Mode",
            "Variant",
            "n",
            "Cost / query USD",
            "Judge / query USD",
            "p50 ms",
            "p95 ms",
            "F1",
            "Faithfulness",
        ],
        [
            [
                f"`{rid}`",
                r["mode"],
                r["variant"],
                str(r["n"]),
                usd(r["cost_per_query_usd"]),
                usd(r["judge_cost_per_query_usd"]),
                num(r["p50_ms"], 0),
                num(r["p95_ms"], 0),
                num(r["f1"]),
                num(r["faithfulness"]),
            ]
            for rid, r in runs.items()
        ],
    )
    for title, key in (("Cost per query type", "gold_type"), ("Cost per route", "route_taken")):
        lines += [f"## {title}", ""]
        lines += table(
            [
                "Run",
                key.replace("_", " "),
                "n",
                "Cost / query USD",
                "p50 ms",
                "p95 ms",
                "F1",
                "Faithfulness",
            ],
            [
                [
                    f"`{g['run_id']}`",
                    str(g[key]),
                    str(g["n"]),
                    usd(g["cost_per_query_usd"]),
                    num(g["p50_ms"], 0),
                    num(g["p95_ms"], 0),
                    num(g["f1"]),
                    num(g["faithfulness"]),
                ]
                for g in e["by_type" if key == "gold_type" else "by_route"]
            ],
        )
    lines += ["## Quality per unit cost", ""]
    lines += table(
        ["Run", "Variant", "F1", "Faithfulness", "Cost / query USD", "Eligible"],
        [
            [
                f"`{q['run_id']}`",
                q["variant"],
                num(q["f1"]),
                num(q["faithfulness"]),
                usd(q["cost_per_query_usd"]),
                "yes" if q["eligible"] else f"no ({q['why_not']})",
            ]
            for q in e["quality_per_cost"]
        ],
    )
    lines += ["## Model selector", ""]
    lines += table(
        ["Run", "Variant", "F1", "Cost / query USD", "Large model share"],
        [
            [
                f"`{s['run_id']}`",
                s["variant"],
                num(s["f1"]),
                usd(s["cost_per_query_usd"]),
                num(s["large_share"]),
            ]
            for s in e["selector"]
        ],
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bench.econ")
    parser.add_argument("run_ids", nargs="+")
    args = parser.parse_args()
    e = economics(args.run_ids)
    unknown = [r for r in args.run_ids if r not in e["runs"]]
    if unknown:
        raise SystemExit(f"no eval results stored for: {', '.join(unknown)}")
    label = "-".join(sorted({r["split"] for r in e["runs"].values()}))
    report_id = results.new_run_id(label)
    rows = [
        {"table": name, **r}
        for name in ("quality_per_cost", "selector", "by_type", "by_route")
        for r in e[name]
    ]
    params = {
        "run_ids": args.run_ids,
        "runs": e["runs"],
        "faithfulness_floor": e["faithfulness_floor"],
    }
    print(results.write("econ", report_id, params, rows, markdown(report_id, e)))


if __name__ == "__main__":
    main()
