import json
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
    monkeypatch.setattr(graph_cli, "extract_batches", lambda c, d: ([TRIPLE], [reject], []))
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
