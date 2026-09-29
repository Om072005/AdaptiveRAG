# Classifier comparison, dev split (20260930-0112-dev)

Run `20260930-0112-dev` · 2026-09-30T01:12:51+05:30 · git `b71e368c08c7` · config `a431d54de69a`

100 dev questions (33 single_hop, 38 multi_hop, 29 comparison), each labelled by every method. Rules and the logistic regression are trained on data/router/train.jsonl only. Latency is the classifier alone: the logistic regression reuses the query embedding retrieval computes anyway, and a cached model call keeps the latency recorded when it was first made. Cost is at list price.

| Method | Macro F1 | F1 single_hop | F1 multi_hop | F1 comparison | Cost per query USD | p50 ms |
|---|---|---|---|---|---|---|
| rules | 0.8014 | 0.7632 | 0.6957 | 0.9455 | 0.00000000 | 0 |
| logreg | 0.8773 | 0.8312 | 0.8182 | 0.9825 | 0.00000000 | 0 |
| llm | 0.8099 | 0.7619 | 0.7419 | 0.9259 | 0.00005737 | 459 |

rules, gold as rows, predicted as columns:

| | single_hop | multi_hop | comparison |
|---|---|---|---|
| single_hop | 29 | 4 | 0 |
| multi_hop | 14 | 24 | 0 |
| comparison | 0 | 3 | 26 |

logreg, gold as rows, predicted as columns:

| | single_hop | multi_hop | comparison |
|---|---|---|---|
| single_hop | 32 | 1 | 0 |
| multi_hop | 11 | 27 | 0 |
| comparison | 1 | 0 | 28 |

llm, gold as rows, predicted as columns:

| | single_hop | multi_hop | comparison |
|---|---|---|---|
| single_hop | 32 | 1 | 0 |
| multi_hop | 15 | 23 | 0 |
| comparison | 4 | 0 | 25 |
