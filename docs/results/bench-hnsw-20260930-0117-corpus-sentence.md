# HNSW vs flat, sentence chunk embeddings (20260930-0117-corpus-sentence)

Run `20260930-0117-corpus-sentence` · 2026-09-30T01:17:21+05:30 · git `45135b529ebd` · config `cb955bd52cb9`

4277 stored sentence chunk embeddings of the full corpus (768 dimensions), queried with the 100 dev gold questions embedded by the same model. pgvector's index uses its defaults (m 16, ef_construction 64) and is forced through the partial index at each ef_search; 'as served' is the plan serving uses. pgvector latency includes the round trip to Neon; flat and our HNSW run in this process. Our HNSW: M 16, ef_construction 200, seed 7. Recall@10 is measured against the exact flat index, one query at a time. Serving uses pgvector HNSW (library default), not our index.

| Index | ef | Recall@10 | p50 ms | p95 ms | Build s |
|---|---|---|---|---|---|
| flat |  | 1.000 | 0.40 | 0.63 | 0.0 |
| hnsw | 10 | 0.918 | 0.19 | 0.26 | 12.7 |
| hnsw | 32 | 0.990 | 0.42 | 0.59 | 12.7 |
| hnsw | 64 | 0.996 | 0.76 | 1.42 | 12.7 |
| hnsw | 128 | 0.998 | 1.49 | 1.77 | 12.7 |
| hnsw | 256 | 0.999 | 2.42 | 3.06 | 12.7 |
| hnsw | 512 | 1.000 | 4.07 | 5.29 | 12.7 |
| hnsw | 1000 | 1.000 | 6.96 | 8.98 | 12.7 |
| pgvector hnsw | 10 | 0.948 | 395.33 | 454.46 |  |
| pgvector hnsw | 40 | 0.993 | 393.07 | 401.42 |  |
| pgvector hnsw | 100 | 0.997 | 394.07 | 403.50 |  |
| pgvector hnsw | 200 | 1.000 | 394.87 | 406.50 |  |
| pgvector hnsw | 400 | 1.000 | 395.40 | 408.81 |  |
| pgvector as served |  | 1.000 | 73.62 | 78.77 |  |
