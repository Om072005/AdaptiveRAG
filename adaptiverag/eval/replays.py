"""python -m adaptiverag.eval.report replays: docs/results/replays.toml -> web/public/data/replays/

Every replay is a stored trace of a real run, read back through serialize.response_from_trace.
Nothing in a replay file is written by hand.
"""

import json
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

import psycopg

from adaptiverag.config import ROOT, router_cfg
from adaptiverag.eval import gold
from adaptiverag.eval.gold import GoldItem
from adaptiverag.eval.judge import SCORES

REPLAYS_TOML = ROOT / "docs" / "results" / "replays.toml"
OUT_DIR = ROOT / "web" / "public" / "data" / "replays"
MODES = ("auto", "vector", "graph", "hybrid")
MAX_BYTES = 150 * 1024


def outcome(em: float, f1: float, gold_type: str, predicted_type: str | None) -> str:
    """The word the page shows next to a question."""
    if predicted_type is not None and predicted_type != gold_type:
        return "misrouted"
    if em == 1.0:
        return "correct"
    return "partial" if f1 > 0 else "wrong"


def check_set(items: list[tuple[str, str]]) -> list[str]:
    """Contract rules for the replay set, from (type, outcome) per question."""
    found = []
    if not 12 <= len(items) <= 16:
        found.append(f"{len(items)} questions, the page needs 12 to 16")
    per_type = Counter(t for t, _ in items)
    found += [
        f"{t}: {per_type[t]} questions, at least 4 needed"
        for t in sorted(gold.QTYPES)
        if per_type[t] < 4
    ]
    if sum(o in ("wrong", "misrouted") for _, o in items) < 2:
        found.append("fewer than 2 questions that went wrong")
    return found


def judgement(
    row: tuple[Any, ...] | None, queued: bool, flag_below: float
) -> dict[str, Any] | None:
    """Judgement shape of contract section 6 from a judgements row."""
    if row is None:
        return None
    scores = dict(zip(SCORES, map(float, row[:3]), strict=True))
    return {
        **scores,
        "rationale": row[3],
        "cost_usd": float(row[4]),
        "flagged": any(v < flag_below for v in scores.values()),
        "queued": queued,
    }


def build(
    c: psycopg.Connection[Any],
    item: GoldItem,
    why: str,
    runs: dict[str, str],
    response_from_trace: Any,
    flag_below: float,
) -> tuple[dict[str, Any], str]:
    """One Replay document and its outcome word."""
    out: dict[str, Any] = {}
    first: tuple[Any, ...] | None = None
    word = ""
    for mode in MODES:
        run_id = runs.get(mode)
        if not run_id:
            continue
        row = c.execute(
            "select r.trace_id, r.em, r.f1, r.recall_at_k, r.predicted_type, e.created_at,"
            " e.git_sha, e.config_hash from eval_results r join eval_runs e on e.run_id = r.run_id"
            " where r.run_id = %s and r.question_id = %s",
            (run_id, item.id),
        ).fetchone()
        if row is None:
            raise SystemExit(f"{item.id} is not in run {run_id}")
        trace_id = str(row[0])
        j = c.execute(
            "select faithfulness, relevance, completeness, rationale, cost_usd from judgements"
            " where trace_id = %s",
            (trace_id,),
        ).fetchone()
        queued = c.execute("select 1 from review_queue where trace_id = %s", (trace_id,)).fetchone()
        out[mode] = {
            "run_id": run_id,
            "response": response_from_trace(trace_id),
            "metrics": {"em": float(row[1]), "f1": float(row[2]), "recall_at_k": float(row[3])},
            "judgement": judgement(j, queued is not None, flag_below),
        }
        if first is None or mode == "auto":
            first = row
            word = outcome(float(row[1]), float(row[2]), item.type, row[4])
    if first is None:
        raise SystemExit(f"{item.id} has no run listed")
    replay = {
        "sample": False,
        "question_id": item.id,
        "question": item.question,
        "type": item.type,
        "gold_answer": item.answer,
        "supporting_titles": item.supporting_titles,
        "why": why,
        "recorded_at": first[5].isoformat(),
        "git_sha": first[6],
        "config_hash": first[7],
        "runs": out,
    }
    return replay, word


def export(
    c: psycopg.Connection[Any],
    spec: dict[str, Any],
    dev: list[GoldItem],
    out_dir: Path,
    response_from_trace: Any,
) -> dict[str, Any]:
    """Write one file per question and the index; refuses a set that breaks the contract rules."""
    by_id = {i.id: i for i in dev}
    runs = {m: r for m, r in spec.get("runs", {}).items() if r}
    flag_below = router_cfg()["judge"]["flag_below"]
    files, index = {}, []
    for q in spec.get("question", []):
        if q["id"] not in by_id:
            raise SystemExit(f"{q['id']} is not a dev gold question (replays come from dev only)")
        item = by_id[q["id"]]
        replay, word = build(c, item, q["why"], runs, response_from_trace, flag_below)
        body = json.dumps(replay, indent=1, ensure_ascii=False) + "\n"
        if len(body.encode()) > MAX_BYTES:
            raise SystemExit(f"{item.id} replay is {len(body.encode())} bytes, over {MAX_BYTES}")
        files[item.id] = body
        index.append(
            {
                "question_id": item.id,
                "question": item.question,
                "type": item.type,
                "why": q["why"],
                "modes": list(replay["runs"]),
                "outcome": word,
            }
        )
    problems = check_set([(i["type"], i["outcome"]) for i in index])
    if problems:
        raise SystemExit("replay set breaks the contract rules: " + "; ".join(problems))
    out_dir.mkdir(parents=True, exist_ok=True)
    for qid, body in files.items():
        (out_dir / f"{qid}.json").write_text(body, encoding="utf-8")
    doc = {"sample": False, "items": index}
    (out_dir / "index.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return doc


def main() -> None:
    from adaptiverag.serialize import response_from_trace
    from adaptiverag.stores import db

    spec = tomllib.loads(REPLAYS_TOML.read_text(encoding="utf-8"))
    with db.conn() as c:
        doc = export(c, spec, gold.load_split("dev"), OUT_DIR, response_from_trace)
    print(f"wrote {len(doc['items'])} replays to {OUT_DIR}")
