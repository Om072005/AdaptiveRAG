"""python -m bench.hnsw_vs_flat [--n 10000] [--dim 768] [--queries 100]

Recall@10 of our HNSW against the exact flat index at several ef values, with build time and
per query latency, on seeded random Gaussian vectors. Writes docs/results/bench-hnsw-<run_id>.*
"""

import argparse
import time
from collections.abc import Callable
from functools import partial
from typing import Any

import numpy as np

from adaptiverag.stores.flat import FlatIndex
from adaptiverag.stores.hnsw import HNSW
from bench import results

EFS = (10, 32, 64, 128, 256, 512, 1000)
K = 10
Search = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]


def row(
    index: str, ef: int | None, recall: float, times: list[float], build: float
) -> dict[str, Any]:
    """One results row; latency as p50 and p95 in milliseconds."""
    p50, p95 = (float(np.percentile(times, p) * 1000) for p in (50, 95))
    return {
        "index": index,
        "ef": ef,
        "recall_at_10": recall,
        "p50_ms": p50,
        "p95_ms": p95,
        "build_s": build,
    }


def timed(search: Search, queries: np.ndarray) -> tuple[list[set[int]], list[float]]:
    """Result ids and seconds per query, one query at a time."""
    ids, times = [], []
    for q in queries:
        started = time.perf_counter()
        found, _ = search(q)
        times.append(time.perf_counter() - started)
        ids.append(set(found.tolist()))
    return ids, times


def measure(
    data: np.ndarray, queries: np.ndarray, M: int, ef_construction: int, seed: int
) -> list[dict[str, Any]]:
    """One row per index and ef: recall@10 against flat, p50 and p95 search latency, build time."""
    started = time.perf_counter()
    flat = FlatIndex()
    flat.add(data)
    flat_build = time.perf_counter() - started
    started = time.perf_counter()
    hnsw = HNSW(data.shape[1], M, ef_construction, seed)
    hnsw.add(data)
    hnsw_build = time.perf_counter() - started

    truth, times = timed(partial(flat.search, k=K), queries)
    rows = [row("flat", None, 1.0, times, flat_build)]
    for ef in EFS:
        found, times = timed(partial(hnsw.search, k=K, ef=ef), queries)
        hits = sum(len(a & b) for a, b in zip(found, truth, strict=True))
        rows.append(row("hnsw", ef, hits / (K * len(queries)), times, hnsw_build))
    return rows


def markdown(run_id: str, p: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# HNSW vs flat, random vectors ({run_id})",
        "",
        "{header}"
        f"{p['n']} seeded random Gaussian vectors in {p['dim']} dimensions, "
        f"{p['queries']} queries, M {p['M']}, ef_construction {p['ef_construction']}, "
        f"seed {p['seed']}. Recall@10 is measured against the exact flat index. Latency is one "
        "query at a time in this process. Serving does not use this index: it uses pgvector "
        "HNSW (library default).",
        "",
        "| Index | ef | Recall@10 | p50 ms | p95 ms | Build s |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        ef = "" if r["ef"] is None else r["ef"]
        lines.append(
            f"| {r['index']} | {ef} | {r['recall_at_10']:.3f} | {r['p50_ms']:.2f} "
            f"| {r['p95_ms']:.2f} | {r['build_s']:.1f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bench.hnsw_vs_flat")
    parser.add_argument("--n", type=int, default=10_000)
    parser.add_argument("--dim", type=int, default=768)
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--M", type=int, default=16)
    parser.add_argument("--ef-construction", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    params = {
        "source": "random",
        "n": args.n,
        "dim": args.dim,
        "queries": args.queries,
        "M": args.M,
        "ef_construction": args.ef_construction,
        "seed": args.seed,
        "k": K,
        "efs": list(EFS),
    }
    rng = np.random.default_rng(args.seed)
    data = rng.normal(size=(args.n, args.dim)).astype(np.float32)
    queries = rng.normal(size=(args.queries, args.dim)).astype(np.float32)
    rows = measure(data, queries, args.M, args.ef_construction, args.seed)
    run_id = results.new_run_id("random")
    print(results.write("bench-hnsw", run_id, params, rows, markdown(run_id, params, rows)))


if __name__ == "__main__":
    main()
