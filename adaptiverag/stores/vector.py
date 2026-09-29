import numpy as np

from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Hit, Retrieved, Strategy


def search(qvec: np.ndarray, k: int, strategy: Strategy) -> list[Hit]:
    """pgvector HNSW, cosine."""
    raise NotImplementedError


def retrieve(question: str, k: int, trace: Trace, qvec: np.ndarray | None = None) -> Retrieved:
    raise NotImplementedError
