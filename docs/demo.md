# Run the showcase yourself

Everything below runs from a fresh `git clone` on your own machine: no account, no API key, and no network once
the models are downloaded. The database is Postgres 16 with pgvector, shipped as a Python package and kept in
`.demo/` inside the clone. The corpus is in the repo as text (`data/demo/corpus.jsonl.gz`, 1.6 MB), and your own
Ollama embeds it once.

## What you need

| | Needed for | Size |
|---|---|---|
| Python 3.12 and [uv](https://docs.astral.sh/uv/) | everything | |
| [Ollama](https://ollama.com) with `nomic-embed-text` and `gpt-oss:20b` | every question | 0.3 GB + 14 GB |
| `qwen3.6:35b-a3b` in Ollama (optional) | multi hop and comparison questions on the large model, as recorded | 22 GB |
| `gemma4:31b` in Ollama (optional) | the judge button on the local page | 20 GB |
| Node 20 or newer | the local page | |

Without the large model, questions the selector would send to it are answered by the small one, and the trace
says so (`small:qwen3.6:35b-a3b not installed (large:label multi_hop)`). Without the judge, the judge button says
which model to pull. An NVIDIA GPU with 8 GB is enough; Ollama splits a model between GPU and CPU when it does not
fit, and every answer prints where it ran (`42% GPU, 58% CPU`).

## Setup, once

```bash
git clone https://github.com/Om072005/AdaptiveRAG.git && cd AdaptiveRAG
uv sync
ollama pull nomic-embed-text && ollama pull gpt-oss:20b
uv run python -m adaptiverag demo setup     # database + corpus, then 17,917 embeddings by your Ollama
uv run python -m adaptiverag demo check     # database, models, GPU, and warms the small model
```

`demo setup` creates the database, applies the migrations and loads 2,957 documents, 4,277 chunks, 7,073
entities, 7,106 aliases and 6,567 relations, then embeds every chunk, entity and relation. It took 2 minutes on
an RTX 2060 SUPER; on a CPU only machine expect longer. A stopped setup resumes where it stopped.

## The three parts

**1. A live question in the terminal.** Each step prints the moment it ends: the question's embedding, the
classifier's label and how sure it is, the entities found in the question, the route and why, every chunk and
graph path retrieved, the model chosen and why. Then the model's own reasoning and its answer stream as they are
written, followed by the tokens, where the model ran, the cost at list prices and the trace id.

```bash
uv run python -m adaptiverag ask "Who died first, Bryce Courtenay or Juan Carlos Onetti?"
uv run python -m adaptiverag ask "Who died first, Bryce Courtenay or Juan Carlos Onetti?" --mode graph   # force a route
```

**2. The page, live.** One command starts the API and the page with a live question box in chapter 03. The page
shows the same steps as they happen, the reasoning and the answer as they stream, then opens the answer in the
step by step view next to the recorded runs. The API's terminal prints every step too. Every question adds a
trace to your database.

```bash
uv run python -m adaptiverag demo page      # http://localhost:5173, stop with Ctrl+C
```

**3. A mini eval.** Three recorded questions (one single hop, one multi hop, one comparison) run live through the
served route, each printed step by step, then a table puts your route, F1 and cost next to the recorded run's.
Every model call is made live (the cache is skipped). Nothing is pinned; it refuses to run against the team's
Neon main. On the lead's machine (RTX 2060 SUPER, 8 GB) all three matched the recorded runs at F1 1.00: about
6 s for the single hop question on the small model, 50 and 59 s for the other two on the large one, which ran
23% on the GPU and 77% on the CPU.

```bash
uv run python -m adaptiverag demo eval      # --quiet for the table only
```

## How close to the recorded runs

The export re-embedded every text on the lead's machine and compared it with the stored vectors: all 4,277
chunk vectors came out the same, and the entity and relation vectors agree to a cosine of 0.99997 or better (the
two that did not are shipped in the file). On the 15 recorded questions the embedded database returns the same
vector hits and the same graph seeds as Neon main, and graph edge scores agree to about three decimals. The
embedded database has no `pg_trgm`, so alias matching runs in Python (`adaptiverag/stores/trgm.py`), a port of
pg_trgm's `word_similarity` checked against Postgres on 1.5 million alias and question pairs.

The models are the same weights, but a model's output depends on the hardware and the loaded context, so a live
answer can differ in wording from the recorded one. That is what the mini eval measures.

## Good to know

- The database keeps running after a command, so the next one starts in under a second. Stop it with
  `uv run python -m adaptiverag demo stop`; delete `.demo/` to start over.
- A model loads from disk the first time it answers, which takes minutes on a slow disk; that wait is reported as
  wait, not latency.
- Your team setup is untouched: with `DATABASE_URL` set in `.env`, every command uses that database instead.
  `DATABASE_URL=embedded` forces the demo database.
