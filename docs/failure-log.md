# Failure log

Real incidents found in a run or in review, oldest first. The README "Known failure modes" table is
copied from here at G6. Every row names the run that showed it.

| # | Symptom | Root cause | Fix | Status | Run |
|---|---|---|---|---|---|
| 1 | Our HNSW reaches recall@10 0.339 at ef 64 on 10k random 768 dimension vectors; the plan asked for 0.95 at ef 64 | Random Gaussian vectors have almost no neighbourhood structure in 768 dimensions: the true nearest neighbours are only slightly closer than any other point, so a graph search has to visit a large part of the index. A reference HNSW with the same M, ef_construction and vectors gave the same recall at each ef, checked once outside the repo | None in the index code. In the same run recall is 0.907 at ef 512 and 0.984 at ef 1000. The benchmark on corpus embeddings decides which ef is reported | Open until the corpus embedding benchmark | `20260929-1429-random` |
