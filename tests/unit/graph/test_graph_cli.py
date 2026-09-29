import json
from pathlib import Path
from typing import Any

import pytest

from adaptiverag.ingest import graph_cli
from adaptiverag.types import Chunk, Triple

CHUNK = Chunk("d1:sentence:0", "d1", "sentence", 0, 0, 27, "Tim Burton directed Ed Wood.", 5)
TRIPLE = Triple("Tim Burton", "PERSON", "directed", "Ed Wood", "WORK", CHUNK.chunk_id, 0, 27, 1.0)


def refuse(*args: Any, **kwargs: Any) -> None:
    raise AssertionError("a dry run must not write or embed")


def test_dry_run_prints_counts_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reject = {"chunk_id": CHUNK.chunk_id, "raw": {}, "reason": "low_confidence"}
    monkeypatch.setattr(graph_cli, "corpus_doc_ids", lambda corpus: ["d1"])
    monkeypatch.setattr(graph_cli.store, "corpus_chunks", lambda ids, s: ([CHUNK], {"d1": ""}))
    monkeypatch.setattr(graph_cli, "extract_batches", lambda c, d, b: ([TRIPLE], [reject], []))
    monkeypatch.setattr(graph_cli, "resolve", lambda kept: ([{}, {}], [{}, {}, {}], [{}]))
    for name in ["save_rejects", "write_graph"]:
        monkeypatch.setattr(graph_cli.store, name, refuse)
    monkeypatch.setattr(graph_cli.llm, "embed", refuse)

    graph_cli.main(["--corpus", "mini", "--dry-run"])
    raw = capsys.readouterr().out
    out = raw[raw.index("{") :]  # after the database and corpus lines
    first, end = json.JSONDecoder().raw_decode(out)
    graph = json.loads(out[end:])["graph"]
    assert "stored_rejects_by_reason" not in first["extraction"]
    assert graph["would_write"] == {
        "entities": 2,
        "aliases": 3,
        "relations": 1,
        "extraction_rejects": 1,
    }
    assert graph["triples_folded_by_resolution"] == 0


def test_embed_slices_split_the_texts_and_stop_cleanly_on_the_quota(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    texts = [f"text {i}" for i in range(40)]
    monkeypatch.setattr(graph_cli, "extract_corpus", lambda corpus, limit: ([], [TRIPLE], [], []))
    monkeypatch.setattr(graph_cli, "graph_texts", lambda kept: texts)
    sent: list[list[str]] = []
    monkeypatch.setattr(graph_cli.llm, "embed", sent.append)
    for k in (1, 2, 3):
        graph_cli.main(["embed", "--corpus", "mini", "--slice", f"{k}/3"])
    assert sorted(t for batch in sent for t in batch) == sorted(texts)
    assert sum(len(b) for b in sent) == len(texts)
    assert "all" in capsys.readouterr().out

    def quota(texts: list[str]) -> None:
        raise graph_cli.RateLimited("daily quota used up")

    monkeypatch.setattr(graph_cli.llm, "embed", quota)
    with pytest.raises(SystemExit, match="rerun later"):
        graph_cli.main(["embed", "--corpus", "mini", "--slice", "1/3"])


def test_names_can_be_embedded_before_the_relations(monkeypatch: pytest.MonkeyPatch) -> None:
    names = [f"name {i}" for i in range(10)]
    relations = [f"relation {i}" for i in range(10)]
    monkeypatch.setattr(graph_cli, "extract_corpus", lambda corpus, limit: ([], [TRIPLE], [], []))
    monkeypatch.setattr(graph_cli, "graph_texts", lambda kept: sorted(names + relations))
    monkeypatch.setattr(graph_cli, "name_texts", lambda kept: ([], names))
    sent: list[list[str]] = []
    monkeypatch.setattr(graph_cli.llm, "embed", sent.append)
    for k in (1, 2):
        graph_cli.main(["embed", "--corpus", "mini", "--slice", f"{k}/2", "--part", "names"])
    assert sorted(t for batch in sent for t in batch) == names
    graph_cli.main(["embed", "--corpus", "mini", "--part", "relations"])
    assert sent[-1] == relations


def test_gold_documents_are_every_context_paragraph_or_the_generated_one() -> None:
    from adaptiverag.ingest.loader import SOURCE
    from adaptiverag.ingest.normalize import doc_id

    raw = {
        "q1": {"context": [["Ed Wood", []], ["Tim Burton", []]]},
        "q2": {"context": [["Tim Burton", []], ["Burbank", []]]},
    }
    items = [{"id": "hp_q1"}, {"id": "hp_q2"}, {"id": "sh_abcdef0123456789_2"}]
    expected = {doc_id(SOURCE, t) for t in ["Ed Wood", "Tim Burton", "Burbank"]}
    assert graph_cli.gold_doc_ids(items, raw) == sorted(expected | {"abcdef0123456789"})


def test_a_scope_change_keeps_planned_batches_and_appends_new_chunks() -> None:
    plan = [["a:0", "a:1", "b:0", "c:0"], ["d:0", "e:0", "f:0", "g:0"], ["h:0", "i:0"]]
    known = {cid for b in plan for cid in b} | {"x:0", "y:0"}
    # b left the scope and x and y joined it
    scope = ["a:0", "a:1", "c:0", "d:0", "e:0", "f:0", "g:0", "x:0", "y:0"]
    batches, new_plan = graph_cli.plan_batches(plan, scope, known, 4)
    assert batches == [plan[0], plan[1], ["x:0", "y:0"]]
    assert new_plan == [*plan, ["x:0", "y:0"]]
    # a planned batch whose chunk is gone is dropped and its scope chunks batched anew
    batches, new_plan = graph_cli.plan_batches(plan, scope, known - {"b:0"}, 4)
    assert batches == [plan[1], ["a:0", "a:1", "c:0", "x:0"], ["y:0"]]
    assert new_plan == [plan[1], plan[2], ["a:0", "a:1", "c:0", "x:0"], ["y:0"]]
    # the same plan and scope always give the same batches, so helpers hit the same cache
    assert graph_cli.plan_batches(plan, scope, known, 4) == graph_cli.plan_batches(
        plan, scope, known, 4
    )


def test_the_plan_file_keeps_other_strategies(tmp_path: Path) -> None:
    path = tmp_path / "plan.jsonl"
    assert graph_cli.read_plan("sentence", path) == []
    graph_cli.write_plan("fixed", [["a:fixed:0"]], path)
    graph_cli.write_plan("sentence", [["a:sentence:0", "a:sentence:1"]], path)
    graph_cli.write_plan("sentence", [["b:sentence:0"]], path)
    assert graph_cli.read_plan("sentence", path) == [["b:sentence:0"]]
    assert graph_cli.read_plan("fixed", path) == [["a:fixed:0"]]


def test_only_rejects_of_the_scope_are_counted() -> None:
    wanted = {"a:0"}
    assert graph_cli.in_scope({"chunk_id": "a:0", "raw": {}}, wanted)
    assert not graph_cli.in_scope({"chunk_id": "b:0", "raw": {}}, wanted)
    assert graph_cli.in_scope({"chunk_id": None, "raw": {"chunk_ids": ["b:0", "a:0"]}}, wanted)
    assert not graph_cli.in_scope({"chunk_id": None, "raw": {"chunk_ids": ["b:0"]}}, wanted)
