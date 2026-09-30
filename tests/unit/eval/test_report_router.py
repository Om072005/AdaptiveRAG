from typing import Any

import pytest

from adaptiverag.eval import report


def row(qid: str, gold: str, predicted: str | None, conf: float | None) -> dict[str, Any]:
    return {
        "question_id": qid,
        "gold_type": gold,
        "predicted_type": predicted,
        "classifier_confidence": conf,
        "route_taken": "vector",
    }


ROWS = [
    row("a", "single_hop", "single_hop", 0.9),
    row("b", "multi_hop", "multi_hop", 0.7),
    row("c", "multi_hop", "single_hop", 0.95),
    row("d", "comparison", "multi_hop", 0.5),
    row("e", "comparison", "comparison", 0.8),
]


def test_confusion_rows_are_gold_and_columns_predicted() -> None:
    conf = report.confusion(ROWS)
    assert conf == {
        "labels": ["single_hop", "multi_hop", "comparison"],
        "matrix": [[1, 0, 0], [1, 1, 0], [0, 1, 1]],
    }


def test_forced_route_run_has_no_confusion() -> None:
    assert report.confusion([row("a", "single_hop", None, None)]) is None


def test_macro_f1_is_the_mean_of_per_label_f1() -> None:
    # single: 2*1/(2+1), multi: 2*1/(2+2), comparison: 2*1/(1+2)
    assert report.macro_f1([[1, 0, 0], [1, 1, 0], [0, 1, 1]]) == pytest.approx(
        (2 / 3 + 0.5 + 2 / 3) / 3
    )
    assert report.macro_f1([[0, 0], [0, 0]]) == 0.0


def test_misroutes_most_confident_first_and_marked() -> None:
    wrong = report.misroutes(ROWS)
    assert [(w["question_id"], w["confident"]) for w in wrong] == [("c", True), ("d", False)]


def test_router_section_in_the_report() -> None:
    run = {
        "run_id": "r",
        "split": "dev",
        "mode": "auto",
        "variant": "v",
        "git_sha": "abc",
        "git_dirty": False,
        "config_hash": "h",
        "n": 5,
    }
    rows = [
        r
        | {
            "em": 0.0,
            "f1": 0.0,
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "sp_precision": None,
            "faithfulness": None,
            "relevance": None,
            "completeness": None,
            "cost_usd": 0,
            "latency_ms": 1,
        }
        for r in ROWS
    ]
    md = report.render_md(run, report.aggregate(rows), None)
    assert "| multi_hop | 1 | 1 | 0 |" in md
    assert "### Confident misroutes (confidence at least 0.8): 1" in md
    assert "- `c` multi_hop predicted single_hop at 0.950, routed vector" in md
    assert "### Other misroutes: 1" in md


def test_routes_and_fallbacks_are_counted() -> None:
    rows = [
        row("a", "single_hop", "single_hop", 0.9) | {"route_taken": "vector", "fallbacks": []},
        row("b", "single_hop", "single_hop", 0.9)
        | {"route_taken": "hybrid", "fallbacks": ["vector_low_score->hybrid"]},
        row("c", "multi_hop", "multi_hop", 0.9) | {"route_taken": "hybrid", "fallbacks": None},
    ]
    assert report.routes_and_fallbacks(rows) == {
        "routes": {"vector": 1, "graph": 0, "hybrid": 2},
        "fallbacks": 1,
        "fallbacks_by_kind": {"vector_low_score": 1},
    }


def test_router_section_names_the_fallback_count() -> None:
    lines = report.render_router(
        report.confusion(ROWS) or {},
        [],
        {
            "routes": {"vector": 3, "graph": 0, "hybrid": 2},
            "fallbacks": 1,
            "fallbacks_by_kind": {"graph_no_path": 1},
        },
    )
    md = "\n".join(lines)
    assert "Routes taken: vector 3, graph 0, hybrid 2" in md
    assert "Fallbacks: 1 of 5 questions (graph_no_path 1)" in md
