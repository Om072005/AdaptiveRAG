# 20260930-0634-dev-graph-server

split `dev` · mode `graph` · variant `server` · git `8bea8c70734e` · config `421af45c74d1` · 100 of 100 questions stored

Compared with: `20260930-0133-dev-graph-baseline`

| metric | value | change |
|---|---|---|
| em | 0.490 | +0.066 |
| f1 | 0.512 | +0.047 |
| recall_at_k | 0.690 | +0.016 |
| mrr | 0.677 | -0.011 |
| sp_precision | 0.150 | +0.043 |
| faithfulness | n/a | n/a |
| relevance | n/a | n/a |
| completeness | n/a | n/a |
| cost_per_query_usd | 0.00146866 | +0.00122150 |
| p50_ms | 7065 | +5399 |
| p95_ms | 10267 | +7348 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 33 | 0.818 | 0.830 | 0.909 | n/a | +0.177 |
| multi_hop | 38 | 0.158 | 0.168 | 0.421 | n/a | -0.065 |
| comparison | 29 | 0.552 | 0.599 | 0.793 | n/a | -0.005 |
