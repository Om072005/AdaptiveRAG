# Failure log

Real incidents found in a run or in review, oldest first. The README "Known failure modes" table is
copied from here at G6. Every row names the run that showed it.

| # | Symptom | Root cause | Fix | Status | Run |
|---|---|---|---|---|---|
| 1 | Our HNSW reaches recall@10 0.339 at ef 64 on 10k random 768 dimension vectors; the plan asked for 0.95 at ef 64 | Random Gaussian vectors have almost no neighbourhood structure in 768 dimensions: the true nearest neighbours are only slightly closer than any other point, so a graph search has to visit a large part of the index. A reference HNSW with the same M, ef_construction and vectors gave the same recall at each ef, checked once outside the repo | None in the index code. In the same run recall is 0.907 at ef 512 and 0.984 at ef 1000. The benchmark on corpus embeddings decides which ef is reported | Closed: on the 4,277 stored sentence chunk embeddings with the 100 dev questions as queries, recall@10 is 0.996 at ef 64 (run `20260930-0117-corpus-sentence`) | `20260929-1429-random` |
| 2 | After embeddings moved to the local model, every answer scored confidence 1.0, nothing was flagged, and the vector route never fell back to hybrid | `vector.min_top_score = 0.55` was set for Gemini's cosine scale. With nomic-embed-text the top-1 cosine on the 100 dev questions runs from 0.684 (5th percentile) to 0.897 (95th), none under 0.55; hits from supporting documents have median 0.748, other hits 0.634. So retrieval strength always saturated and fallback row F1 could not fire | Re-tune `vector.min_top_score` (and check `graph.min_seed_score`) on the dev split with `eval.tune`, and cite the run id in the router.toml commit. No value is changed by guess | Open | `20260930-0041-dev-vector-smoke` |
