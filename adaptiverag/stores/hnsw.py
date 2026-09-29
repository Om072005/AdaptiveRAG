"""HNSW written from scratch, benchmark only (not on the serving path)."""

import numpy as np


class HNSW:
    def __init__(self, dim: int, M: int = 16, ef_construction: int = 200, seed: int = 7) -> None:
        self.dim = dim
        self.M = M
        self.ef_construction = ef_construction
        self.seed = seed

    def add(self, vecs: np.ndarray) -> None:
        raise NotImplementedError

    def search(self, q: np.ndarray, k: int, ef: int = 64) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def save(self, path: str) -> None:
        raise NotImplementedError

    @classmethod
    def load(cls, path: str) -> "HNSW":
        raise NotImplementedError
