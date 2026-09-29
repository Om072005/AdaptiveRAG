# Chunking experiment, mini corpus (20260930-0113-mini)

Run `20260930-0113-mini` · 2026-09-30T01:13:22+05:30 · git `48e20e914daf` · config `cb955bd52cb9`

27 HotpotQA questions of the mini corpus (3 left out because they are in the gold test split), top 8 chunks per strategy by exact cosine search. Fixed and semantic chunks exist only for the mini corpus's 300 documents and the full corpus is sentence chunks only, so every strategy here searches the same 300 documents. This is a small sample: one question moves recall@k by 0.037. Verdicts compare recall@k with the serving strategy (sentence) by a paired bootstrap over questions (2000 resamples, seed 7); the config change is a separate, reviewed step.

| Strategy | Params | Chunks | Precision | Context retention | Recall@k | MRR | Verdict |
|---|---|---|---|---|---|---|---|
| fixed | 64 words, overlap 16 | 635 | 0.131 | 0.899 | 0.963 | 0.957 | too close to call against sentence on this sample |
| sentence | up to 96 words | 445 | 0.105 | 0.951 | 0.963 | 0.957 | serving now |
| semantic | split above percentile 90 | 532 | 0.115 | 0.895 | 0.944 | 0.981 | too close to call against sentence on this sample |
