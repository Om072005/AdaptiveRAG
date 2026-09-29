"""bake and replay export against real Postgres, on temp tables that vanish on close."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest

from adaptiverag.config import models, settings
from adaptiverag.eval import bake, replays
from adaptiverag.eval.gold import GoldItem

pytestmark = pytest.mark.network
TYPES = ["single_hop"] * 4 + ["multi_hop"] * 4 + ["comparison"] * 4
ITEMS = [
    GoldItem(f"q{i:02d}", f"question {i}?", "a", t, "dev", ["T"], [("T", 0)], "hotpotqa")
    for i, t in enumerate(TYPES)
]


@pytest.fixture
def c() -> Iterator[psycopg.Connection[Any]]:
    url = settings().database_url_direct
    if not url:
        pytest.skip("DATABASE_URL_DIRECT not set")
    conn = psycopg.connect(url)
    for t in ("eval_runs", "eval_results", "traces", "judgements", "review_queue"):
        conn.execute(f"create temp table {t} (like public.{t} including defaults)")
    n = 0
    for mode in ("auto", "vector"):
        conn.execute(
            "insert into eval_runs (run_id, split, mode, variant, git_sha, git_dirty,"
            " config_hash, n) values (%s, 'dev', %s, 'replay', 'abc', false, 'h', 12)",
            (f"r-{mode}", mode),
        )
        for i, item in enumerate(ITEMS):
            n += 1
            tid = f"00000000-0000-4000-8000-{n:012d}"
            predicted = ("single_hop" if i == 4 else item.type) if mode == "auto" else None
            conn.execute(
                "insert into traces (trace_id, source, question, mode, route_taken,"
                " classifier_confidence, model_selected)"
                " values (%s, 'eval', %s, %s, 'vector', 0.9, %s)",
                (tid, item.question, mode, models()["large"].model if i % 2 else "small-model"),
            )
            conn.execute(
                "insert into eval_results (run_id, question_id, trace_id, gold_type,"
                " predicted_type, route_taken, em, f1, recall_at_k, mrr, faithfulness,"
                " relevance, completeness, cost_usd, latency_ms)"
                " values (%s, %s, %s, %s, %s, 'vector', %s, %s, 1, 1, 1, 1, 1, 0.001, 100)",
                (
                    f"r-{mode}",
                    item.id,
                    tid,
                    item.type,
                    predicted,
                    0.0 if i == 0 else 1.0,
                    0.0 if i == 0 else 1.0,
                ),
            )
            conn.execute(
                "insert into judgements (trace_id, faithfulness, relevance, completeness,"
                " rationale, model, cost_usd) values (%s, 1, 0.5, 1, 'ok', 'j', 0.0002)",
                (tid,),
            )
    yield conn
    conn.close()


def test_bake_builds_results_from_pinned_runs(c: psycopg.Connection[Any], tmp_path: Path) -> None:
    for name, rows in [
        ("cls", [{"method": "logreg", "macro_f1": 0.5, "cost_per_query_usd": 0.0, "p50_ms": 1}]),
        (
            "hnsw",
            [
                {
                    "index": "flat",
                    "ef": None,
                    "recall_at_10": 1.0,
                    "p50_ms": 1,
                    "p95_ms": 2,
                    "build_s": 0.1,
                }
            ],
        ),
        (
            "chunk",
            [
                {
                    "strategy": "sentence",
                    "params": "96",
                    "precision": 0.5,
                    "context_retention": 0.5,
                    "retrieval_score": 0.5,
                    "verdict": "chosen",
                }
            ],
        ),
        ("graph", {"entities": 10, "relations": 20, "reject_rate": 0.1, "er_precision": 0.9}),
    ]:
        (tmp_path / f"{name}.json").write_text(json.dumps({"run_id": f"id-{name}", "rows": rows}))
    pinned = {
        "routes": ["r-vector", "r-auto"],
        "by_type": ["r-vector"],
        "quality_per_cost": ["r-vector"],
        "selector": ["r-auto"],
        "confusion": "r-auto",
        "classifier": "cls",
        "hnsw": "hnsw",
        "chunking": "chunk",
        "graph": "graph",
    }
    body = bake.bake(c, pinned, tmp_path, "| 1 | s | r | f | Open | `x` |", "sha")
    assert body["sample"] is False and set(body["runs"]) == {"r-vector", "r-auto"}
    t = body["tables"]
    assert set(t) == {
        "routes",
        "by_type",
        "quality_per_cost",
        "selector",
        "classifier",
        "confusion",
        "hnsw",
        "chunking",
        "graph",
        "failures",
    }
    assert [r["mode"] for r in t["routes"]] == ["vector", "auto"]
    assert t["selector"][0]["large_share"] == 0.5
    assert t["confusion"]["matrix"][1] == [1, 3, 0]
    assert t["hnsw"][0]["run_id"] == "id-hnsw" and t["graph"]["entities"] == 10
    assert t["failures"][0]["run_id"] == "x"
    with pytest.raises(SystemExit, match="no run for: graph"):
        bake.bake(c, pinned | {"graph": ""}, tmp_path, "", "sha")


def test_replays_export_from_stored_traces(c: psycopg.Connection[Any], tmp_path: Path) -> None:
    spec = {
        "runs": {"auto": "r-auto", "vector": "r-vector"},
        "question": [{"id": i.id, "why": f"because {i.id}"} for i in ITEMS],
    }
    fake = lambda tid: {"trace_id": tid}  # noqa: E731
    doc = replays.export(c, spec, ITEMS, tmp_path, fake)
    words = {i["question_id"]: i["outcome"] for i in doc["items"]}
    assert words["q00"] == "wrong" and words["q04"] == "misrouted" and words["q01"] == "correct"
    replay = json.loads((tmp_path / "q01.json").read_text(encoding="utf-8"))
    assert set(replay) == {
        "sample",
        "question_id",
        "question",
        "type",
        "gold_answer",
        "supporting_titles",
        "why",
        "recorded_at",
        "git_sha",
        "config_hash",
        "runs",
    }
    assert set(replay["runs"]) == {"auto", "vector"}
    assert replay["runs"]["vector"]["judgement"]["flagged"] is True
    assert set(doc["items"][0]) == {"question_id", "question", "type", "why", "modes", "outcome"}
    with pytest.raises(SystemExit, match="12 to 16"):
        replays.export(c, spec | {"question": spec["question"][:11]}, ITEMS, tmp_path, fake)
