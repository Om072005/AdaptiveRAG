"""python -m bench.hnsw_vs_flat [--source random|corpus] [--strategy sentence] [--n 10000]

Recall@10 against the exact flat index at several ef values, with build time and per query latency.
random: seeded Gaussian vectors, our HNSW vs flat.
corpus: the stored chunk embeddings of one strategy (full corpus) with the dev gold questions as
queries; adds pgvector's HNSW, forced through the partial index at several ef_search values, and
the plan serving actually uses. Writes docs/results/bench-hnsw-<run_id>.*
"""

import argparse
import json
import time
from collections.abc import Callable, Iterable
from functools import partial
from typing import Any, cast

import numpy as np

from adaptiverag.config import ROOT, settings
from adaptiverag.ingest import loader
from adaptiverag.ingest.embed import embed_texts
from adaptiverag.stores import corpus, db, vector
from adaptiverag.stores.flat import FlatIndex
from adaptiverag.stores.hnsw import HNSW
from adaptiverag.types import Strategy
from bench import results

EFS = (10, 32, 64, 128, 256, 512, 1000)
PG_EF_SEARCH = (10, 40, 100, 200, 400)  # 40 is pgvector's default
K = 10
Search = Callable[[np.ndarray], Iterable[Any]]


def row(
    index: str, ef: int | None, recall: float, times: list[float], build: float | None
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


def timed(search: Search, queries: np.ndarray) -> tuple[list[set[Any]], list[float]]:
    """Result ids and seconds per query, one query at a time."""
    ids, times = [], []
    for q in queries:
        started = time.perf_counter()
        found = set(search(q))
        times.append(time.perf_counter() - started)
        ids.append(found)
    return ids, times


def recall(found: list[set[Any]], truth: list[set[Any]]) -> float:
    return sum(len(a & b) for a, b in zip(found, truth, strict=True)) / (K * len(truth))


def flat_ids(index: FlatIndex, q: np.ndarray) -> list[int]:
    return list(index.search(q, K)[0].tolist())


def hnsw_ids(index: HNSW, ef: int, q: np.ndarray) -> list[int]:
    return list(index.search(q, K, ef=ef)[0].tolist())


def served_ids(strategy: Strategy, q: np.ndarray) -> list[str]:
    return [h.chunk_id for h in vector.search(q, K, strategy)]


def measure(
    data: np.ndarray, queries: np.ndarray, M: int, ef_construction: int, seed: int
) -> tuple[list[dict[str, Any]], list[set[Any]]]:
    """Flat and our HNSW rows, plus the exact top 10 per query (row numbers into data)."""
    started = time.perf_counter()
    flat = FlatIndex()
    flat.add(data)
    flat_build = time.perf_counter() - started
    started = time.perf_counter()
    hnsw = HNSW(data.shape[1], M, ef_construction, seed)
    hnsw.add(data)
    hnsw_build = time.perf_counter() - started

    truth, times = timed(partial(flat_ids, flat), queries)
    rows = [row("flat", None, 1.0, times, flat_build)]
    for ef in EFS:
        found, times = timed(partial(hnsw_ids, hnsw, ef), queries)
        rows.append(row("hnsw", ef, recall(found, truth), times, hnsw_build))
    return rows, truth


def pgvector_rows(
    ids: list[str], queries: np.ndarray, truth: list[set[Any]], strategy: Strategy
) -> list[dict[str, Any]]:
    """pgvector's HNSW forced at each ef_search, then the plan serving uses, against flat."""
    truth_ids = [{ids[i] for i in t} for t in truth]
    rows = []
    with db.conn() as c:
        c.autocommit = True
        if not vector.uses_index(c, queries[0], K, strategy):
            raise SystemExit(f"the forced plan does not scan chunks_hnsw_{strategy}")
        for ef in PG_EF_SEARCH:
            search = partial(vector.index_search, c, k=K, strategy=strategy, ef_search=ef)
            found, times = timed(search, queries)
            rows.append(row("pgvector hnsw", ef, recall(found, truth_ids), times, None))
    found, times = timed(partial(served_ids, strategy), queries)
    rows.append(row("pgvector as served", None, recall(found, truth_ids), times, None))
    return rows


def dev_questions() -> list[str]:
    path = ROOT / "data" / "gold" / "dev.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line)["question"] for line in lines if line]


def markdown(run_id: str, p: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    if p["source"] == "random":
        title = "random vectors"
        about = f"{p['n']} seeded random Gaussian vectors in {p['dim']} dimensions, "
        about += f"{p['queries']} queries"
    else:
        title = f"{p['strategy']} chunk embeddings"
        about = (
            f"{p['n']} stored {p['strategy']} chunk embeddings of the full corpus ({p['dim']} "
            f"dimensions), queried with the {p['queries']} dev gold questions embedded by the same "
            "model. pgvector's index uses its defaults (m 16, ef_construction 64) and is forced "
            "through the partial index at each ef_search; 'as served' is the plan serving uses. "
            "pgvector latency includes the round trip to Neon; flat and our HNSW run in this "
            "process"
        )
    lines = [
        f"# HNSW vs flat, {title} ({run_id})",
        "",
        "{header}"
        f"{about}. Our HNSW: M {p['M']}, ef_construction {p['ef_construction']}, seed {p['seed']}. "
        "Recall@10 is measured against the exact flat index, one query at a time. Serving uses "
        "pgvector HNSW (library default), not our index.",
        "",
        "| Index | ef | Recall@10 | p50 ms | p95 ms | Build s |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        ef = "" if r["ef"] is None else r["ef"]
        build = "" if r["build_s"] is None else f"{r['build_s']:.1f}"
        lines.append(
            f"| {r['index']} | {ef} | {r['recall_at_10']:.3f} | {r['p50_ms']:.2f} "
            f"| {r['p95_ms']:.2f} | {build} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bench.hnsw_vs_flat")
    parser.add_argument("--source", choices=["random", "corpus"], default="random")
    parser.add_argument("--strategy", choices=["fixed", "sentence", "semantic"], default="sentence")
    parser.add_argument("--n", type=int, default=10_000, help="random only")
    parser.add_argument("--dim", type=int, default=768, help="random only")
    parser.add_argument("--queries", type=int, default=100, help="random only")
    parser.add_argument("--M", type=int, default=16)
    parser.add_argument("--ef-construction", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    params: dict[str, Any] = {
        "source": args.source,
        "M": args.M,
        "ef_construction": args.ef_construction,
        "seed": args.seed,
        "k": K,
        "efs": list(EFS),
    }
    if args.source == "random":
        rng = np.random.default_rng(args.seed)
        data = rng.normal(size=(args.n, args.dim)).astype(np.float32)
        queries = rng.normal(size=(args.queries, args.dim)).astype(np.float32)
        rows, _ = measure(data, queries, args.M, args.ef_construction, args.seed)
        label = "random"
    else:
        strategy = cast(Strategy, args.strategy)
        doc_ids = loader.manifest_doc_ids("full")
        ids, data = vector.stored_vectors(strategy, doc_ids)
        with db.conn() as c:
            total = len(corpus.chunk_ids(c, strategy, doc_ids))
        if len(ids) < total:
            raise SystemExit(
                f"only {len(ids)} of {total} {strategy} chunks are embedded; finish them first"
            )
        queries = embed_texts(dev_questions())
        rows, truth = measure(data, queries, args.M, args.ef_construction, args.seed)
        rows += pgvector_rows(ids, queries, truth, strategy)
        params |= {
            "strategy": strategy,
            "pg_ef_search": list(PG_EF_SEARCH),
            "database": db_endpoint(),
        }
        label = f"corpus-{strategy}"
    params |= {"n": len(data), "dim": int(data.shape[1]), "queries": len(queries)}
    run_id = results.new_run_id(label)
    print(results.write("bench-hnsw", run_id, params, rows, markdown(run_id, params, rows)))


def db_endpoint() -> str:
    return settings().database_url.split("@")[-1].split(".")[0]


if __name__ == "__main__":
    main()
