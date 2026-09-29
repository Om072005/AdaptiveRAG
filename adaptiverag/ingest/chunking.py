import numpy as np

from adaptiverag.types import Chunk, Document


def split_sentences(text: str) -> list[tuple[int, int]]:
    raise NotImplementedError


def chunk_fixed(doc: Document, n_words: int, overlap: int) -> list[Chunk]:
    raise NotImplementedError


def chunk_sentence(doc: Document, max_words: int) -> list[Chunk]:
    raise NotImplementedError


def chunk_semantic(doc: Document, sentence_vecs: np.ndarray, percentile: float) -> list[Chunk]:
    """Split where adjacent sentence cosine distance is above the percentile."""
    raise NotImplementedError
