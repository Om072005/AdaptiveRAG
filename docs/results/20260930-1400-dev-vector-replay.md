# 20260930-1400-dev-vector-replay

split `dev` · mode `vector` · variant `replay` · git `4e370b935ce4` · config `d67a90a95faa` · 15 of 15 questions stored

Compared with: `20260930-1248-dev-vector-baseline`

| metric | value | change |
|---|---|---|
| em | 0.533 | -0.177 |
| f1 | 0.625 | -0.151 |
| recall_at_k | 0.967 | +0.022 |
| mrr | 1.000 | +0.000 |
| sp_precision | 0.086 | +0.005 |
| faithfulness | 0.883 | -0.052 |
| relevance | 0.450 | -0.020 |
| completeness | 0.933 | -0.037 |
| cost_per_query_usd | 0.00002476 | -0.00000046 |
| p50_ms | 1028 | -2 |
| p95_ms | 4738 | +3443 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 5 | 0.800 | 0.800 | 1.000 | 1.000 | -0.152 |
| multi_hop | 6 | 0.333 | 0.562 | 0.917 | 0.708 | -0.075 |
| comparison | 4 | 0.500 | 0.500 | 1.000 | 1.000 | -0.259 |
