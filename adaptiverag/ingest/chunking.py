import re

import numpy as np

from adaptiverag.types import Chunk, Document, Strategy

WORD = re.compile(r"\S+")


def make_chunk(doc: Document, strategy: Strategy, ord: int, start: int, end: int) -> Chunk:
    """A chunk whose text is exactly doc.text[start:end]."""
    text = doc.text[start:end]
    chunk_id = f"{doc.doc_id}:{strategy}:{ord}"
    return Chunk(chunk_id, doc.doc_id, strategy, ord, start, end, text, len(WORD.findall(text)))


def split_sentences(text: str) -> list[tuple[int, int]]:
    raise NotImplementedError


def chunk_fixed(doc: Document, n_words: int, overlap: int) -> list[Chunk]:
    """Windows of n_words words, each sharing overlap words with the previous; short last kept."""
    if n_words <= 0 or not 0 <= overlap < n_words:
        raise ValueError(f"need n_words > 0 and 0 <= overlap < n_words, got {n_words}, {overlap}")
    words = [m.span() for m in WORD.finditer(doc.text)]
    chunks: list[Chunk] = []
    for first in range(0, len(words), n_words - overlap):
        last = min(first + n_words, len(words))
        chunks.append(make_chunk(doc, "fixed", len(chunks), words[first][0], words[last - 1][1]))
        if last == len(words):
            break
    return chunks


def chunk_sentence(doc: Document, max_words: int) -> list[Chunk]:
    raise NotImplementedError


def chunk_semantic(doc: Document, sentence_vecs: np.ndarray, percentile: float) -> list[Chunk]:
    """Split where adjacent sentence cosine distance is above the percentile."""
    raise NotImplementedError
