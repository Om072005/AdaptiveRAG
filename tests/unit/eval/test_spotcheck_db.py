"""spot check against real Postgres, on temp tables that vanish on close."""

import psycopg
import pytest
from psycopg.types.json import Jsonb

from adaptiverag.config import settings
from adaptiverag.eval import spotcheck

pytestmark = pytest.mark.network


def test_score_saves_manual_scores_once_and_agreement_reads_them() -> None:
    url = settings().database_url_direct
    if not url:
        pytest.skip("DATABASE_URL_DIRECT not set")
    with psycopg.connect(url) as c:
        for t in ("traces", "eval_results", "manual_scores"):
            c.execute(f"create temp table {t} (like public.{t} including defaults)")
        for i in range(3):
            tid = f"00000000-0000-4000-8000-00000000000{i}"
            c.execute(
                "insert into traces (trace_id, source, question, mode, route_taken, detail)"
                " values (%s, 'eval', %s, 'vector', 'vector', %s)",
                (tid, f"question {i}", Jsonb({"answer": f"Answer: a{i}"})),
            )
            c.execute(
                "insert into eval_results (run_id, question_id, trace_id, gold_type, route_taken,"
                " em, f1, recall_at_k, mrr, faithfulness, relevance, completeness, cost_usd,"
                " latency_ms) values ('r', %s, %s, 'single_hop', 'vector', 0, 0, 0, 0, 1, 1, 0.25,"
                " 0, 1)",
                (f"q{i}", tid),
            )
        answers = iter(["5", "5", "2", ""] * 3)
        assert spotcheck.score(c, "r", "dhruv", 20, ask=lambda _: next(answers)) == 3
        assert spotcheck.score(c, "r", "dhruv", 20, ask=lambda _: "5") == 0
        a = spotcheck.agreement(spotcheck.load_pairs(c, "r"), 0.6)
        assert a["n"] == 3 and a["faithfulness"]["mean_abs_gap"] == 0.0
        assert a["same_flag_decision"] == 1.0
