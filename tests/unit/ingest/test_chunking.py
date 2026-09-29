import pytest

from adaptiverag.config import ingest_cfg
from adaptiverag.ingest.chunking import WORD, chunk_fixed
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
