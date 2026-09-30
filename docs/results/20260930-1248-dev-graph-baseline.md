# 20260930-1248-dev-graph-baseline

split `dev` · mode `graph` · variant `baseline` · git `4e370b935ce4` · config `d67a90a95faa` · 100 of 100 questions stored

Compared with: `20260930-1546-dev-graph-baseline`

| metric | value | change |
|---|---|---|
| em | 0.480 | +0.140 |
| f1 | 0.498 | +0.130 |
| recall_at_k | 0.675 | +0.105 |
| mrr | 0.681 | +0.069 |
| sp_precision | 0.154 | -0.030 |
| faithfulness | 0.943 | +0.057 |
| relevance | 0.623 | -0.077 |
| completeness | 0.970 | +0.030 |
| cost_per_query_usd | 0.00001931 | -0.00000045 |
| p50_ms | 5492 | +811 |
| p95_ms | 7554 | +844 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 33 | 0.818 | 0.830 | 0.909 | 1.000 |  |
| multi_hop | 38 | 0.158 | 0.195 | 0.408 | 0.901 | -0.079 |
| comparison | 29 | 0.517 | 0.517 | 0.759 | 0.931 | +0.039 |
