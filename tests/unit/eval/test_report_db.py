"""report against real Postgres, on temp tables that shadow the real ones and vanish on close."""

import json
from pathlib import Path

import psycopg
import pytest

from adaptiverag.config import settings
from adaptiverag.eval import report

pytestmark = pytest.mark.network


def test_report_finds_previous_comparable_run_and_writes_files(tmp_path: Path) -> None:
    url = settings().database_url_direct
    if not url:
        pytest.skip("DATABASE_URL_DIRECT not set")
    with psycopg.connect(url) as c:
        for t in ("eval_runs", "eval_results"):
            c.execute(f"create temp table {t} (like public.{t} including defaults)")
        for run_id, when, mode, f1 in [
            ("r-old", "2026-10-01", "vector", 0.4),
            ("r-graph", "2026-10-02", "graph", 0.9),
            ("r-new", "2026-10-03", "vector", 0.6),
        ]:
            c.execute(
                "insert into eval_runs (run_id, created_at, split, mode, variant, git_sha,"
                " git_dirty, config_hash, n) values (%s, %s, 'dev', %s, 'b', 'abc', false, 'h', 1)",
                (run_id, when, mode),
            )
            c.execute(
                "insert into eval_results (run_id, question_id, gold_type, route_taken, em, f1,"
                " recall_at_k, mrr, cost_usd, latency_ms) values"
                " (%s, 'q1', 'multi_hop', %s, 0, %s, 1, 1, 0.001, 100)",
                (run_id, mode, f1),
            )
        md = report.report(c, "r-new", None, tmp_path)
        assert "Compared with: `r-old`" in md
        body = json.loads((tmp_path / "r-new.json").read_text(encoding="utf-8"))
        assert body["vs"] == "r-old"
        assert body["diff"]["overall"]["f1"] == pytest.approx(0.2)
        assert (tmp_path / "r-new.md").exists()
        assert "Compared with: `r-graph`" in report.report(c, "r-new", "r-graph", tmp_path)
