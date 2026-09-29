# Evaluation protocol

How every eval run is scored, and the rules that keep the numbers honest. Results live in
`docs/results/`; only runs listed in `docs/results/pinned.toml` are quoted in the README or on the page.

## Gold set

150 HotpotQA questions from inside the full corpus: 100 `dev`, 50 `test`
(`data/gold/dev.jsonl`, `data/gold/test.jsonl`, format in the contracts). Types: `multi_hop`
(HotpotQA bridge), `comparison` (HotpotQA comparison) and `single_hop` (generated from one corpus
paragraph by the `large` role, the only model call in the project that runs above temperature 0).
Every item is checked by a named person (`python -m adaptiverag.eval.gold verify`): the question is
answerable from the listed sentences, the answer is the shortest correct span, the type is right.
Wrong items are fixed or replaced, never silently dropped.

## Non judge metrics (computed first, need no model)

| Metric | Definition |
|---|---|
| EM | normalized answer equals the normalized gold answer (HotpotQA official normalization: lower case, no punctuation, no articles) |
| F1 | token F1 between the normalized answers; a yes/no answer scores 0 unless both sides match, as in the official script |
| recall@k | share of the gold supporting titles found among the top k hits (`vector.k` in `config/router.toml`) |
| MRR | 1 / position of the first hit from a supporting title, 0 if none |
| sentence precision | share of retrieved characters that fall inside gold supporting sentences; overlapping chunks count their shared characters twice |

## Judge (computed second)

The `judge` role (Gemini) is a different model family from both generators (`gpt-oss:20b` and
`qwen3.6:35b-a3b`, run locally, D16) and the only model called through a hosted API. It sees the question, the numbered context blocks the generator saw (plus graph
facts with their block numbers) and the answer text. It does not see the gold answer: EM and F1
already measure that. Temperature 0, JSON output.

Metric definitions follow the README: faithfulness is about the answer against the context,
relevance is about the retrieved context against the question, completeness is about the answer
against every part of the question.

Rubric (the prompt uses this text exactly):

<!-- rubric:start -->
```text
Score each metric from 1 to 5.

faithfulness: is every claim in the answer supported by the context?
5 every claim is stated in the context
4 all claims supported, one needs a small inference the context clearly allows
3 the main answer is supported, but one side claim is not in the context
2 the main answer is not supported by the context, some side claims are
1 the answer contradicts the context or is not grounded in it at all
If the answer says "not enough context", score 5 when the context really lacks the answer, else 1.

relevance: are the retrieved context blocks actually about the question?
5 every block is about the question's entities and what it asks
4 most blocks are on topic, one or two are off topic
3 about half the blocks are on topic
2 one block is on topic, the rest are not
1 no block is about the question

completeness: does the answer cover every part of the question?
5 every part is answered (both sides of a comparison, every hop of a chain)
4 every part is answered, one only vaguely
3 one part of a multi part question is missing
2 most parts are missing
1 the answer does not address the question
A single part question answered fully scores 5, whether or not the answer is correct.
```
<!-- rubric:end -->

A score s from 1 to 5 is stored as (s - 1) / 4, so 1 maps to 0.0 and 5 to 1.0. A reply that is not
valid JSON with three integer scores from 1 to 5 is retried once. If the retry fails too, the
question is stored as a judge failure, never as a score, and reports count failures separately.

A judged answer is flagged for review when any of the three scores is below `judge.flag_below` in
`config/router.toml`; it then enters `review_queue` with status `open`.

The judge's free quota is 20 calls a day per key, so judged runs score a fixed subset: the 40 dev questions in
`data/gold/judge_subset.toml` (13 single hop, 15 multi hop, 12 comparison, drawn per type in proportion to the
split with seed 7). Every judged variant scores the same 40, so judge metrics compare across variants; EM, F1,
recall@k and MRR still come from runs over all 100 dev questions. A judged run is
`eval.run --split dev --questions data/gold/judge_subset.toml --judge ...`; its answers are cache hits of the
full run with the same config.

## Stated limitation and mitigations

LLM-as-judge is an imperfect proxy and partly circular. We (1) use a different, stronger model family
as judge, (2) score a manual sample of 20 answers per pinned run by hand and report judge vs manual
agreement, (3) read runs directionally: `python -m adaptiverag.eval.report <run> --vs <previous run>`
prints the change per metric and per type.

## Run hygiene

- Every run stores git sha, dirty flag, config hash, split, mode and variant.
- Thresholds are tuned on `dev` only. `test` is locked: `eval.run --split test` refuses unless
  `ALLOW_TEST=1`, and each pinned variant runs on it once, on the frozen commit.
- `--pin` needs a clean working tree and the Neon `main` database.
- Costs are list price and latencies come from the original call, even on a cache hit, so a cached
  rerun never looks cheaper or faster than it was.
- A run stopped by a provider rate limit is continued with `--resume <run_id>`, never restarted.
