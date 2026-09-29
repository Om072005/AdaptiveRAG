import re

import numpy as np

from adaptiverag.types import Chunk, Document, Strategy

WORD = re.compile(r"\S+")
DOTTED = re.compile(r"(?:[a-z]\.)+")  # initials and dotted acronyms: j., u.s., e.g.
OPENERS = "\"'“‘(["
CLOSERS = "\"'”’)]"
# Words ending in a period that are usually followed by a capitalised word in the same sentence.
# Suffixes like Inc. or etc. are left out: mid sentence they are followed by a lowercase word.
ABBREVIATIONS = frozenset(
    {
        *("mr.", "mrs.", "ms.", "dr.", "prof.", "rev.", "hon.", "sr.", "jr.", "st.", "mt.", "ft."),
        *("gen.", "col.", "lt.", "sgt.", "capt.", "gov.", "sen.", "rep.", "pres.", "ph.d."),
        *("no.", "vol.", "vs.", "jan.", "feb.", "mar.", "apr.", "jun.", "jul.", "aug.", "sep."),
        *("sept.", "oct.", "nov.", "dec."),
    }
)


def make_chunk(doc: Document, strategy: Strategy, ord: int, start: int, end: int) -> Chunk:
    """A chunk whose text is exactly doc.text[start:end]."""
    text = doc.text[start:end]
    chunk_id = f"{doc.doc_id}:{strategy}:{ord}"
    return Chunk(chunk_id, doc.doc_id, strategy, ord, start, end, text, len(WORD.findall(text)))


def ends_sentence(word: str, next_word: str) -> bool:
    """True if word closes a sentence, given the word that follows it."""
    core = word.rstrip(CLOSERS)
    if not core or core[-1] not in ".!?" or next_word.lstrip(OPENERS)[:1].islower():
        return False
    bare = core.lstrip(OPENERS).lower()
    return core[-1] != "." or (bare not in ABBREVIATIONS and not DOTTED.fullmatch(bare))


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Sentence spans over text; every non space character falls in exactly one span."""
    words = list(WORD.finditer(text))
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for i, word in enumerate(words):
        start = word.start() if start is None else start
        if i + 1 == len(words) or ends_sentence(word.group(), words[i + 1].group()):
            spans.append((start, word.end()))
            start = None
    return spans


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
