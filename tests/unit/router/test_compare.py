import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from adaptiverag.router import train
from adaptiverag.types import Classification, QType

ITEMS = [
    {"question": "When was Ed Wood released?", "type": "single_hop"},
    {"question": "Who directed the film that starred Johnny Depp?", "type": "multi_hop"},
    {"question": "Who was born first, Tim Burton or Johnny Depp?", "type": "comparison"},
    {"question": "Which film is older, Ed Wood or Batman?", "type": "comparison"},
]


def pred(label: QType, cost: float = 0.0, ms: int = 0) -> Classification:
    return Classification(label, 0.9, {label: 0.9}, "x", cost, ms)


def test_f1_per_label_and_the_eval_reports_macro_f1() -> None:
    preds = [pred("single_hop"), pred("single_hop"), pred("comparison"), pred("multi_hop")]
    s = train.score(ITEMS, preds)
    assert s["matrix"] == [[1, 0, 0], [1, 0, 0], [0, 1, 1]]
    assert s["f1_by_label"] == {"single_hop": 2 / 3, "multi_hop": 0.0, "comparison": 2 / 3}
    assert s["macro_f1"] == pytest.approx(4 / 9)
    assert train.label_f1([[0, 0], [0, 0]]) == [0.0, 0.0]


def test_cost_is_per_query_and_latency_the_median() -> None:
    preds = [
        pred(q["type"], cost=0.001, ms=ms) for q, ms in zip(ITEMS, [1, 3, 5, 100], strict=True)
    ]
    s = train.score(ITEMS, preds)
    assert s["cost_per_query_usd"] == pytest.approx(0.001) and s["p50_ms"] == 4
    assert s["macro_f1"] == 1.0


def fake_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[tuple[Any, ...]]:
    path = tmp_path / "dev.jsonl"
    path.write_text("".join(json.dumps(q) + "\n" for q in ITEMS), encoding="utf-8")
    monkeypatch.setattr(train, "DEV_PATH", path)
    monkeypatch.setattr(train.llm, "embed", lambda texts: np.ones((len(texts), 768)))
    by_question = {q["question"]: q["type"] for q in ITEMS}
    monkeypatch.setattr(train, "classify", lambda q, v, t, m: pred(by_question[q], ms=2))
    written: list[tuple[Any, ...]] = []
    monkeypatch.setattr(train.results, "write", lambda *a: written.append(a) or tmp_path / "x.md")
    return written


def test_a_subset_of_methods_is_a_preview(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    written = fake_run(monkeypatch, tmp_path)
    train.main(["compare", "--methods", "rules"])
    assert written == []


def test_all_three_write_the_contract_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    written = fake_run(monkeypatch, tmp_path)
    train.main(["compare"])
    name, run_id, params, rows, md = written[0]
    assert name == "classifier" and run_id.endswith("-dev") and params["split"] == "dev"
    assert [r["method"] for r in rows] == ["rules", "logreg", "llm"]
    assert all(set(r) == {"method", "macro_f1", "cost_per_query_usd", "p50_ms"} for r in rows)
    assert "| rules | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.00000000 | 2 |" in md
    assert "(1 single_hop, 1 multi_hop, 2 comparison)" in md
