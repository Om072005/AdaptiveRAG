"""python -m bench.chunking [--k 8] [--limit N]

The README chunking table, measured on the mini corpus's own HotpotQA questions (any that are in the
gold test split are left out). For each strategy, the top k chunks are found by exact cosine search
over that strategy's stored chunks of the mini corpus documents only, so every strategy searches the
same 300 documents (the full corpus has sentence chunks only), and scored:
  precision          share of retrieved characters inside gold supporting sentences (sp_precision)
  context retention  share of gold supporting sentences that sit whole inside one retrieved chunk
  retrieval score    supporting title recall@k, with MRR next to it
Each strategy is compared with the serving strategy by a seeded paired bootstrap over questions.
Needs the mini corpus chunked and embedded for every strategy on the database in DATABASE_URL.
"""

import argparse
import json
from typing import Any, cast

import numpy as np

from adaptiverag.config import ROOT, ingest_cfg, router_cfg
from adaptiverag.eval.metrics import mrr, recall_at_k, sp_precision
from adaptiverag.eval.run import chunk_spans
from adaptiverag.ingest import loader
from adaptiverag.ingest.embed import embed_texts
from adaptiverag.stores import corpus, vector
from adaptiverag.stores.db import conn
from adaptiverag.stores.flat import FlatIndex
from adaptiverag.types import Document, Hit, Strategy
from bench import results

STRATEGIES: tuple[Strategy, ...] = ("fixed", "sentence", "semantic")
BOOTSTRAP = 2000
SEED = 7
Span = tuple[str, int, int]


def supporting_spans(question: dict[str, Any], by_title: dict[str, Document]) -> list[Span]:
    """(doc_id, start, end) per supporting sentence; facts past a paragraph's end are skipped."""
    spans = []
    for title, i in question["supporting_facts"]:
        doc = by_title[title]
        if i < len(doc.sentences) and doc.sentences[i][1] > doc.sentences[i][0]:
            spans.append((doc.doc_id, *doc.sentences[i]))
    return spans


def retention(spans: list[Span], hit_offsets: list[Span]) -> float:
    """Share of supporting sentences that sit whole inside at least one retrieved chunk."""
    if not spans:
        return 0.0
    inside = [
        any(d == cd and cs <= s and e <= ce for cd, cs, ce in hit_offsets) for d, s, e in spans
    ]
    return sum(inside) / len(spans)


def paired_bootstrap(
    a: list[float], b: list[float], n: int = BOOTSTRAP, seed: int = SEED
) -> tuple[float, float, float]:
    """Mean of a - b over questions, with a 95% interval from resampling the questions."""
    diff = np.array(a) - np.array(b)
    rng = np.random.default_rng(seed)
    means = diff[rng.integers(len(diff), size=(n, len(diff)))].mean(axis=1)
    return float(diff.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def verdict(strategy: str, serving: str, interval: tuple[float, float, float]) -> str:
    """One line from the recall@k difference against the serving strategy."""
    if strategy == serving:
        return "serving now"
    _, low, high = interval
    if low > 0:
        return f"beats {serving} on recall@k (95% interval above 0)"
    if high < 0:
        return f"below {serving} on recall@k (95% interval below 0)"
    return f"too close to call against {serving} on this sample"


Row = tuple[str, str, str, int, int]  # doc_id, title, text, start_offset, end_offset


def pool(strategy: Strategy, doc_ids: list[str]) -> tuple[FlatIndex, list[str], dict[str, Row]]:
    """One strategy's embedded chunks of these documents, as an exact index plus their rows."""
    ids, vecs = vector.stored_vectors(strategy, doc_ids)
    with conn() as c:
        total = len(corpus.chunk_ids(c, strategy, doc_ids))
        rows = corpus.hit_rows(c, ids)
    if not ids or len(ids) < total:
        raise SystemExit(f"{len(ids)} of {total} {strategy} chunks are embedded; embed them first")
    index = FlatIndex()
    index.add(vecs)
    return index, ids, rows


def top_hits(
    index: FlatIndex, ids: list[str], rows: dict[str, Row], qvec: np.ndarray, k: int
) -> list[Hit]:
    """The k best chunks as ranked hits, the way the serving search reports them."""
    found, scores = index.search(qvec, k)
    hits = []
    for rank, (i, score) in enumerate(zip(found.tolist(), scores.tolist(), strict=True), start=1):
        doc_id, title, text, _, _ = rows[ids[i]]
        hits.append(Hit(ids[i], doc_id, title, text, float(score), "vector", rank))
    return hits


def score_questions(
    strategy: Strategy,
    questions: list[dict[str, Any]],
    qvecs: np.ndarray,
    by_title: dict[str, Document],
    k: int,
    doc_ids: list[str],
) -> tuple[int, list[dict[str, float]]]:
    """Number of chunks searched, and per question metrics for this strategy's top k hits."""
    index, ids, rows = pool(strategy, doc_ids)
    per_question = []
    for q, qvec in zip(questions, qvecs, strict=True):
        hits = top_hits(index, ids, rows, qvec, k)
        offsets = {h.chunk_id: (rows[h.chunk_id][0], *rows[h.chunk_id][3:]) for h in hits}
        spans = supporting_spans(q, by_title)
        titles = list(dict.fromkeys(t for t, _ in q["supporting_facts"]))
        per_question.append(
            {
                "precision": sp_precision(hits, chunk_spans(spans, offsets)),
                "context_retention": retention(spans, list(offsets.values())),
                "recall_at_k": recall_at_k(hits, titles, k),
                "mrr": mrr(hits, titles),
            }
        )
    return len(ids), per_question


def markdown(run_id: str, p: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Chunking experiment, mini corpus ({run_id})",
        "",
        "{header}"
        f"{p['n_questions']} HotpotQA questions of the mini corpus ({p['excluded_test']} left out "
        f"because they are in the gold test split), top {p['k']} chunks per strategy by exact "
        "cosine search. Fixed and semantic chunks exist only for the mini corpus's 300 documents "
        "and the full corpus is sentence chunks only, so every strategy here searches the same "
        "300 documents. This is a small sample: one question moves recall@k by "
        f"{1 / p['n_questions']:.3f}. Verdicts compare recall@k with the serving strategy "
        f"({p['serving']}) by a paired bootstrap over questions ({p['bootstrap']} resamples, seed "
        f"{p['seed']}); the config change is a separate, reviewed step.",
        "",
        "| Strategy | Params | Chunks | Precision | Context retention | Recall@k | MRR | Verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['strategy']} | {r['params']} | {r['n_chunks']} | {r['precision']:.3f} "
            f"| {r['context_retention']:.3f} | {r['retrieval_score']:.3f} | {r['mrr']:.3f} "
            f"| {r['verdict']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bench.chunking")
    parser.add_argument("--k", type=int, default=int(router_cfg()["vector"]["k"]))
    parser.add_argument("--limit", type=int, help="first N questions only, for development")
    args = parser.parse_args()

    docs, questions = loader.corpus("mini")
    test_ids = {
        json.loads(line)["id"].removeprefix("hp_")
        for line in (ROOT / "data" / "gold" / "test.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    }
    kept = [q for q in questions if q["id"] not in test_ids][: args.limit]
    by_title = {d.title: d for d in docs}
    qvecs = embed_texts([q["question"] for q in kept])
    serving = cast(Strategy, router_cfg()["serving"]["chunk_strategy"])
    cfg = ingest_cfg()["chunk"]
    params_of = {
        "fixed": f"{cfg['fixed']['n_words']} words, overlap {cfg['fixed']['overlap']}",
        "sentence": f"up to {cfg['sentence']['max_words']} words",
        "semantic": f"split above percentile {cfg['semantic']['percentile']}",
    }
    doc_ids = [d.doc_id for d in docs]
    scored = {s: score_questions(s, kept, qvecs, by_title, args.k, doc_ids) for s in STRATEGIES}
    per_strategy = {s: per_q for s, (_, per_q) in scored.items()}
    rows = []
    for s in STRATEGIES:
        n_chunks, per_q = scored[s]
        recall = [r["recall_at_k"] for r in per_q]
        interval = paired_bootstrap(recall, [r["recall_at_k"] for r in per_strategy[serving]])
        rows.append(
            {
                "strategy": s,
                "params": params_of[s],
                "n_chunks": n_chunks,
                **{
                    m: float(np.mean([r[m] for r in per_q]))
                    for m in ("precision", "context_retention", "mrr")
                },
                "retrieval_score": float(np.mean(recall)),
                "recall_vs_serving": interval,
                "verdict": verdict(s, serving, interval),
                "per_question": per_q,
            }
        )
    params = {
        "corpus": "mini",
        "n_questions": len(kept),
        "question_ids": [q["id"] for q in kept],
        "excluded_test": len(questions) - len([q for q in questions if q["id"] not in test_ids]),
        "k": args.k,
        "serving": serving,
        "chunk": cfg,
        "bootstrap": BOOTSTRAP,
        "seed": SEED,
    }
    run_id = results.new_run_id("mini")
    print(results.write("bench-chunking", run_id, params, rows, markdown(run_id, params, rows)))


if __name__ == "__main__":
    main()
