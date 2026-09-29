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
    seen: list[tuple[str, list[str], bool]] = []

    def run(name: str, strategies: list[str], embed: bool = True) -> None:
        seen.append((name, strategies, embed))

    monkeypatch.setattr(pipeline, "run", run)
    pipeline.main(["--corpus", "mini"])
    assert seen == [("mini", ["fixed", "sentence", "semantic"], True)]


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

    def chunk_ids(self, c: object, strategy: str, doc_ids: list[str]) -> list[str]:
        return sorted(i for i, ch in self.chunks.items() if ch.strategy == strategy)

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


def stored_store(monkeypatch: pytest.MonkeyPatch) -> FakeStore:
    """A fake store holding the fixture's sentence and fixed chunks, none embedded yet."""
    store = FakeStore()
    docs, _ = fixture_sample(3)
    cfg = ingest_cfg()["chunk"]
    store.insert_chunks(
        None, pipeline.chunk_docs(docs, "sentence", cfg) + pipeline.chunk_docs(docs, "fixed", cfg)
    )
    monkeypatch.setattr(pipeline, "corpus", store)
    monkeypatch.setattr(pipeline, "conn", NoConn)
    monkeypatch.setattr(pipeline.loader, "manifest_doc_ids", lambda name: [d.doc_id for d in docs])
    monkeypatch.setattr(pipeline, "EMBED_BATCH", 1)
    return store


def test_slices_split_the_chunks_with_no_overlap_and_no_gap() -> None:
    ids = [f"{i:016x}:sentence:{j}" for i in range(500) for j in range(4)]
    slices = [[i for i in ids if pipeline.in_slice(i, k, 4)] for k in range(1, 5)]
    assert sorted(i for s in slices for i in s) == sorted(ids)
    assert all(400 <= len(s) <= 600 for s in slices)


def test_parse_slice() -> None:
    assert pipeline.parse_slice("2/4") == (2, 4)
    for bad in ["0/4", "5/4", "2", "a/b", "2/4/1"]:
        with pytest.raises(argparse.ArgumentTypeError):
            pipeline.parse_slice(bad)


def test_embed_fills_only_its_slice_and_resumes_after_the_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = stored_store(monkeypatch)
    budget = {"texts": 1}

    def quota_embed(texts: list[str], *, trace: object = None) -> np.ndarray:
        if budget["texts"] < len(texts):
            raise llm.RateLimited("daily quota")
        budget["texts"] -= len(texts)
        return llm.normalize_rows(np.ones((len(texts), 768)))

    monkeypatch.setattr(llm, "embed", quota_embed)
    mine = {
        i
        for i, ch in store.chunks.items()
        if ch.strategy == "sentence" and pipeline.in_slice(i, 1, 2)
    }
    assert len(mine) >= 2
    with pytest.raises(SystemExit, match="slice 1/2 stopped"):
        pipeline.embed_main(["--corpus", "full", "--strategy", "sentence", "--slice", "1/2"])
    assert len(store.vecs) == 1 and set(store.vecs) <= mine

    budget["texts"] = 10_000
    pipeline.embed_main(["--corpus", "full", "--strategy", "sentence", "--slice", "1/2"])
    assert set(store.vecs) == mine
    pipeline.embed_main(["--corpus", "full", "--strategy", "sentence", "--slice", "2/2"])
    assert set(store.vecs) == {i for i, ch in store.chunks.items() if ch.strategy == "sentence"}


def test_embed_refuses_a_corpus_with_no_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    store = stored_store(monkeypatch)
    store.chunks.clear()
    with pytest.raises(SystemExit, match="no sentence chunks"):
        pipeline.embed_main(["--corpus", "full", "--strategy", "sentence"])


def test_run_without_embeddings_stores_chunks_only(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeStore()
    monkeypatch.setattr(pipeline, "corpus", store)
    monkeypatch.setattr(pipeline, "conn", NoConn)
    monkeypatch.setattr(pipeline.loader, "corpus", lambda name: fixture_sample(3))

    def no_embed(texts: list[str], *, trace: object = None) -> np.ndarray:
        raise AssertionError("--no-embed must not embed")

    monkeypatch.setattr(llm, "embed", no_embed)
    pipeline.main(["--corpus", "full", "--strategies", "sentence", "--no-embed"])
    assert store.chunks and store.vecs == {}
