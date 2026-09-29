"""HNSW written from scratch, benchmark only (not on the serving path).

Malkov and Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical
Navigable Small World graphs" (2016): layered proximity graphs, greedy descent from the top layer,
a beam of width ef on layer 0, and the neighbour selection heuristic (their algorithm 4).
Distances are cosine distances on unit vectors: 1 - dot.
"""

import heapq
import json
import math

import numpy as np

from adaptiverag.stores.flat import unit_rows


class HNSW:
    def __init__(self, dim: int, M: int = 16, ef_construction: int = 200, seed: int = 7) -> None:
        self.dim = dim
        self.M = M
        self.ef_construction = ef_construction
        self.seed = seed
        self.max_links0 = 2 * M  # layer 0 keeps twice as many links, as in the paper
        self.level_mult = 1 / math.log(M)
        self.rng = np.random.default_rng(seed)
        self.vecs = np.zeros((0, dim), dtype=np.float32)
        self.levels: list[int] = []
        self.links: list[list[list[int]]] = []  # links[node][layer] = neighbour ids
        self.entry = -1

    def add(self, vecs: np.ndarray) -> None:
        """Insert vectors in order; their ids continue from the last add."""
        start = len(self.vecs)
        self.vecs = np.vstack([self.vecs, unit_rows(vecs)])
        for node in range(start, len(self.vecs)):
            self._insert(node)

    def search(self, q: np.ndarray, k: int, ef: int = 64) -> tuple[np.ndarray, np.ndarray]:
        """(ids, cosine scores) of the k best found with a layer 0 beam of max(ef, k)."""
        if self.entry < 0:
            return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
        qv = unit_rows(q)[0]
        ep = self.entry
        for layer in range(self.levels[self.entry], 0, -1):
            ep = self._search_layer(qv, [ep], 1, layer)[0][1]
        found = self._search_layer(qv, [ep], max(ef, k), 0)[:k]
        ids = np.array([i for _, i in found], dtype=np.int64)
        return ids, np.array([1.0 - d for d, _ in found], dtype=np.float32)

    def _insert(self, node: int) -> None:
        level = int(-math.log(1.0 - self.rng.random()) * self.level_mult)
        self.levels.append(level)
        self.links.append([[] for _ in range(level + 1)])
        if self.entry < 0:
            self.entry = node
            return
        q = self.vecs[node]
        top = self.levels[self.entry]
        ep = self.entry
        for layer in range(top, level, -1):
            ep = self._search_layer(q, [ep], 1, layer)[0][1]
        entry_points = [ep]
        for layer in range(min(level, top), -1, -1):
            found = self._search_layer(q, entry_points, self.ef_construction, layer)
            self.links[node][layer] = self._select(found, self.M)
            limit = self.max_links0 if layer == 0 else self.M
            for n in self.links[node][layer]:
                self.links[n][layer].append(node)
                if len(self.links[n][layer]) > limit:
                    self.links[n][layer] = self._shrink(n, layer, limit)
            entry_points = [i for _, i in found]
        if level > top:
            self.entry = node

    def _search_layer(
        self, q: np.ndarray, entry_points: list[int], ef: int, layer: int
    ) -> list[tuple[float, int]]:
        """The ef closest nodes reachable on one layer, as sorted (distance, id)."""
        visited = set(entry_points)
        dists = (1.0 - self.vecs[entry_points] @ q).tolist()
        candidates = list(zip(dists, entry_points, strict=True))  # min heap: nearest first
        heapq.heapify(candidates)
        best = [(-d, i) for d, i in candidates]  # max heap: furthest of the kept ones first
        heapq.heapify(best)
        while len(best) > ef:
            heapq.heappop(best)
        while candidates:
            d, c = heapq.heappop(candidates)
            if d > -best[0][0]:
                break
            fresh = [n for n in self.links[c][layer] if n not in visited]
            if not fresh:
                continue
            visited.update(fresh)
            # one matrix product per expanded node instead of one per neighbour
            for dn, n in zip((1.0 - self.vecs[fresh] @ q).tolist(), fresh, strict=True):
                if len(best) < ef or dn < -best[0][0]:
                    heapq.heappush(candidates, (dn, n))
                    heapq.heappush(best, (-dn, n))
                    if len(best) > ef:
                        heapq.heappop(best)
        return sorted((-d, i) for d, i in best)

    def _select(self, found: list[tuple[float, int]], m: int) -> list[int]:
        """Paper heuristic: keep a candidate only if it is nearer the base than any kept one."""
        kept: list[int] = []
        for d, c in found:
            if len(kept) == m:
                break
            if not kept or bool(np.all(1.0 - self.vecs[kept] @ self.vecs[c] > d)):
                kept.append(c)
        return kept

    def _shrink(self, node: int, layer: int, limit: int) -> list[int]:
        links = self.links[node][layer]
        dists = (1.0 - self.vecs[links] @ self.vecs[node]).tolist()
        return self._select(sorted(zip(dists, links, strict=True)), limit)

    def save(self, path: str) -> None:
        counts = [len(layer) for node in self.links for layer in node]
        flat = [n for node in self.links for layer in node for n in layer]
        params = {"dim": self.dim, "M": self.M, "ef_construction": self.ef_construction}
        with open(path, "wb") as f:
            np.savez(
                f,
                params=json.dumps({**params, "seed": self.seed, "entry": self.entry}),
                rng=json.dumps(self.rng.bit_generator.state),
                vecs=self.vecs,
                levels=np.array(self.levels, dtype=np.int64),
                counts=np.array(counts, dtype=np.int64),
                flat=np.array(flat, dtype=np.int64),
            )

    @classmethod
    def load(cls, path: str) -> "HNSW":
        with np.load(path) as f:
            p = json.loads(str(f["params"]))
            index = cls(p["dim"], p["M"], p["ef_construction"], p["seed"])
            index.rng.bit_generator.state = json.loads(str(f["rng"]))
            index.vecs, index.entry = f["vecs"], p["entry"]
            index.levels = f["levels"].tolist()
            counts, flat = f["counts"].tolist(), f["flat"].tolist()
        pos = 0
        sizes = iter(counts)
        for level in index.levels:
            node: list[list[int]] = []
            for _ in range(level + 1):
                n = next(sizes)
                node.append(flat[pos : pos + n])
                pos += n
            index.links.append(node)
        return index
