# 20260930-1400-dev-hybrid-replay

split `dev` · mode `hybrid` · variant `replay` · git `4e370b935ce4` · config `d67a90a95faa` · 15 of 15 questions stored

Compared with: `20260930-1248-dev-hybrid-baseline`

| metric | value | change |
|---|---|---|
| em | 0.600 | -0.180 |
| f1 | 0.683 | -0.138 |
| recall_at_k | 0.967 | +0.022 |
| mrr | 1.000 | +0.000 |
| sp_precision | 0.086 | +0.005 |
| faithfulness | 0.867 | -0.078 |
| relevance | 0.500 | +0.015 |
| completeness | 0.933 | -0.057 |
| cost_per_query_usd | 0.00002664 | -0.00000060 |
| p50_ms | 6824 | -337 |
| p95_ms | 12666 | +2096 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 5 | 0.800 | 0.800 | 1.000 | 1.000 | -0.152 |
| multi_hop | 6 | 0.500 | 0.611 | 0.917 | 0.667 | -0.049 |
| comparison | 4 | 0.500 | 0.643 | 1.000 | 1.000 | -0.239 |
