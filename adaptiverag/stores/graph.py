import numpy as np

from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import GraphPath, Retrieved, Seed


def link_entities(question: str, qvec: np.ndarray, trace: Trace) -> list[Seed]:
    raise NotImplementedError


def traverse(
    seeds: list[Seed], qvec: np.ndarray, depth: int, fanout: int, max_paths: int
) -> list[GraphPath]:
    raise NotImplementedError


def retrieve(question: str, k: int, trace: Trace, qvec: np.ndarray | None = None) -> Retrieved:
    """Hits are the provenance chunks of the best paths."""
    raise NotImplementedError
