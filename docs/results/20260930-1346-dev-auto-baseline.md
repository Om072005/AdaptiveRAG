# 20260930-1346-dev-auto-baseline

split `dev` · mode `auto` · variant `baseline` · git `4e370b935ce4` · config `d67a90a95faa` · 100 of 100 questions stored

Compared with: `20260930-1346-dev-auto-selector`

| metric | value | change |
|---|---|---|
| em | 0.800 | +0.000 |
| f1 | 0.848 | +0.000 |
| recall_at_k | 0.945 | +0.000 |
| mrr | 1.000 | +0.000 |
| sp_precision | 0.081 | +0.000 |
| faithfulness | 0.975 | +0.000 |
| relevance | 0.450 | +0.000 |
| completeness | 1.000 | +0.000 |
| cost_per_query_usd | 0.00083095 | +0.00000000 |
| p50_ms | 7511 | -60 |
| p95_ms | 58960 | +47 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 33 | 0.939 | 0.952 | 1.000 | 1.000 | +0.000 |
| multi_hop | 38 | 0.605 | 0.702 | 0.855 | 0.941 | +0.000 |
| comparison | 29 | 0.897 | 0.920 | 1.000 | 0.991 | +0.000 |

## Router (macro F1 0.877)

Routes taken: vector 11, graph 0, hybrid 89

Fallbacks: 0 of 100 questions

| gold, predicted | single_hop | multi_hop | comparison |
|---|---|---|---|
| single_hop | 32 | 1 | 0 |
| multi_hop | 11 | 27 | 0 |
| comparison | 1 | 0 | 28 |

### Confident misroutes (confidence at least 0.8): 2

- `sh_8fd983e4b981c2d6_0` single_hop predicted multi_hop at 0.921, routed hybrid
- `hp_5a81ad9855429903bc27b9a3` multi_hop predicted single_hop at 0.842, routed hybrid

### Other misroutes: 11

- `hp_5a887293554299206df2b273` multi_hop predicted single_hop at 0.791, routed hybrid
- `hp_5aba5e2555429955dce3edf1` multi_hop predicted single_hop at 0.759, routed hybrid
- `hp_5ae180d855429901ffe4aecc` multi_hop predicted single_hop at 0.675, routed hybrid
- `hp_5ae326d85542991a06ce9938` multi_hop predicted single_hop at 0.659, routed hybrid
- `hp_5addda9b5542992200553b5b` multi_hop predicted single_hop at 0.642, routed hybrid
- `hp_5a7e7c725542991319bc94be` multi_hop predicted single_hop at 0.624, routed hybrid
- `hp_5ab5ee055542997d4ad1f259` multi_hop predicted single_hop at 0.565, routed hybrid
- `hp_5a845e9055429933447460ec` multi_hop predicted single_hop at 0.551, routed hybrid
- `hp_5ab23d8a55429970612095c9` multi_hop predicted single_hop at 0.517, routed hybrid
- `hp_5a865bbf5542991e77181615` multi_hop predicted single_hop at 0.515, routed hybrid
- `hp_5ac38ce255429939154137c2` comparison predicted single_hop at 0.465, routed hybrid
