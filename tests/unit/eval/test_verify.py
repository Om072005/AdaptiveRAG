from pathlib import Path

from adaptiverag.eval import gold, verify
from adaptiverag.eval.gold import GoldItem


def item(n: int, split: str) -> GoldItem:
    return GoldItem(f"hp_{n}", f"q{n}?", "a", "multi_hop", split, ["T"], [("T", 0)], "hotpotqa")


def write(tmp_path: Path) -> None:
    gold.write_jsonl(tmp_path / "dev.jsonl", [item(1, "dev"), item(2, "dev")])
    gold.write_jsonl(tmp_path / "test.jsonl", [item(3, "test")])


def no_db(items: list[GoldItem]) -> verify.Sentences:
    return {("T", 0): "The supporting sentence."}


def test_numbering_is_dev_then_test(tmp_path: Path) -> None:
    write(tmp_path)
    assert [(n, i.id) for n, i in verify.numbered(tmp_path)] == [
        (1, "hp_1"),
        (2, "hp_2"),
        (3, "hp_3"),
    ]


def test_render_shows_sentences_and_missing_ones() -> None:
    text = verify.render(7, item(1, "dev"), {("T", 0): "The supporting sentence."})
    assert "#7 hp_1 [multi_hop, dev]" in text and "T #0: The supporting sentence." in text
    assert "not found" in verify.render(7, item(1, "dev"), {})


def test_apply_accepts_or_flags_with_a_note() -> None:
    it = item(1, "dev")
    verify.apply(it, "y", "dhruv")
    assert it.verified_by == "dhruv"
    verify.apply(it, "n", "om", "answer is too long")
    assert it.verified_by == "" and it.notes == "om: answer is too long"


def test_run_walks_only_the_range_and_saves(tmp_path: Path) -> None:
    write(tmp_path)
    answers = iter(["y", "n", "wrong type"])
    counts = verify.run(tmp_path, 2, 3, "dhruv", ask=lambda _: next(answers), sentences=no_db)
    assert counts == {"y": 1, "n": 1, "s": 0}
    items = dict((i.id, i) for _, i in verify.numbered(tmp_path))
    assert items["hp_1"].verified_by == ""
    assert items["hp_2"].verified_by == "dhruv"
    assert items["hp_3"].notes == "dhruv: wrong type" and items["hp_3"].split == "test"


def test_quit_stops_and_keeps_earlier_answers(tmp_path: Path) -> None:
    write(tmp_path)
    answers = iter(["maybe", "y", "q"])
    counts = verify.run(tmp_path, 1, 3, "om", ask=lambda _: next(answers), sentences=no_db)
    assert counts == {"y": 1, "n": 0, "s": 0}
    assert verify.status(tmp_path)["unverified"] == [2, 3]


def test_status_lists_unverified_and_problems(tmp_path: Path) -> None:
    write(tmp_path)
    s = verify.status(tmp_path)
    assert s["total"] == 3 and s["unverified"] == [1, 2, 3]
    assert s["problems"][1] == ["not verified"]
