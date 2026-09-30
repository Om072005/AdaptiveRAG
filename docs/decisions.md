# Decision log

Each decision: what we chose, what we did not, and why. The README table "Design decisions & tradeoffs" keeps
its five rows; everything we decided while building goes here. New entries go at the bottom of their section.

## Architecture and data

**D1 One Postgres (Neon) for chunks, vectors, the graph, traces and evals.** Not Neo4j plus a vector database
plus a trace store. The README graph schema is an entity relationship diagram, so it maps to tables, and a
foreign key makes provenance impossible to skip: `relations.chunk_id` is `not null` and has no cascade.
Traversal is depth two with a fan out cap, a few indexed queries we write ourselves. Quality per unit cost is
one join between eval results and trace costs. Neon branches give every member a copy of shared data in
seconds. We would move the graph to Neo4j if it passed about 100k edges or needed depth over three.

**D2 pgvector HNSW serves; our own HNSW and a flat index are for the benchmark only.** A static page and a
local API should not load a Python index on every start. The benchmark still measures our HNSW against flat
and against pgvector, and the README says plainly that the library index serves.

**D3 HotpotQA dev (distractor) as corpus and gold set.** It ships gold answers and sentence level supporting
facts, so EM, F1 and supporting title recall do not depend on a model judge. Question types map onto the
router labels. Known weakness: paragraphs are short Wikipedia intros, so chunking strategies differ less than
on long documents, and the chunking table says so.

**D6 No RAG framework.** `scripts/check.sh` fails on LangChain, LlamaIndex or Haystack imports, and on sklearn,
scipy or torch, because retrieval, routing, merge and the classifier are written by us.

**D12 Every model call is cached in Postgres.** Keyed by a hash of the exact request (model, messages or input,
every parameter). Reruns are free and reproducible, and a hit returns the original tokens and latency, so a
cached rerun never makes a route look cheaper or faster. Embeddings are cached per text, so a partly done
ingest resumes without paying twice.

**D13 The public page is static and replays recorded runs.** It never calls a model or the database, so a
shared link cannot break or run up a bill. Vercel receives only `web/` (`.vercelignore`), the project framework
is set to Other, and there are no functions. The full system runs locally for the team.

**D14 Evaluation hygiene.** Tune on dev only; the test split is locked behind `ALLOW_TEST=1` and run once per
pinned variant on D13; every run records git sha, dirty flag and config hash; the README quotes pinned runs only.

## Models and routing

**D4 Groq GPT-OSS generates, Gemini extracts and judges (generation and extraction moved local in D16).** Small and classify: `gpt-oss-20b`; large:
`gpt-oss-120b`; extract: Gemini Flash-Lite; judge: Gemini Flash. Embeddings started on `gemini-embedding-001` at 768
dimensions and moved to a local model on 2026-09-30 (D5). The judge is a different family from the generator, as the README asks. One OpenAI compatible
gateway means a provider swap is a config change.

**D5 Embeddings: a local open model, one query embedding reused.** Changed on 2026-09-30 from Gemini's
`gemini-embedding-001` to `nomic-embed-text` (v1.5, 768 dimensions) served by Ollama on the lead's GPU (an RTX
2060 SUPER, 8 GB). Why: Gemini's free tier embeds 1,000 texts a day per key, and the corpus, the chunking
experiment, the graph and the classifier needed about 15,000, several days of four keys; the team chose to stay on
free tiers. Measured before switching: the full corpus (4,277 sentence chunks) embeds in 29 s, and on the 100 dev
gold questions supporting title recall@8 is 0.945 (every supporting title in the top 8 for 89 of them), MRR 1.0.
The model embeds questions and searched texts with different prefixes (`search_query: `, `search_document: `),
set in `config/models.toml`; `llm.embed(kind=...)` picks one. Cost is recorded as 0 because it runs locally.
We did not run a side by side comparison with Gemini on the same questions; the switch rests on the local
measurement above. What we lose: anyone
embedding a new question needs Ollama running; every corpus, gold, training and replay question is cached on Neon
`main`, so eval runs do not.

**D5b One query embedding, reused.** Computed once per question and used by vector search, the classifier,
entity linking, traversal scoring and MMR.

**D7 Three classifiers compared, logistic regression by default.** Rules on cue features, numpy logistic
regression on the query embedding plus cues, and a few shot LLM. The default reuses the embedding we already
paid for, so it adds almost no cost, and its softmax gives a real classifier confidence.

**D8 Hybrid is reciprocal rank fusion, then MMR.** No score calibration is needed between cosine and path
scores; MMR stops near duplicate chunks filling the context. An LLM re-rank exists behind a flag, off by default.

**D9 Entity resolution with a person guard.** Merge on normalized name or embedding similarity, but two PERSON
entities also need a shared neighbour or the same source document. That guards the README's most expected
failure: merging two people who share a name.

**D10 Traversal is BFS, depth two, fan out 25.** Edge score is extraction confidence times relation similarity
to the question; path score is the product. Bounded cost per query, and every edge keeps its chunk.

**D11 Classifier confidence and answer confidence are separate columns.** Answer confidence is citation
coverage plus retrieval strength, with weights in `config/router.toml`. A confidently classified question can
still get a badly grounded answer; logging both lets us show when.

**D15 Free tiers, one account per member.** Limits are per Groq organization and per Gemini project. Latency
counts only the successful attempt; backoff after a 429 goes to `wait_ms` and `throttle_wait_ms`.

**D16 Every model but the judge runs locally (2026-09-30).** Small, classify and extract: `gpt-oss:20b`, the same
open weights Groq served; large: `qwen3.6:35b-a3b`, a mixture of experts with 3B active parameters, the largest
model that fits the lead's 8 GB GPU plus 32 GB RAM (`gpt-oss-120b` needs about 65 GB); both through Ollama. The judge
stays on Gemini (`gemini-3.8-flash`), a different family from both generators. Why: the free tiers (200,000
tokens a day per Groq organization, 500 extraction calls a day per Gemini project) set the pace of every eval
run, and the team chose to stay free. Costs are the OpenRouter list price of the same weights (checked
2026-09-30: `gpt-oss-20b` 0.018 / 0.09, `qwen3.6-35b-a3b` 0.15 / 1.00 USD per million tokens), so the economics
tables still compare routes and model sizes. Latency is measured on that one machine (i5-13400F, RTX 2060 SUPER),
not on a hosted provider. What changes: the large model is now a different family from the small one, and the
graph is re-extracted by the local model; every run before this decision is superseded.

**D17 Relational questions route to hybrid, and the small model answers everything (2026-09-30).** The first
full dev runs on the local models (rented 2x RTX 5090, commit `8bea8c7`, Neon main) showed the graph route
losing to hybrid on the questions it was built for: multi hop F1 0.168 on graph against 0.671 on hybrid, and
forced graph 0.512 overall against hybrid 0.844 and vector 0.776 (`20260930-0634-dev-graph-server`,
`20260930-0659-dev-hybrid-server`, `20260930-0620-dev-vector-server`). Auto mode, which sent relational
questions to graph, scored 0.568 (`20260930-0724-dev-auto-server`) with a router at macro F1 0.877, so the
routes, not the classifier, were the loss. `[policy] relational_route = "hybrid"` now sends multi hop and
comparison questions to hybrid, where the graph still contributes its paths through rank fusion; the graph
route stays in the code, the forced graph runs and the decision table, and one config line restores it.
Replayed offline with `eval.tune` (no live run yet), the new policy scores 0.824 at the old thresholds and 0.844 at
`classifier.min_confidence = 0.85`, which keeps the 11 most confident single hop questions on the cheaper vector
route. The selector's large model rules are emptied (superseded in part by D20: under D17's own routes the large model
is ahead): under the pre-D17 routes (62 of 100 questions on hybrid, 37 on graph) always-small matched the selector and
always-large
(F1 0.638 against 0.636 and 0.636) at USD 0.000025 against 0.0015 per query and 40% of the p50 latency
(`20260930-0754-dev-auto-always-small`, `20260930-0738-dev-auto-selector`,
`20260930-0810-dev-auto-always-large`). The context length rule stays; no dev question reached it. Latency in
runs after this decision comes from the server for model calls answered from the cache and from the lead's
PC for new calls and database time; each trace records which calls were cached.

**D18 Entities merge by name only (2026-09-30).** 100 merge decisions sampled from the local graph and labelled
against both source passages (labelled by the lead, `data/graph/merge_labels.jsonl` at `d1c3727`) put the
name rule at precision 0.96 (50 of 52) and the embedding rule at 0.125 (6 of 48). The correct embedding merges
scored cosine 0.90 to 0.97 and the wrong ones 0.88 to 0.94, so no threshold separates them; 28 of the 42 wrong
ones joined two different dates ("November 1, 1961" with "November 19, 1957"), others joined Cork City and Cork
County Council or two different Gundam series. `resolve.embed_merge = false` turns the rule off and keeps it in
code. The graph on Neon main was rebuilt from the cached extraction: 7,073 entities (was 6,542) and 6,567
relations; a fresh sample of 100 decisions labelled the same way scores 0.91 (graph report). What it costs:
the six correct embedding merges in the first sample (Paris and "Paris, France", two names of the NCTA) now stay
two entities, which the alias lookup and the vector side of hybrid still reach.

**D19 The judge is Gemma 4 31B on the Gemini API, and judged runs score all 100 dev questions (2026-09-30).**
`gemini-3.8-flash` allows 20 calls a day per key, which would have taken weeks for the judged runs. Mistral Large 3
was the preferred replacement, but the free Mistral tier serves only the Ministral models (Large answers 403,
Medium and Small have a quota of 0 requests a minute) and card payment failed. `gemma-4-31b-it` runs on the same
free Gemini key with a far larger quota; it is a different family from both generators (GPT-OSS and Qwen) and larger
than the small model's active parameters. It rejects `response_format` (a 500), so the judge role sets
`json_mode = false` and `judge.parse_scores` reads the JSON after its thought block and inside a code fence. A call
takes about 40 seconds and returns an occasional 500, which stops a run for `--resume`. Cost numbers use the
OpenRouter list price of the same weights (0.08 / 0.30 USD per million tokens, checked 2026-09-30); the free tier
bills nothing. With the quota no longer binding, a judged run scores the whole dev split, so every results row
takes F1 and faithfulness from one run (this replaces the 40 question subset of the eval protocol). Every judged
run uses this one judge; mixing judges across runs would make faithfulness incomparable.

**D20 The large model answers questions classified multi hop or comparison (2026-09-30).** D17 emptied the
selector's rules because always-small had matched always-large, but that comparison ran under the pre-D17 routes.
Under D17's routes the pinned runs disagree: always-small scores dev F1 0.821 and always-large 0.859
(`20260930-1524-dev-auto-always-small`, `20260930-1538-dev-auto-always-large`), with the large model ahead on every
type (single hop 0.952 to 0.982, multi hop 0.661 to 0.706, comparison 0.882 to 0.920). A paired bootstrap (2000
resamples, seed 7) puts always-large at +0.038 F1, 95% interval 0.009 to 0.078. Replayed offline on the same two
runs, sending only the questions the classifier labels multi hop or comparison to the large model scores 0.848
(+0.027, interval 0.002 to 0.059) at USD 0.00083 per query, against 0.000027 for always-small and 0.00139 for
always-large. `select.large_if_labels = ["multi_hop", "comparison"]` restores that rule; the route rule stays
empty because under D17 nearly every question is on hybrid. The live selector run confirms or refutes the replay,
and the faithfulness floor decides the quality per cost table. Latency of the large model is not compared: on the
lead's 8 GB GPU it runs partly on the CPU (p50 35 s), which says nothing about the model.

**D21 The judge runs on our own GPU server (2026-09-30).** A few hours into D19's judged runs, every model on
the free Gemini API answered 500 or 503 (Gemma 4 31B and 26B "Internal error", gemini-3.8-flash "high demand"),
and judging stalled. Gemma 4 has open weights, so the judge moved to `gemma4:31b` on Ollama (Q4_K_M, about 20 GB)
on a rented GPU server, next to the two generators. It is the same model family and size as D19, quantized; to keep
every score from one judge, every judged run is made on the server, and the about 180 answers the API had scored
belong to runs that are not pinned. The judge's cost stays the OpenRouter list price of the weights. The same
server also answers the test split (D13), so the test runs' model latency is measured on that one machine.

**D22 The judge gets 4,096 output tokens, and failed verdicts are judged again (2026-09-30).** Gemma 4 31B reasons
before it writes its scores. With 1,024 output tokens, 6 to 9 of every 100 dev verdicts in the judged runs at
`4e370b9` came back empty (41) or cut off inside the JSON (13), so those answers had no faithfulness score. The
server session held the test split rather than run it with the same fault. `judge.max_tokens = 4096` in
`config/router.toml` gives the judge room. The judge runs at temperature 0, so a call that finished inside 1,024
tokens produces the same verdict with the larger budget; only the calls that ran out change. `eval.rejudge`
rebuilds each unscored answer through the pipeline from the model cache (same answer, same context, so the same
judge prompt; the rebuilt trace is saved with source `cli`, which eval metrics never count) and stores the verdict on the run's own trace and
result row. The dev and replay runs keep their commit `4e370b9`; their late verdicts were made at the D22 commit,
and the test split runs at the D22 commit from the start.

**D23 Answer confidence stays as it is, and full width citation markers count (2026-09-30).** Calibrated
against the judge on the judged dev auto run (`20260930-1346-dev-auto-baseline`), answer confidence correlates
with faithfulness at 0.04; the best reweighting (`w_citation` 0.25, `w_retrieval` 0.75) reaches only 0.11, and the
suggested `answer.min_confidence` of 0.05 would stop flagging almost every answer. With a signal that weak, no
change is applied: the weights stay 0.5 / 0.5 and the bar 0.55, and the weakness is failure log 5. One cause
was found and fixed: gpt-oss sometimes writes citation markers with full width brackets (`【1】`), which the
parser did not count, so correct, cited answers got citation coverage 0 and were flagged. `cite.py` now reads
them as `[1]`. Pinned runs keep the confidence they were scored with; the fix applies to answers made from now on.

**Manual check of the judge.** 20 answers of the test auto run (`20260930-1557-test-auto-baseline`), scored by
the lead against the same rubric without seeing the judge's scores: mean absolute gap 0.075 for faithfulness,
0.10 for relevance and 0.05 for completeness on the 0 to 1 scale; 95%, 90% and 95% of scores within one rubric
step; the same flag decision on 80% of answers.

## Decided while building (D1 to D3)

- **`aliases` primary key is `(surface_form, canonical_id)`**, not `surface_form` alone as the README draws it,
  so one surface form can point at two different people with the same name.
- **`schema_migrations` is created with `if not exists`** because the migration runner creates it before
  applying `0001`. Migration `0002` added `low_confidence` as an extraction reject reason.
- **Extraction moved to `gemini-3.5-flash-lite`** (see the provider notes below). It costs 0.30 / 2.50 per
  million tokens instead of 0.10 / 0.40, and thinking cannot be turned off.
- **Output tokens include hidden reasoning.** Gemini reports thinking only in `total_tokens`, so the gateway
  bills `max(completion_tokens, total_tokens - prompt_tokens)`.
- **Daily quotas stop a run at once.** A 429 that names a per day quota raises `RateLimited` without retrying,
  because waiting cannot clear it and refused retries still count. Per minute limits are waited out.
- **The call cap (4 per query) is checked before the provider is called**, so the fifth call costs nothing.
- **Empty retrieval answers "not enough context" without calling a model**, with answer confidence 0.
- **A citation written after the full stop belongs to that sentence.** Found in the first real `ask`, where it
  had halved citation coverage.
- **`sp_precision` takes chunk relative spans.** The eval run converts document offsets with
  `chunks.start_offset` and clips them to the chunk; the denominator counts overlapping chunks twice.
- **One shared database connection for reads on the query path**, so retrieval latency does not include a new
  TLS handshake to Neon on every query.
- **`POST /api/query` returns the response stored on the trace**, so a live answer and its replay are the same.
- **Split Gemini quotas instead of billing.** Enabling billing on the team's Gemini project failed on Google's
  side (`OR_BACR2_59`), so embedding the full corpus is spread over the four members' own keys, one slice each,
  into Neon `main`, and judged runs grow 20 questions per key per day with `--resume`.
- **Fixed and semantic chunks exist only for the mini corpus.** The chunking experiment compares the three
  strategies on the mini corpus's 300 documents and its 27 HotpotQA questions that are not in the gold test
  split. Neon `main` holds fixed and semantic chunks for those documents only; the full corpus (2,957 documents)
  is chunked and embedded as sentence chunks only. Serving searches sentence chunks through their own partial
  index, so the extra strategies change nothing it returns.
- **The page names members by GitHub username**, shows the lead's address as contact, and the repo is MIT.

## Decided while building the graph and router (D4 onward)

- **A second entity with the same name gets its own id.** Entity ids are `e_` plus 12 hex of
  sha1(type|normalized name). When the person guard keeps two same-name people apart, the second one's key
  also takes its anchor document id, so both keep stable ids and share one alias row per surface form.
- **Evidence the model quotes but that is not in its chunk keeps the whole chunk as its span.** Offsets are
  computed in code from the quote; when the quote is not found, the triple is kept with the chunk's own start
  and end instead of offsets that could point at the wrong text, and the graph report counts these as
  "evidence not located".
- **Extraction batches are recorded and reused.** Batches of four consecutive chunks shifted whenever a gold
  edit changed the dev scope, so cached requests stopped matching. `data/graph/extract_batches.jsonl` keeps
  every batch sent; a planned batch is sent unchanged (its chunks outside the scope are dropped after
  extraction) and only chunks no batch holds form new batches.
- **The graph dry run calls no model.** It merges by name only and says so, so checking the counts costs no
  embedding quota.
- **The rules classifier's confidence is measured, not a vote share.** A vote share gave a one cue question
  0.50, under `classifier.min_confidence`. The confidence is now the share of training questions with the
  same winning label and lead in votes that carry that label (`router/weights/rules.json`); the threshold
  did not change.

## Providers

### Models, list prices and free tier limits (checked 2026-09-29)

Costs are always computed from the paid tier list price in `config/models.toml`, even while we run on free
tiers, so a number does not depend on whose key ran the query.

| Role | Provider | Model id | In / out, USD per 1M tokens | Listed by `/models` |
|---|---|---|---|---|
| small, classify (until D16) | Groq | `openai/gpt-oss-20b` | 0.075 / 0.30 | yes |
| large (until D16) | Groq | `openai/gpt-oss-120b` | 0.15 / 0.60 | yes |
| small, classify, extract (from D16) | Ollama, local | `gpt-oss:20b` | 0.018 / 0.09 (OpenRouter list) | n/a |
| large (from D16) | Ollama, local | `qwen3.6:35b-a3b` | 0.15 / 1.00 (OpenRouter list) | n/a |
| extract (until D16) | Gemini | `gemini-3.5-flash-lite` | 0.30 / 2.50 | yes |
| judge | Gemini | `gemini-3.8-flash` | 0.75 / 3.75, introductory until 2026-12-31, then 1.50 / 7.50 | yes |
| embed (until 2026-09-30, see D5) | Gemini | `gemini-embedding-001` | 0.15 input | yes |
| embed (from 2026-09-30) | Ollama, local | `nomic-embed-text` v1.5 | 0, local compute | n/a |

Sources: https://console.groq.com/docs/models, https://ai.google.dev/gemini-api/docs/pricing,
https://developers.googleblog.com/gemini-embedding-available-gemini-api/

Notes from the provider docs:

- Groq lists `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` as Enterprise only, which is why the
  generators are the two GPT-OSS models. Both accept `reasoning_effort` low, medium or high.
- `gemini-2.5-flash-lite` is still listed by `/models` but every call returns 404 "no longer available to new
  users", so extraction uses the fallback the plan named, `gemini-3.5-flash-lite`. Thinking cannot be turned off
  on 3.x models, so extraction runs at `reasoning_effort = "minimal"`.
- Gemini's OpenAI compatible usage block leaves thinking tokens out of `completion_tokens` but counts them in
  `total_tokens` (a low effort call reported 2 completion and 68 total tokens for an 18 token prompt).
- `gemini-embedding-001` is marked legacy but stable. Its successor `gemini-embedding-2` costs 0.20 and its
  vectors are not comparable with 001, so we stay on 001 for the whole project. At 768 dimensions 001 needs
  L2 normalization on our side.
- On the OpenAI compatible Gemini endpoint, `reasoning_effort = "none"` turns thinking off for 2.5 models;
  3.x Flash accepts low. Embeddings accept `dimensions = 768` there (checked 2026-09-29), return no usage
  block, and are not unit length, so the gateway normalizes them.

### Free tier limits

| Provider | Model | Requests per minute | Requests per day | Tokens per minute | Tokens per day |
|---|---|---|---|---|---|
| Groq (per organization) | `openai/gpt-oss-20b` | 30 | 1,000 | 8,000 | 200,000 |
| Groq (per organization) | `openai/gpt-oss-120b` | 30 | 1,000 | 8,000 | 200,000 |
| Gemini (per project) | `gemini-embedding-001` | 100 texts | 1,000 texts | 30,000 | |
| Gemini (per project) | `gemini-3.8-flash` (judge) | 5 | 20 | 250,000 | |
| Gemini (per project) | `gemini-3.5-flash-lite` (extract) | 15 | 500 | 250,000 | |

Sources: https://console.groq.com/docs/rate-limits and the AI Studio rate limit page of our project
(2026-09-29). Gemini counts every embedded text as a request, and its daily quotas reset at midnight Pacific.

What this means for us: at about 3k tokens per question, 8k tokens per minute allows two or three large model
questions a minute per Groq organization, and one Gemini project embeds at most 1,000 texts a day. Eval runs
will be throttled, which is why latency counts only the successful attempt and backoff goes to
`throttle_wait_ms`.
