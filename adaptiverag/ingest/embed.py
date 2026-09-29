import numpy as np

from adaptiverag.types import Chunk


def embed_chunks(chunks: list[Chunk]) -> np.ndarray:
    raise NotImplementedError
