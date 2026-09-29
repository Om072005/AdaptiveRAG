import numpy as np

from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Hit


def rrf(lists: list[list[Hit]], k: int = 60) -> list[Hit]:
    raise NotImplementedError


def mmr(
    hits: list[Hit], qvec: np.ndarray, vecs: dict[str, np.ndarray], lam: float, k: int
) -> list[Hit]:
    raise NotImplementedError


def merge_rerank(
    vector_hits: list[Hit], graph_hits: list[Hit], qvec: np.ndarray, k: int, trace: Trace
) -> list[Hit]:
    raise NotImplementedError
