from pathlib import Path

import pytest

from adaptiverag.eval import gold
from adaptiverag.eval.gold import GoldItem


def pool(qtype: str, n: int) -> list[GoldItem]:
    return [
        GoldItem(f"{qtype}_{i:03d}", "q?", "a", qtype, "", ["T"], [("T", 0)], "hotpotqa")
        for i in range(n)
    ]


def candidates() -> list[GoldItem]:
    return pool("multi_hop", 70) + pool("comparison", 45) + pool("single_hop", 55)


def test_split_follows_contract_mix() -> None:
    items = gold.split_items(candidates())
    for split, mix in gold.SPLIT_MIX.items():
        for qtype, n in mix.items():
            assert sum(i.split == split and i.type == qtype for i in items) == n
    assert sum(i.split == "dev" for i in items) == 100
    assert sum(i.split == "test" for i in items) == 50


def test_split_is_stable_for_a_seed_and_input_order() -> None:
    a = gold.split_items(candidates())
    b = gold.split_items(list(reversed(candidates())))
    assert [(i.id, i.split) for i in a] == [(i.id, i.split) for i in b]
    c = gold.split_items(candidates(), seed=8)
    assert [(i.id, i.split) for i in a] != [(i.id, i.split) for i in c]


def test_split_refuses_when_a_type_is_short() -> None:
    with pytest.raises(ValueError, match="comparison: 39 candidates, need 40"):
        gold.split_items(pool("multi_hop", 60) + pool("comparison", 39) + pool("single_hop", 50))


def test_test_split_is_locked_without_allow_test(tmp_path: Path) -> None:
    gold.write_jsonl(tmp_path / "test.jsonl", pool("multi_hop", 1))
    gold.write_jsonl(tmp_path / "dev.jsonl", pool("comparison", 1))
    with pytest.raises(gold.TestSplitLocked):
        gold.load_split("test", tmp_path, allow_test=False)
    assert len(gold.load_split("test", tmp_path, allow_test=True)) == 1
    assert len(gold.load_split("dev", tmp_path, allow_test=False)) == 1


def test_split_cli_writes_files_once(tmp_path: Path) -> None:
    src = tmp_path / "candidates.jsonl"
    gold.write_jsonl(src, candidates())
    gold.main(["split", "--candidates", str(src), "--gold-dir", str(tmp_path)])
    assert len(gold.read_jsonl(tmp_path / "dev.jsonl")) == 100
    assert {i.split for i in gold.read_jsonl(tmp_path / "test.jsonl")} == {"test"}
    with pytest.raises(SystemExit, match="refusing to re-split"):
        gold.main(["split", "--candidates", str(src), "--gold-dir", str(tmp_path)])
