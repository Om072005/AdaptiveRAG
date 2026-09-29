"""Exact search, benchmark only (not on the serving path)."""

import numpy as np


class FlatIndex:
    def add(self, vecs: np.ndarray) -> None:
        raise NotImplementedError

    def search(self, q: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        """(ids, scores)."""
        raise NotImplementedError
