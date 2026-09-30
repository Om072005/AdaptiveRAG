# 20260930-1400-dev-auto-replay

split `dev` · mode `auto` · variant `replay` · git `4e370b935ce4` · config `d67a90a95faa` · 15 of 15 questions stored

Compared with: `20260930-1346-dev-auto-baseline`

| metric | value | change |
|---|---|---|
| em | 0.733 | -0.067 |
| f1 | 0.787 | -0.061 |
| recall_at_k | 0.967 | +0.022 |
| mrr | 1.000 | +0.000 |
| sp_precision | 0.086 | +0.005 |
| faithfulness | 0.933 | -0.042 |
| relevance | 0.500 | +0.050 |
| completeness | 1.000 | +0.000 |
| cost_per_query_usd | 0.00070623 | -0.00012472 |
| p50_ms | 6998 | -513 |
| p95_ms | 61116 | +2156 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 5 | 0.800 | 0.800 | 1.000 | 1.000 | -0.152 |
| multi_hop | 6 | 0.667 | 0.800 | 0.917 | 0.833 | +0.098 |
| comparison | 4 | 0.750 | 0.750 | 1.000 | 1.000 | -0.170 |

## Router (macro F1 0.750)

Routes taken: vector 2, graph 0, hybrid 13

Fallbacks: 0 of 15 questions

| gold, predicted | single_hop | multi_hop | comparison |
|---|---|---|---|
| single_hop | 4 | 1 | 0 |
| multi_hop | 2 | 4 | 0 |
| comparison | 1 | 0 | 3 |

### Confident misroutes (confidence at least 0.8): 1

- `sh_8fd983e4b981c2d6_0` single_hop predicted multi_hop at 0.921, routed hybrid

### Other misroutes: 3

- `hp_5aba5e2555429955dce3edf1` multi_hop predicted single_hop at 0.759, routed hybrid
- `hp_5a7e7c725542991319bc94be` multi_hop predicted single_hop at 0.624, routed hybrid
- `hp_5ac38ce255429939154137c2` comparison predicted single_hop at 0.465, routed hybrid
