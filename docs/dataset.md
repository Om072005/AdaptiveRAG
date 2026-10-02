# The dataset

Every question, passage and score in AdaptiveRAG comes from one public dataset:
**HotpotQA v1, dev set, distractor setting**.

| | |
|---|---|
| Dataset | [HotpotQA](https://hotpotqa.github.io/) (Yang et al., EMNLP 2018), English Wikipedia |
| File | `hotpot_dev_distractor_v1.json`, 7,405 questions ([official download](http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json), or the same rows on [Hugging Face](https://huggingface.co/datasets/hotpotqa/hotpot_qa), config `distractor`, split `validation`) |
| Setting | Distractor: each question comes with 10 Wikipedia paragraphs, 2 that hold the answer and 8 that look relevant but do not |
| License | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |

## What we took from it

| | Questions sampled | Documents | Used for |
|---|---|---|---|
| Full corpus | 300 (seed 7) | 2,957 (4,277 sentence chunks) | everything on the page and in the README |
| Mini corpus | 30 (seed 7) | 300 | quick benchmarks, such as chunking |

A corpus is every context paragraph of the sampled questions, so the distractors are searched too and retrieval
has to find the right 2 among them. The sample is fixed by its seed, so the same command always builds the same
corpus: [`adaptiverag/ingest/loader.py`](../adaptiverag/ingest/loader.py), with the ids in
[`data/corpus/full.json`](../data/corpus/full.json) and [`data/corpus/mini.json`](../data/corpus/mini.json).

## The questions we score

150 questions from inside the full corpus, each checked by a named person:

| Split | Questions | Multi hop | Comparison | Single hop |
|---|---|---|---|---|
| `dev` | 100 | 38 | 29 | 33 |
| `test` | 50 | 20 | 13 | 17 |

Multi hop and comparison questions are HotpotQA's own (its `bridge` and `comparison` types). HotpotQA has no
single hop questions, so those are written from one corpus paragraph by the large model and then checked by hand.
Files: [`data/gold/dev.jsonl`](../data/gold/dev.jsonl), [`data/gold/test.jsonl`](../data/gold/test.jsonl); how
they are scored is in the [evaluation protocol](eval-protocol.md).
