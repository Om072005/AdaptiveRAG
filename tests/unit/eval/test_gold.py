import json
from pathlib import Path

from adaptiverag.eval import gold

FIXTURE = Path(__file__).parent / "fixtures" / "hotpot_rows.json"


def rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_bridge_row_becomes_multi_hop_candidate() -> None:
    item = gold.from_hotpot(rows()[0])
    assert item.id == "hp_q_bridge"
    assert item.type == "multi_hop"
    assert item.split == "" and item.verified_by == ""
    assert item.supporting_titles == ["Acme Rockets", "Jane Roe"]
    assert item.supporting_sentences == [("Acme Rockets", 0), ("Jane Roe", 1)]
    assert item.source == "hotpotqa" and item.notes == ""


def test_comparison_row_keeps_its_type() -> None:
    assert gold.from_hotpot(rows()[1]).type == "comparison"


def test_out_of_range_supporting_sentence_is_kept_and_noted() -> None:
    item = gold.from_hotpot(rows()[2])
    assert ("John Doe", 3) in item.supporting_sentences
    assert "John Doe#3" in item.notes


def test_build_keeps_only_manifest_questions_in_manifest_order() -> None:
    items = gold.build_candidates(rows(), ["q_compare", "q_missing", "q_bridge"])
    assert [i.id for i in items] == ["hp_q_compare", "hp_q_bridge"]


def test_problems_on_candidate_and_final_item() -> None:
    item = gold.from_hotpot(rows()[0])
    assert gold.problems(item) == []
    assert gold.problems(item, final=True) == ["split ''", "not verified"]
    item.split, item.verified_by = "dev", "dhruv"
    assert gold.problems(item, final=True) == []


def test_problems_flags_bad_type_and_stray_sentence() -> None:
    item = gold.from_hotpot(rows()[0])
    item.type = "bridge"
    item.supporting_sentences.append(("Distractor", 0))
    assert gold.problems(item) == [
        "type 'bridge'",
        "supporting sentence outside supporting titles",
    ]


def test_jsonl_round_trip_matches_contract_keys(tmp_path: Path) -> None:
    items = gold.build_candidates(rows(), ["q_bridge", "q_compare"])
    path = tmp_path / "gold.jsonl"
    gold.write_jsonl(path, items)
    first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert list(first) == [
        "id",
        "question",
        "answer",
        "type",
        "split",
        "supporting_titles",
        "supporting_sentences",
        "source",
        "verified_by",
        "notes",
    ]
    assert first["supporting_sentences"] == [["Acme Rockets", 0], ["Jane Roe", 1]]
    assert gold.read_jsonl(path) == items


def test_build_cli_writes_candidates(tmp_path: Path) -> None:
    manifest = tmp_path / "full.json"
    manifest.write_text(json.dumps({"seed": 7, "question_ids": ["q_bridge", "q_compare"]}))
    out = tmp_path / "candidates.jsonl"
    gold.main(["build", "--raw", str(FIXTURE), "--manifest", str(manifest), "--out", str(out)])
    assert [i.type for i in gold.read_jsonl(out)] == ["multi_hop", "comparison"]


def test_jsonl_is_written_with_lf_line_endings(tmp_path: Path) -> None:
    path = tmp_path / "gold.jsonl"
    gold.write_jsonl(path, gold.build_candidates(rows(), ["q_bridge", "q_compare"]))
    assert b"\r\n" not in path.read_bytes()
