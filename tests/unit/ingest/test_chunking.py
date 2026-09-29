import numpy as np
import pytest

from adaptiverag.config import ingest_cfg
from adaptiverag.ingest.chunking import (
    WORD,
    chunk_fixed,
    chunk_semantic,
    chunk_sentence,
    split_sentences,
)
from adaptiverag.ingest.normalize import doc_id, join_sentences
from adaptiverag.types import Chunk, Document


def make_doc(sentences: list[str], title: str = "Test") -> Document:
    text, spans = join_sentences(sentences)
    return Document(doc_id("test", title), "test", title, text, spans)


def numbered(n: int) -> Document:
    """n words w0 .. w{n-1}, a sentence break every 7 words."""
    words = [f"w{i}" for i in range(n)]
    return make_doc([" ".join(words[i : i + 7]) + "." for i in range(0, n, 7)])


def words(c: Chunk) -> list[str]:
    return WORD.findall(c.text)


def test_offsets_slice_the_document_text() -> None:
    doc = numbered(50)
    for c in chunk_fixed(doc, 8, 3):
        assert c.text == doc.text[c.start : c.end]
        assert c.n_words == len(words(c))


def test_overlap_is_exact() -> None:
    doc = numbered(50)
    chunks = chunk_fixed(doc, 8, 3)
    for a, b in zip(chunks, chunks[1:], strict=False):
        assert words(a)[-3:] == words(b)[:3]
        assert len(WORD.findall(doc.text[a.start : b.start])) == 5


def test_no_word_is_lost() -> None:
    doc = numbered(50)
    covered = {w for c in chunk_fixed(doc, 8, 3) for w in words(c)}
    assert covered == set(WORD.findall(doc.text))


def test_short_last_chunk_is_kept() -> None:
    chunks = chunk_fixed(numbered(11), 4, 1)
    assert [c.n_words for c in chunks] == [4, 4, 4, 2]
    assert words(chunks[-1]) == ["w9", "w10."]


def test_no_chunk_that_only_repeats_the_overlap() -> None:
    assert [c.n_words for c in chunk_fixed(numbered(7), 4, 1)] == [4, 4]
    assert len(chunk_fixed(numbered(64), 64, 16)) == 1


def test_ids_and_order() -> None:
    doc = numbered(30)
    chunks = chunk_fixed(doc, 10, 2)
    assert [c.ord for c in chunks] == list(range(len(chunks)))
    assert all(c.chunk_id == f"{doc.doc_id}:fixed:{c.ord}" for c in chunks)
    assert all(c.doc_id == doc.doc_id and c.strategy == "fixed" for c in chunks)


def test_empty_document_has_no_chunks() -> None:
    assert chunk_fixed(make_doc([]), 8, 2) == []


def test_configured_size_on_a_long_document() -> None:
    cfg = ingest_cfg()["chunk"]["fixed"]
    chunks = chunk_fixed(numbered(300), cfg["n_words"], cfg["overlap"])
    assert all(c.n_words == cfg["n_words"] for c in chunks[:-1])
    assert 0 < chunks[-1].n_words <= cfg["n_words"]


@pytest.mark.parametrize(("n_words", "overlap"), [(0, 0), (4, -1), (4, 4), (4, 5)])
def test_bad_sizes_raise(n_words: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_fixed(numbered(10), n_words, overlap)


def test_sentence_chunks_never_split_a_sentence() -> None:
    doc = make_doc(["One two three.", "Four five six seven.", "Eight nine.", "Ten eleven twelve."])
    boundaries = {p for s, e in split_sentences(doc.text) for p in (s, e)}
    for c in chunk_sentence(doc, 7):
        assert c.start in boundaries and c.end in boundaries
        assert c.text == doc.text[c.start : c.end]


def test_sentence_chunks_respect_max_words() -> None:
    doc = make_doc(["One two three.", "Four five six seven.", "Eight nine.", "Ten eleven twelve."])
    chunks = chunk_sentence(doc, 7)
    assert [c.text for c in chunks] == [
        "One two three. Four five six seven.",
        "Eight nine. Ten eleven twelve.",
    ]
    assert all(c.n_words <= 7 for c in chunks)


def test_a_sentence_longer_than_max_words_stays_whole() -> None:
    doc = make_doc(["Short one.", "This sentence has far too many words for it.", "End."])
    assert [c.text for c in chunk_sentence(doc, 4)] == [
        "Short one.",
        "This sentence has far too many words for it.",
        "End.",
    ]


def test_sentence_chunks_cover_every_sentence_in_order() -> None:
    doc = make_doc([f"Line {i} has five words." for i in range(40)])
    chunks = chunk_sentence(doc, 12)
    assert len(chunks) == 20 and all(c.n_words == 10 for c in chunks)
    assert " ".join(c.text for c in chunks) == doc.text
    assert [c.ord for c in chunks] == list(range(len(chunks)))
    assert all(c.chunk_id == f"{doc.doc_id}:sentence:{c.ord}" for c in chunks)


def test_sentence_chunker_edge_cases() -> None:
    assert chunk_sentence(make_doc([]), 10) == []
    with pytest.raises(ValueError):
        chunk_sentence(numbered(10), 0)


def topic_vecs(topics: list[int], dim: int = 8) -> np.ndarray:
    """One unit vector per sentence; sentences with the same topic number share a direction."""
    rng = np.random.default_rng(7)
    base = {t: rng.normal(size=dim) for t in set(topics)}
    vecs = np.array([base[t] + rng.normal(scale=0.05, size=dim) for t in topics])
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


SIX = [
    "Paris is big.",
    "It is in France.",
    "It has a tower.",
    "Tea is a drink.",
    "It is hot.",
    "Some add milk.",
]


def test_semantic_split_at_the_one_known_topic_shift() -> None:
    doc = make_doc(SIX)
    chunks = chunk_semantic(doc, topic_vecs([0, 0, 0, 1, 1, 1]), 90)
    assert [c.text for c in chunks] == [
        "Paris is big. It is in France. It has a tower.",
        "Tea is a drink. It is hot. Some add milk.",
    ]
    assert all(c.strategy == "semantic" and c.text == doc.text[c.start : c.end] for c in chunks)
    assert [c.chunk_id for c in chunks] == [f"{doc.doc_id}:semantic:0", f"{doc.doc_id}:semantic:1"]


def test_semantic_chunks_cover_the_whole_text_in_order() -> None:
    doc = make_doc(SIX)
    chunks = chunk_semantic(doc, topic_vecs([0, 1, 0, 1, 2, 2]), 50)
    assert " ".join(c.text for c in chunks) == doc.text
    assert [c.ord for c in chunks] == list(range(len(chunks)))


def test_semantic_edge_cases() -> None:
    one = make_doc(["Only one sentence here."])
    assert [c.text for c in chunk_semantic(one, topic_vecs([0]), 90)] == [one.text]
    assert chunk_semantic(make_doc([]), np.zeros((0, 8)), 90) == []
    with pytest.raises(ValueError):
        chunk_semantic(make_doc(SIX), topic_vecs([0, 0]), 90)
