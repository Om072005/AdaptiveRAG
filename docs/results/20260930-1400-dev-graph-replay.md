# 20260930-1400-dev-graph-replay

split `dev` · mode `graph` · variant `replay` · git `4e370b935ce4` · config `d67a90a95faa` · 15 of 15 questions stored

Compared with: `20260930-1248-dev-graph-baseline`

| metric | value | change |
|---|---|---|
| em | 0.333 | -0.147 |
| f1 | 0.333 | -0.165 |
| recall_at_k | 0.600 | -0.075 |
| mrr | 0.669 | -0.012 |
| sp_precision | 0.135 | -0.018 |
| faithfulness | 1.000 | +0.057 |
| relevance | 0.600 | -0.023 |
| completeness | 1.000 | +0.030 |
| cost_per_query_usd | 0.00001852 | -0.00000080 |
| p50_ms | 5683 | +191 |
| p95_ms | 9091 | +1537 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 5 | 0.600 | 0.600 | 0.800 | 1.000 | -0.230 |
| multi_hop | 6 | 0.167 | 0.167 | 0.500 | 1.000 | -0.028 |
| comparison | 4 | 0.250 | 0.250 | 0.500 | 1.000 | -0.267 |
