import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from adaptiverag.ingest import loader
from adaptiverag.ingest.normalize import doc_id, normalize

FIXTURE = Path(__file__).parent / "fixtures" / "hotpot_3q.json"


def records() -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def test_one_document_per_unique_title() -> None:
    docs, questions = loader.from_records(records(), 3)
    titles = [d.title for d in docs]
    assert len(questions) == 3
    assert len(titles) == len(set(titles)) == 7  # "Ed Wood" is in two questions
    assert set(titles) == {t for q in questions for t in q["titles"]}


def test_documents_follow_the_contract() -> None:
    docs, _ = loader.from_records(records(), 3)
    for d in docs:
        assert d.source == "hotpotqa-dev"
        assert d.doc_id == doc_id("hotpotqa-dev", d.title)
        assert normalize(d.text) == d.text
        for start, end in d.sentences:
            assert 0 <= start <= end <= len(d.text)


def test_sentence_offsets_keep_the_original_sentences() -> None:
    raw = {title: sents for r in records() for title, sents in r["context"]}
    docs, _ = loader.from_records(records(), 3)
    for d in docs:
        assert len(d.sentences) == len(raw[d.title])
        assert [d.text[s:e] for s, e in d.sentences] == [normalize(s) for s in raw[d.title]]


def test_supporting_facts_point_at_real_sentences() -> None:
    docs, questions = loader.from_records(records(), 3)
    by_title = {d.title: d for d in docs}
    for q in questions:
        for title, i in q["supporting_facts"]:
            start, end = by_title[title].sentences[i]
            assert end > start


def test_titles_stay_as_in_the_dataset() -> None:
    docs, _ = loader.from_records(records(), 3)
    assert "Café de Flore" in {d.title for d in docs}


def test_sample_is_seeded_and_a_smaller_sample_is_a_prefix() -> None:
    _, three = loader.from_records(records(), 3, seed=7)
    _, again = loader.from_records(records(), 3, seed=7)
    _, two = loader.from_records(records(), 2, seed=7)
    assert [q["id"] for q in three] == [q["id"] for q in again]
    assert [q["id"] for q in two] == [q["id"] for q in three[:2]]


def test_question_fields() -> None:
    _, questions = loader.from_records(records(), 3)
    q = next(q for q in questions if q["id"] == "fx0000000000000000000002")
    assert q["answer"] == "Tim Burton"
    assert q["type"] == "bridge"
    assert q["supporting_facts"] == [["Ed Wood (film)", 0], ["Ed Wood (film)", 1]]
    assert q["titles"] == ["Ed Wood (film)", "Ed Wood", "Plan 9 from Outer Space"]


@pytest.mark.parametrize("n", [0, 4])
def test_sample_size_out_of_range_raises(n: int) -> None:
    with pytest.raises(ValueError):
        loader.from_records(records(), n)


def test_read_raw_uses_the_local_file_without_downloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "raw.json"
    shutil.copy(FIXTURE, path)

    def no_download(url: str, path: Path) -> None:
        raise AssertionError("must not download when the file exists")

    monkeypatch.setattr(loader, "download", no_download)
    assert [r["_id"] for r in loader.read_raw(path)] == [r["_id"] for r in records()]


def test_mirror_row_converts_back_to_the_original_layout() -> None:
    for original in records():
        row = {
            "id": original["_id"],
            "question": original["question"],
            "answer": original["answer"],
            "type": original["type"],
            "level": original["level"],
            "supporting_facts": {
                "title": [t for t, _ in original["supporting_facts"]],
                "sent_id": [i for _, i in original["supporting_facts"]],
            },
            "context": {
                "title": [t for t, _ in original["context"]],
                "sentences": [s for _, s in original["context"]],
            },
        }
        assert loader.from_mirror_row(row) == original
