# 20260930-0738-dev-auto-selector

split `dev` · mode `auto` · variant `selector` · git `8bea8c70734e` (dirty) · config `02c646b8c411` · 100 of 100 questions stored

Compared with: `20260930-0724-dev-auto-server`

| metric | value | change |
|---|---|---|
| em | 0.590 | +0.060 |
| f1 | 0.636 | +0.068 |
| recall_at_k | 0.785 | +0.035 |
| mrr | 0.825 | +0.037 |
| sp_precision | 0.100 | -0.021 |
| faithfulness | n/a | n/a |
| relevance | n/a | n/a |
| completeness | n/a | n/a |
| cost_per_query_usd | 0.00147130 | +0.00048887 |
| p50_ms | 7688 | +1136 |
| p95_ms | 12629 | +2387 |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 33 | 0.939 | 0.952 | 0.970 | n/a | +0.030 |
| multi_hop | 38 | 0.289 | 0.365 | 0.605 | n/a | +0.126 |
| comparison | 29 | 0.586 | 0.633 | 0.810 | n/a | +0.034 |

## Router (macro F1 0.877)

| gold, predicted | single_hop | multi_hop | comparison |
|---|---|---|---|
| single_hop | 32 | 1 | 0 |
| multi_hop | 11 | 27 | 0 |
| comparison | 1 | 0 | 28 |

### Confident misroutes (confidence at least 0.8): 2

- `sh_8fd983e4b981c2d6_0` single_hop predicted multi_hop at 0.921, routed graph
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
