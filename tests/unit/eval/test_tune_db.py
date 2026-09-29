"""tune against real Postgres, on temp tables that vanish on close."""

import contextlib

import psycopg
import pytest

from adaptiverag.config import settings
from adaptiverag.eval import tune

pytestmark = pytest.mark.network


def test_tune_reads_four_runs_and_prints_a_diff(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    url = settings().database_url_direct
    if not url:
        pytest.skip("DATABASE_URL_DIRECT not set")
    with psycopg.connect(url) as c:
        for t in ("eval_runs", "eval_results", "traces"):
            c.execute(f"create temp table {t} (like public.{t} including defaults)")
        n = 0
        # q1 single hop, sure; q2 multi hop at 0.5 confidence and better on graph
        for mode, f1s in [
            ("auto", (1, 0)),
            ("vector", (1, 0)),
            ("graph", (0, 1)),
            ("hybrid", (0.5, 0.25)),
        ]:
            c.execute(
                "insert into eval_runs (run_id, split, mode, variant, git_sha, git_dirty,"
                " config_hash, n) values (%s, 'dev', %s, 'v', 'a', false, 'h', 2)",
                (f"r-{mode}", mode),
            )
            for qid, label, conf, f1 in [
                ("q1", "single_hop", 0.9, f1s[0]),
                ("q2", "multi_hop", 0.5, f1s[1]),
            ]:
                n += 1
                tid = f"00000000-0000-4000-8000-{n:012d}"
                c.execute(
                    "insert into traces (trace_id, source, question, mode, route_taken,"
                    " classifier_label, classifier_confidence, top_score, path_found)"
                    " values (%s, 'eval', 'q', %s, 'vector', %s, %s, 0.9, true)",
                    (
                        tid,
                        mode,
                        label if mode == "auto" else None,
                        conf if mode == "auto" else None,
                    ),
                )
                c.execute(
                    "insert into eval_results (run_id, question_id, trace_id, gold_type,"
                    " route_taken, em, f1, recall_at_k, mrr, cost_usd, latency_ms)"
                    " values (%s, %s, %s, %s, 'vector', 0, %s, 0, 0, 0.001, 1)",
                    (f"r-{mode}", qid, tid, label, f1),
                )
        monkeypatch.setattr("adaptiverag.stores.db.conn", lambda: contextlib.nullcontext(c))
        tune.main(["--split", "dev"])
    out = capsys.readouterr().out
    assert "runs: auto r-auto, vector r-vector, graph r-graph, hybrid r-hybrid" in out
    assert "2 questions" in out
    assert "[classifier] min_confidence = 0.6 -> " in out
