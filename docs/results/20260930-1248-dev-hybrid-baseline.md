# 20260930-1248-dev-hybrid-baseline

split `dev` · mode `hybrid` · variant `baseline` · git `4e370b935ce4` · config `d67a90a95faa` · 100 of 100 questions stored

Compared with: `20260930-1546-dev-hybrid-baseline`

| metric | value | change |
|---|---|---|
| em | 0.780 | -0.029 |
| f1 | 0.821 | -0.041 |
| recall_at_k | 0.945 | +0.009 |
| mrr | 1.000 | +0.000 |
| sp_precision | 0.081 | -0.024 |
| faithfulness | 0.945 | +0.035 |
| relevance | 0.485 | -0.063 |
| completeness | 0.990 | +0.011 |
| cost_per_query_usd | 0.00002724 | -0.00000056 |
| p50_ms | 7161 | +509 |
| p95_ms | 10570 | +1233 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 33 | 0.939 | 0.952 | 1.000 | 1.000 |  |
| multi_hop | 38 | 0.579 | 0.661 | 0.855 | 0.868 | -0.144 |
| comparison | 29 | 0.862 | 0.882 | 1.000 | 0.983 | -0.050 |
