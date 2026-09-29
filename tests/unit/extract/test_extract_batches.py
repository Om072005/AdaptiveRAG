import json
import re
from pathlib import Path
from typing import Any

import pytest

from adaptiverag.ingest import extract
from adaptiverag.ingest.extract import extract_batches, extract_triples, summarize
from adaptiverag.types import Chunk, LLMResult

TEXTS = [
    "Tim Burton directed Ed Wood.",
    "Johnny Depp starred in Ed Wood.",
    "Ed Wood was released in 1994.",
    "Scott Derrickson lives in Los Angeles.",
    "Doctor Strange was directed by Scott Derrickson.",
]


def corpus() -> tuple[list[Chunk], dict[str, str]]:
    doc = " ".join(TEXTS)
    chunks, start = [], 0
    for i, text in enumerate(TEXTS):
        chunks.append(
            Chunk(f"d1:sentence:{i}", "d1", "sentence", i, start, start + len(text), text, 5)
        )
        start += len(text) + 1
    return chunks, {"d1": doc}


def fact(chunk: int, s: str, o: str, conf: float = 0.9, **kw: Any) -> dict[str, Any]:
    item = {
        "chunk": chunk,
        "subject": s,
        "subject_type": "PERSON",
        "predicate": "related_to",
        "object": o,
        "object_type": "WORK",
        "evidence": "",
        "confidence": conf,
    }
    return item | kw


class FakeGateway:
    def __init__(self, answers: list[str], cached: bool = False) -> None:
        self.answers, self.cached, self.seen = answers, cached, []

    def __call__(self, role: str, messages: list[dict[str, str]], **kw: Any) -> LLMResult:
        self.seen.append({"role": role, "messages": messages, **kw})
        text = self.answers[len(self.seen) - 1]
        return LLMResult(text, "extract", "m", 100, 50, 0.001, 10, self.cached, False, 0, 0)


def test_four_chunks_per_call_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGateway(['{"triples": []}'] * 2)
    monkeypatch.setattr(extract.llm, "chat", fake)
    chunks, docs = corpus()
    extract_batches(chunks, docs)
    assert [call["role"] for call in fake.seen] == ["extract", "extract"]
    assert all(c["json_mode"] and c["temperature"] == 0.0 for c in fake.seen)
    assert fake.seen[0]["max_tokens"] == 4096
    first, second = (c["messages"][1]["content"] for c in fake.seen)
    assert "[4] Scott Derrickson lives" in first and "[5]" not in first
    assert second == f"Passages:\n\n[1] {TEXTS[4]}"


def test_triples_are_screened_with_a_reason_each(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = [
        json.dumps(
            {
                "triples": [
                    fact(1, "Tim Burton", "Ed Wood", evidence="Tim Burton directed Ed Wood"),
                    fact(2, "Johnny Depp", "Ed Wood", conf=0.3),
                    fact(3, "Christopher Nolan", "Ed Wood"),
                    fact(4, "Scott Derrickson", "Los Angeles", subject_type="MOVIE"),
                ]
            }
        ),
        "the model wrote prose",
    ]
    monkeypatch.setattr(extract.llm, "chat", FakeGateway(answers))
    chunks, docs = corpus()
    kept, rejects, calls = extract_batches(chunks, docs)
    assert [(t.subject, t.chunk_id, t.evidence_start, t.evidence_end) for t in kept] == [
        ("Tim Burton", "d1:sentence:0", 0, 27)
    ]
    assert [(r["chunk_id"], r["reason"]) for r in rejects] == [
        ("d1:sentence:3", "bad_json"),
        ("d1:sentence:1", "low_confidence"),
        ("d1:sentence:2", "subject_not_in_source"),
        (None, "bad_json"),
    ]
    assert rejects[1]["raw"]["subject"] == "Johnny Depp" and rejects[1]["raw"]["confidence"] == 0.3

    summary = summarize(chunks, kept, rejects, calls)
    assert summary["triples_returned"] == 4 and summary["kept"] == 1 and summary["rejected"] == 3
    assert summary["reject_rate"] == 0.75
    assert summary["bad_responses"] == 1
    assert summary["rejects_by_reason"] == {
        "bad_json": 2,
        "low_confidence": 1,
        "subject_not_in_source": 1,
    }
    assert summary["calls"] == 2 and summary["cost_usd_this_run"] == 0.002
    assert summary["evidence_not_found"] == 0 and summary["chunks_with_triples"] == 1


def test_a_cached_rerun_costs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extract.llm, "chat", FakeGateway(['{"triples": []}'] * 2, cached=True))
    chunks, docs = corpus()
    summary = summarize(chunks, *extract_batches(chunks, docs))
    assert summary["calls_cached"] == 2 and summary["cost_usd_this_run"] == 0
    assert summary["cost_usd_list_price"] == 0.002  # reports keep the list price of the original


def test_a_chunk_that_does_not_match_its_document_stops_the_run() -> None:
    chunks, docs = corpus()
    with pytest.raises(ValueError, match="d1:sentence:0"):
        extract_triples(chunks, {"d1": "x" + docs["d1"]})


def test_evidence_not_found_is_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    answer = json.dumps({"triples": [fact(1, "Tim Burton", "Ed Wood", evidence="nowhere")]})
    monkeypatch.setattr(extract.llm, "chat", FakeGateway([answer, '{"triples": []}']))
    chunks, docs = corpus()
    summary = summarize(chunks, *extract_batches(chunks, docs))
    assert summary["evidence_not_found"] == 1


def test_every_reason_extraction_stores_is_allowed_by_the_latest_migration() -> None:
    migrations = sorted((Path(__file__).resolve().parents[3] / "db" / "migrations").glob("*.sql"))
    checks = [
        re.findall(r"reason in \(([^)]*)\)", m.read_text(encoding="utf-8")) for m in migrations
    ]
    latest = [c for found in checks for c in found][-1]
    allowed = {r.strip(" '") for r in latest.split(",")}
    produced = {"bad_json", "low_confidence", "empty", "self_loop"}
    assert produced | {"subject_not_in_source", "object_not_in_source"} <= allowed
