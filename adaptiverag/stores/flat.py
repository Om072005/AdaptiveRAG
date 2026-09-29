"""Exact search, benchmark only (not on the serving path)."""

import numpy as np


def unit_rows(vecs: np.ndarray) -> np.ndarray:
    """float32 rows scaled to length 1, so a dot product is the cosine."""
    vecs = np.atleast_2d(np.asarray(vecs, dtype=np.float32))
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.where(norms == 0, 1, norms)


class FlatIndex:
    """Cosine against every stored vector; ids are insertion order. The recall baseline."""

    def __init__(self) -> None:
        self.vecs = np.zeros((0, 0), dtype=np.float32)

    def add(self, vecs: np.ndarray) -> None:
        new = unit_rows(vecs)
        self.vecs = new if self.vecs.size == 0 else np.vstack([self.vecs, new])

    def search(self, q: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        """(ids, scores)."""
        if self.vecs.size == 0:
            return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
        scores = self.vecs @ unit_rows(q)[0]
        # best score first, lower id first on ties, so results never depend on sort stability
        order = np.lexsort((np.arange(len(scores)), -scores))[:k]
        return order.astype(np.int64), scores[order]
