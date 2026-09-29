import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from adaptiverag import llm
from adaptiverag.config import ingest_cfg
from adaptiverag.ingest import loader, pipeline
from adaptiverag.types import Document

FIXTURE = Path(__file__).parent / "fixtures" / "hotpot_3q.json"


def fixture_sample(n: int, seed: int = 7) -> tuple[list[Document], list[dict[str, Any]]]:
    return loader.from_records(json.loads(FIXTURE.read_text(encoding="utf-8")), min(n, 3), seed)


def test_parse_strategies() -> None:
    assert pipeline.parse_strategies("fixed,sentence") == ["fixed", "sentence"]
    assert pipeline.parse_strategies(" sentence , fixed,sentence") == ["sentence", "fixed"]
    for bad in ["", "fixed,tokens", ","]:
        with pytest.raises(argparse.ArgumentTypeError):
            pipeline.parse_strategies(bad)


def test_default_strategies_are_all_three(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(pipeline, "run", lambda name, strategies: seen.append((name, strategies)))
    pipeline.main(["--corpus", "mini"])
    assert seen == [("mini", ["fixed", "sentence", "semantic"])]


def test_chunk_docs_uses_the_configured_sizes() -> None:
    docs, _ = fixture_sample(3)
    cfg = ingest_cfg()["chunk"]
    fixed = pipeline.chunk_docs(docs, "fixed", cfg)
    sentence = pipeline.chunk_docs(docs, "sentence", cfg)
    assert {c.doc_id for c in fixed} == {c.doc_id for c in sentence} == {d.doc_id for d in docs}
    assert all(c.strategy == "fixed" and c.n_words <= cfg["fixed"]["n_words"] for c in fixed)
    assert all(c.strategy == "sentence" for c in sentence)
    text = {d.doc_id: d.text for d in docs}
    assert all(c.text == text[c.doc_id][c.start : c.end] for c in fixed + sentence)


def test_semantic_chunks_use_one_embedding_call(monkeypatch: pytest.MonkeyPatch) -> None:
    docs, _ = fixture_sample(3)
    calls: list[int] = []

    def fake_embed(texts: list[str], *, trace: object = None) -> np.ndarray:
        calls.append(len(texts))
        return llm.normalize_rows(np.eye(len(texts), 768) + 0.5)

    monkeypatch.setattr(llm, "embed", fake_embed)
    chunks = pipeline.chunk_docs(docs, "semantic", ingest_cfg()["chunk"])
    assert len(calls) == 1
    assert {c.doc_id for c in chunks} == {d.doc_id for d in docs}
    assert all(c.strategy == "semantic" for c in chunks)
