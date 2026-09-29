import numpy as np

from adaptiverag import llm
from adaptiverag.config import models
from adaptiverag.ingest.chunking import split_sentences
from adaptiverag.types import Chunk, Document


def embed_texts(texts: list[str]) -> np.ndarray:
    """(n, dims) float32 unit vectors in text order, cached by the gateway; no call for none."""
    if not texts:
        return np.zeros((0, models()["embed"].dims or 768), dtype=np.float32)
    return llm.embed(texts)


def embed_questions(questions: list[str]) -> np.ndarray:
    """Questions as search queries (models with separate query and document prefixes need this)."""
    if not questions:
        return np.zeros((0, models()["embed"].dims or 768), dtype=np.float32)
    return llm.embed(questions, kind="query")


def embed_chunks(chunks: list[Chunk]) -> np.ndarray:
    """(n, dims) float32 unit vectors of the chunk texts, in chunk order, cached by the gateway."""
    return embed_texts([c.text for c in chunks])


def embed_sentences(docs: list[Document]) -> list[np.ndarray]:
    """Per document, one unit vector per split_sentences span; all documents in one batched call."""
    spans = [split_sentences(d.text) for d in docs]
    vecs = embed_texts([d.text[s:e] for d, sp in zip(docs, spans, strict=True) for s, e in sp])
    out: list[np.ndarray] = []
    for sp in spans:
        out.append(vecs[: len(sp)])
        vecs = vecs[len(sp) :]
    return out
