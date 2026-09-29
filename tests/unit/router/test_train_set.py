import json
from typing import Any

import pytest

from adaptiverag.config import ROOT
from adaptiverag.ingest.loader import SOURCE
from adaptiverag.ingest.normalize import doc_id
from adaptiverag.router import train
from adaptiverag.router.train import TRAIN_PATH, paragraphs, pick_questions
from adaptiverag.types import LLMResult


def row(
    i: int, qtype: str, question: str = "", titles: tuple[str, ...] = ("A", "B")
) -> dict[str, Any]:
    return {
        "_id": f"q{i:03d}",
        "question": question or f"question {i}?",
        "type": qtype,
        "context": [[t, [f"{t} is a thing.", f"{t} has a second sentence."]] for t in titles],
    }


ROWS = [row(i, "bridge") for i in range(10)] + [row(100 + i, "comparison") for i in range(6)]


def test_questions_follow_the_mix_and_skip_banned_texts() -> None:
    mix = {"multi_hop": 4, "comparison": 3, "single_hop": 0}
    picked = pick_questions(ROWS, mix, 7, banned={"question 1?"})
    assert [p["label"] for p in picked].count("multi_hop") == 4
    assert [p["label"] for p in picked].count("comparison") == 3
    assert all(p["question"] != "question 1?" and p["source"] == "hotpotqa-train" for p in picked)
    assert pick_questions(list(reversed(ROWS)), mix, 7, {"question 1?"}) == picked


def test_paragraphs_leave_out_corpus_titles_and_repeats() -> None:
    rows = [row(1, "bridge", titles=("Kept", "Corpus")), row(2, "bridge", titles=("Kept", "Other"))]
    docs = paragraphs(rows, corpus_doc_ids={doc_id(SOURCE, "Corpus")})
    assert sorted(d.title for d in docs) == ["Kept", "Other"]
    assert all(d.source == "hotpotqa-train" for d in docs)


def test_generated_questions_use_the_small_model(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, float]] = []

    def fake_chat(role: str, messages: list[dict[str, str]], **kw: Any) -> LLMResult:
        seen.append((role, kw["temperature"]))
        answer = json.dumps({"question": "What is Kept?", "answer": "a thing", "sentence": 0})
        return LLMResult(answer, "small", "m", 1, 1, 0.0, 1, False, False, 0, 0)

    monkeypatch.setattr(train.llm, "chat", fake_chat)
    docs = paragraphs([row(1, "bridge", titles=("Kept",))], set())
    items, rejects = train.generate_single_hop(docs, 1, 7)
    assert seen == [("small", 0.0)] and rejects == []
    assert items == [
        {
            "id": items[0]["id"],
            "question": "What is Kept?",
            "label": "single_hop",
            "source": "generated",
            "title": "Kept",
        }
    ]


def lines(path: Any) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_the_training_set_never_overlaps_the_corpus_or_the_gold_set() -> None:
    items = lines(TRAIN_PATH)
    corpus = json.loads((ROOT / "data" / "corpus" / "full.json").read_text(encoding="utf-8"))
    gold = lines(ROOT / "data" / "gold" / "dev.jsonl") + lines(
        ROOT / "data" / "gold" / "test.jsonl"
    )
    assert len({i["id"] for i in items}) == len(items)
    assert {i["label"] for i in items} == {"single_hop", "multi_hop", "comparison"}
    assert {i["source"] for i in items} == {"hotpotqa-train", "generated"}
    corpus_questions = {f"hp_{q}" for q in corpus["question_ids"]}
    assert not {i["id"] for i in items} & corpus_questions
    assert not {i["question"].strip() for i in items} & {g["question"].strip() for g in gold}
    corpus_docs = set(corpus["doc_ids"])
    generated = [i for i in items if i["source"] == "generated"]
    assert generated and all(doc_id(SOURCE, i["title"]) not in corpus_docs for i in generated)
