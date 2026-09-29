from collections.abc import Callable

import numpy as np
import pytest

from adaptiverag import llm
from adaptiverag.ingest.embed import embed_chunks, embed_sentences, embed_texts
from adaptiverag.types import Chunk, Document


def chunk(ord: int, text: str) -> Chunk:
    return Chunk(f"d:fixed:{ord}", "d", "fixed", ord, 0, len(text), text, len(text.split()))


def fake_embed(calls: list[list[str]]) -> Callable[..., np.ndarray]:
    def embed(texts: list[str], *, trace: object = None) -> np.ndarray:
        calls.append(texts)
        vecs = np.array([[len(t), i + 1.0] + [0.0] * 766 for i, t in enumerate(texts)])
        return llm.normalize_rows(vecs)

    return embed


def test_sends_chunk_texts_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(llm, "embed", fake_embed(calls))
    vecs = embed_chunks([chunk(0, "one two"), chunk(1, "three")])
    assert calls == [["one two", "three"]]
    assert vecs.shape == (2, 768) and vecs.dtype == np.float32
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0)


def test_no_chunks_makes_no_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(llm, "embed", fake_embed(calls))
    assert embed_chunks([]).shape == (0, 768)
    assert calls == []


def test_sentence_vectors_line_up_with_each_document(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(llm, "embed", fake_embed(calls))
    docs = [
        Document("a", "t", "A", "One here. Two here. Three here.", ()),
        Document("b", "t", "B", "", ()),
        Document("c", "t", "C", "Only one.", ()),
    ]
    vecs = embed_sentences(docs)
    assert calls == [["One here.", "Two here.", "Three here.", "Only one."]]
    assert [v.shape[0] for v in vecs] == [3, 0, 1]
    # the fake encodes each text's position in the call, so this is the fourth text sent
    assert np.allclose(vecs[2][0][:2], np.array([9.0, 4.0]) / np.hypot(9.0, 4.0))


def test_no_texts_makes_no_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(llm, "embed", fake_embed(calls))
    assert embed_texts([]).shape == (0, 768) and embed_sentences([]) == [] and calls == []
