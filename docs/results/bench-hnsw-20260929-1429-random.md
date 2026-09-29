# HNSW vs flat, random vectors (20260929-1429-random)

Run `20260929-1429-random` · 2026-09-29T14:29:34+05:30 · git `6e369ee8dd44` · config `cbef4421628a`

10000 seeded random Gaussian vectors in 768 dimensions, 100 queries, M 16, ef_construction 200, seed 7. Recall@10 is measured against the exact flat index. Latency is one query at a time in this process. Serving does not use this index: it uses pgvector HNSW (library default).

| Index | ef | Recall@10 | p50 ms | p95 ms | Build s |
|---|---|---|---|---|---|
| flat |  | 1.000 | 1.06 | 1.45 | 0.0 |
| hnsw | 10 | 0.097 | 0.31 | 0.50 | 43.0 |
| hnsw | 32 | 0.193 | 0.76 | 1.16 | 43.0 |
| hnsw | 64 | 0.339 | 1.42 | 2.01 | 43.0 |
| hnsw | 128 | 0.506 | 2.39 | 3.58 | 43.0 |
| hnsw | 256 | 0.728 | 4.27 | 6.50 | 43.0 |
| hnsw | 512 | 0.907 | 7.93 | 10.14 | 43.0 |
| hnsw | 1000 | 0.984 | 13.29 | 16.50 | 43.0 |
