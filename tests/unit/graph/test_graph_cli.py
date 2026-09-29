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
    out = capsys.readouterr().out.split("\n", 1)[1]
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
