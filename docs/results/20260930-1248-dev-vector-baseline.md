# 20260930-1248-dev-vector-baseline

split `dev` · mode `vector` · variant `baseline` · git `4e370b935ce4` · config `d67a90a95faa` · 100 of 100 questions stored

Compared with: `20260930-1532-dev-vector-baseline`

| metric | value | change |
|---|---|---|
| em | 0.710 | +0.064 |
| f1 | 0.776 | +0.038 |
| recall_at_k | 0.945 | +0.018 |
| mrr | 1.000 | +0.000 |
| sp_precision | 0.081 | -0.022 |
| faithfulness | 0.935 | +0.050 |
| relevance | 0.470 | -0.056 |
| completeness | 0.970 | +0.032 |
| cost_per_query_usd | 0.00002522 | -0.00000066 |
| p50_ms | 1030 | +314 |
| p95_ms | 1295 | -500 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 33 | 0.939 | 0.952 | 1.000 | 1.000 |  |
| multi_hop | 38 | 0.474 | 0.637 | 0.855 | 0.888 | -0.082 |
| comparison | 29 | 0.759 | 0.759 | 1.000 | 0.922 | -0.003 |
