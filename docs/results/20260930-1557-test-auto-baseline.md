# 20260930-1557-test-auto-baseline

split `test` · mode `auto` · variant `baseline` · git `b08eb9614364` · config `e52cef8141c0` · 50 of 50 questions stored

Compared with: no earlier comparable run

| metric | value | change |
|---|---|---|
| em | 0.720 |  |
| f1 | 0.811 |  |
| recall_at_k | 0.970 |  |
| mrr | 0.990 |  |
| sp_precision | 0.087 |  |
| faithfulness | 0.935 |  |
| relevance | 0.470 |  |
| completeness | 0.970 |  |
| cost_per_query_usd | 0.00105475 |  |
| p50_ms | 9522 |  |
| p95_ms | 14925 |  |

| type | n | em | f1 | recall_at_k | faithfulness | f1 change |
|---|---|---|---|---|---|---|
| single_hop | 17 | 0.824 | 0.874 | 1.000 | 1.000 |  |
| multi_hop | 20 | 0.600 | 0.744 | 0.925 | 0.863 |  |
| comparison | 13 | 0.769 | 0.831 | 1.000 | 0.962 |  |

## Router (macro F1 0.842)

Routes taken: vector 4, graph 0, hybrid 46

Fallbacks: 0 of 50 questions

| gold, predicted | single_hop | multi_hop | comparison |
|---|---|---|---|
| single_hop | 14 | 2 | 1 |
| multi_hop | 2 | 15 | 3 |
| comparison | 0 | 0 | 13 |

### Confident misroutes (confidence at least 0.8): 0


### Other misroutes: 8

- `sh_91c9dc978e62c013_0` single_hop predicted multi_hop at 0.756, routed hybrid
- `hp_5adebc51554299728e26c799` multi_hop predicted comparison at 0.728, routed hybrid
- `hp_5a80db5055429938b6142218` multi_hop predicted comparison at 0.700, routed hybrid
- `hp_5abe2b0155429976d4830a83` multi_hop predicted comparison at 0.560, routed hybrid
- `sh_8561b9741de9054e_2` single_hop predicted multi_hop at 0.542, routed hybrid
- `hp_5a832a625542990548d0b1b4` multi_hop predicted single_hop at 0.536, routed hybrid
- `hp_5ab9fe1255429939ce03dc40` multi_hop predicted single_hop at 0.510, routed hybrid
- `sh_93a2dca4c1276f82_0` single_hop predicted comparison at 0.392, routed hybrid
