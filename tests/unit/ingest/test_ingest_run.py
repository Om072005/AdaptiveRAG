import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from adaptiverag import llm
from adaptiverag.config import ingest_cfg
from adaptiverag.ingest import loader, pipeline
from adaptiverag.types import Chunk, Document

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


class FakeStore:
    """In memory stand in for stores.corpus, to check stop and resume without a database."""

    def __init__(self) -> None:
        self.docs: dict[str, Document] = {}
        self.chunks: dict[str, Chunk] = {}
        self.vecs: dict[str, np.ndarray] = {}

    def insert_documents(self, c: object, docs: list[Document]) -> int:
        new = [d for d in docs if d.doc_id not in self.docs]
        self.docs.update({d.doc_id: d for d in new})
        return len(new)

    def insert_chunks(self, c: object, chunks: list[Chunk]) -> int:
        new = [ch for ch in chunks if ch.chunk_id not in self.chunks]
        self.chunks.update({ch.chunk_id: ch for ch in new})
        return len(new)

    def chunked_doc_ids(self, c: object, strategy: str, doc_ids: list[str]) -> set[str]:
        return {ch.doc_id for ch in self.chunks.values() if ch.strategy == strategy}

    def chunks_without_embedding(
        self, c: object, strategies: list[str], doc_ids: list[str]
    ) -> list[Chunk]:
        return sorted(
            (
                ch
                for ch in self.chunks.values()
                if ch.strategy in strategies and ch.chunk_id not in self.vecs
            ),
            key=lambda ch: ch.chunk_id,
        )

    def set_embeddings(self, c: object, chunk_ids: list[str], vecs: np.ndarray) -> None:
        self.vecs.update(zip(chunk_ids, vecs, strict=True))


class NoConn:
    def __enter__(self) -> "NoConn":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def commit(self) -> None:
        return None


def test_a_run_stopped_by_the_quota_resumes_without_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore()
    monkeypatch.setattr(pipeline, "corpus", store)
    monkeypatch.setattr(pipeline, "conn", NoConn)
    monkeypatch.setattr(pipeline.loader, "corpus", lambda name: fixture_sample(3))
    monkeypatch.setattr(pipeline, "EMBED_BATCH", 2)
    budget = {"texts": 5}

    def quota_embed(texts: list[str], *, trace: object = None) -> np.ndarray:
        if budget["texts"] < len(texts):
            raise llm.RateLimited("daily quota")
        budget["texts"] -= len(texts)
        return llm.normalize_rows(np.ones((len(texts), 768)))

    monkeypatch.setattr(llm, "embed", quota_embed)
    with pytest.raises(SystemExit, match="rerun later"):
        pipeline.main(["--corpus", "mini", "--strategies", "sentence,fixed"])
    first_chunks, first_vecs = dict(store.chunks), dict(store.vecs)
    assert first_vecs and all(
        ch.strategy == "sentence" for ch in (store.chunks[i] for i in first_vecs)
    )
    assert not any(
        ch.strategy == "fixed" for ch in store.chunks.values()
    )  # sentence finishes first

    budget["texts"] = 10_000
    pipeline.main(["--corpus", "mini", "--strategies", "sentence,fixed"])
    assert set(first_chunks) <= set(store.chunks)
    assert set(store.vecs) == set(store.chunks)
    assert {ch.strategy for ch in store.chunks.values()} == {"sentence", "fixed"}
