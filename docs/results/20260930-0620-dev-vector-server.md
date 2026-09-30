# 20260930-0620-dev-vector-server

split `dev` · mode `vector` · variant `server` · git `8bea8c70734e` · config `421af45c74d1` · 100 of 100 questions stored

Compared with: `20260930-0120-dev-vector-baseline`

| metric | value | change |
|---|---|---|
| em | 0.710 | -0.060 |
| f1 | 0.776 | -0.034 |
| recall_at_k | 0.945 | +0.000 |
| mrr | 1.000 | +0.000 |
| sp_precision | 0.081 | +0.000 |
| faithfulness | n/a | n/a |
| relevance | n/a | n/a |
| completeness | n/a | n/a |
| cost_per_query_usd | 0.00002522 | -0.00007237 |
| p50_ms | 1524 | +735 |
| p95_ms | 2434 | +1294 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 33 | 0.939 | 0.952 | 1.000 | n/a | +0.000 |
| multi_hop | 38 | 0.474 | 0.637 | 0.855 | n/a | -0.010 |
| comparison | 29 | 0.759 | 0.759 | 1.000 | n/a | -0.103 |
