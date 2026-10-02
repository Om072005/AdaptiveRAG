# What went wrong, and what we did about it

Real incidents found in a run or in review while building AdaptiveRAG, oldest first. Each one names the run
that showed it, so the numbers can be checked in [`docs/results/`](results/). The same incidents, as one table,
are in the [failure log](failure-log.md).

| # | Incident | Status |
|---|---|---|
| 1 | [Our HNSW index looked far below target](#1-our-hnsw-index-looked-far-below-target) | Closed |
| 2 | [Every answer scored full confidence](#2-every-answer-scored-full-confidence) | Closed |
| 3 | [Letting the router choose scored worse than one method](#3-letting-the-router-choose-scored-worse-than-one-method) | Fixed |
| 4 | [Entity resolution merged different things](#4-entity-resolution-merged-different-things) | Fixed |
| 5 | [Answer confidence hardly tracks the judge](#5-answer-confidence-hardly-tracks-the-judge) | Open |
| 6 | [A correct number scores zero](#6-a-correct-number-scores-zero) | Known limit |

---

## 1. Our HNSW index looked far below target

**What we saw.** Our HNSW reached recall@10 of 0.339 at ef 64 on 10k random 768 dimension vectors. The plan asked
for 0.95 at ef 64.

**Why.** Random Gaussian vectors have almost no neighbourhood structure in 768 dimensions: the true nearest
neighbours are only slightly closer than any other point, so a graph search has to visit a large part of the
index. A reference HNSW with the same M, ef_construction and vectors gave the same recall at each ef.

**What we did.** Nothing in the index code. In the same run recall is 0.907 at ef 512 and 0.984 at ef 1000, and
the benchmark on real corpus embeddings decides which ef is reported.

**Status: closed.** On the 4,277 stored sentence chunk embeddings, with the 100 dev questions as queries,
recall@10 is 0.996 at ef 64 (run `20260930-0117-corpus-sentence`).

Seen in `20260929-1429-random`.

## 2. Every answer scored full confidence

**What we saw.** After embeddings moved to the local model, every answer scored confidence 1.0, nothing was
flagged, and the vector route never fell back to hybrid.

**Why.** `vector.min_top_score = 0.55` was set for Gemini's cosine scale. With nomic-embed-text the top-1 cosine
on the 100 dev questions runs from 0.684 (5th percentile) to 0.897 (95th), never under 0.55, so retrieval strength
always saturated and the fallback could not fire.

**What we did.** Re-tuned the threshold on the dev split with `eval.tune` instead of guessing a value.

**Status: closed as inert.** Every `min_top_score` from 0.30 to 0.75 scores the same (dev F1 0.844), because no
confident single hop question has a top-1 cosine under 0.68. The value stays 0.55, and the fallback is kept for
other corpora.

Seen in `20260930-0041-dev-vector-smoke`, `20260930-0620-dev-vector-server`.

## 3. Letting the router choose scored worse than one method

**What we saw.** Auto mode scored dev F1 0.568, below forced vector (0.776) and hybrid (0.844), although the
router itself classified questions well (macro F1 0.877).

**Why.** The graph route alone answered multi hop questions at F1 0.168 (hybrid: 0.671 on the same questions)
and comparisons at 0.599 (hybrid: 0.914). The graph misses supporting sentences that the vector side of hybrid
finds.

**What we did.** Decision D17: questions that join or compare facts now go to hybrid
(`relational_route = "hybrid"`), with `classifier.min_confidence = 0.85` from `eval.tune`. The offline replay
scored 0.844. The graph route and its forced runs stay for comparison.

**Status: fixed** in config.

Seen in `20260930-0724-dev-auto-server`, `20260930-0634-dev-graph-server`, `20260930-0659-dev-hybrid-server`.

## 4. Entity resolution merged different things

**What we saw.** 44 of 100 sampled merge decisions were wrong, among them "November 1, 1961" with
"November 19, 1957", and Cork City Council with Cork County Council.

**Why.** The embedding rule (cosine at or above 0.88 within a type and blocking key) had precision 0.125 (6 of 48).
Short names such as dates and numbers embed almost identically whatever their value.

**What we did.** Decision D18: embedding merges are off (`resolve.embed_merge = false`), and the graph was rebuilt
from the cached extraction.

**Status: fixed.** A new sample of 100 decisions scores precision 0.91, all by the name rule.

Seen in the first labelled sample at `d1c3727`, and the graph report after D18.

## 5. Answer confidence hardly tracks the judge

**What we saw.** Confidence correlates with the judge's faithfulness score at only 0.04 on the judged dev auto run,
and correct answers with one clear citation were flagged low confidence (Hawaii Senate, the National World War I
Memorial, L. B. Day Amphitheatre on the test split).

**Why.** gpt-oss sometimes writes citation markers as `【1】`, which the citation parser did not read, so citation
coverage was 0. Beyond that, coverage and retrieval strength are weak signals when almost every answer is
faithful (mean 0.975).

**What we did.** `cite.py` reads full width brackets (D23). Calibration found no weighting worth applying.

**Status: open.** The confidence signal needs a better input than coverage and retrieval strength.

Seen in `20260930-1346-dev-auto-baseline`, `20260930-1557-test-auto-baseline`.

## 6. A correct number scores zero

**What we saw.** A correct numeric answer scored F1 0: "25" against the gold "twenty-five" (Hawaii Senate, test
split).

**Why.** Token F1 compares normalized words, and numerals and number words are different tokens.

**What we did.** Nothing. The metric stays HotpotQA's so our numbers compare with published results. The judge
scored the answer fully faithful.

**Status: known limit** of the metric.

Seen in `20260930-1557-test-auto-baseline`.

---

## What is ours, and what is borrowed

- **Every number** on the page and in the README comes from a run listed in
  [`docs/results/pinned.toml`](results/pinned.toml), and each figure names that run. A result that came out worse
  than expected stays.
- **Our own code:** retrieval, routing, graph traversal, merging and the question classifier.
- **Library defaults:** vector search is served by pgvector's HNSW index (our own HNSW is measured against it), and
  embeddings come from an open model, nomic-embed-text, served by Ollama.
- **Models:** answers come from open models run through Ollama, gpt-oss 20B as the small model and
  Qwen 3.6 35B-A3B as the large one. Their cost is the public list price of the same weights, not what we paid.
- **Judging:** every answer is scored by Gemma 4 31B (open weights, run on a rented GPU server), a different model
  family from both. A judge model is an imperfect proxy, so a sample of its scores is checked by hand and the
  agreement is reported with the results.
- **Latency** comes from two machines: model calls first made on a rented server with two RTX 5090 cards keep that
  time when a later run reuses them from the cache, and new calls and database round trips are timed on one of
  our PCs.
