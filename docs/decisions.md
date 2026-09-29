# Decision log

The full log (decisions D1 to D15 with alternatives and reasons) is written on D3. This file starts with the
provider facts we checked on D1, because every cost and latency number later depends on them.

## Models, list prices and free tier limits (checked 2026-09-29)

Costs are always computed from the paid tier list price in `config/models.toml`, even while we run on free
tiers, so a number does not depend on whose key ran the query.

| Role | Provider | Model id | In / out, USD per 1M tokens | Listed by `/models` |
|---|---|---|---|---|
| small, classify | Groq | `openai/gpt-oss-20b` | 0.075 / 0.30 | yes |
| large | Groq | `openai/gpt-oss-120b` | 0.15 / 0.60 | yes |
| extract | Gemini | `gemini-3.5-flash-lite` | 0.30 / 2.50 | yes |
| judge | Gemini | `gemini-3.8-flash` | 0.75 / 3.75, introductory until 2026-12-31, then 1.50 / 7.50 | yes |
| embed | Gemini | `gemini-embedding-001` | 0.15 input | yes |

Sources: https://console.groq.com/docs/models, https://ai.google.dev/gemini-api/docs/pricing,
https://developers.googleblog.com/gemini-embedding-available-gemini-api/

Notes from the provider docs:

- Groq lists `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` as Enterprise only, which is why the
  generators are the two GPT-OSS models. Both accept `reasoning_effort` low, medium or high.
- `gemini-2.5-flash-lite` is still listed by `/models` but every call returns 404 "no longer available to new
  users", so extraction uses the fallback the plan named, `gemini-3.5-flash-lite`. Thinking cannot be turned off
  on 3.x models, so extraction runs at `reasoning_effort = "minimal"`.
- Gemini's OpenAI compatible usage block leaves thinking tokens out of `completion_tokens` but counts them in
  `total_tokens` (a low effort call reported 2 completion and 68 total tokens for an 18 token prompt). The
  gateway therefore bills output as `total_tokens - prompt_tokens` when that is larger.
- `gemini-embedding-001` is marked legacy but stable. Its successor `gemini-embedding-2` costs 0.20 and its
  vectors are not comparable with 001, so we stay on 001 for the whole project. At 768 dimensions 001 needs
  L2 normalization on our side.
- On the OpenAI compatible Gemini endpoint, `reasoning_effort = "none"` turns thinking off for 2.5 models;
  3.x Flash accepts low. Embeddings accept `dimensions = 768` there (checked
  2026-09-29), return no usage block, and are not unit length, so the gateway normalizes them.

### Free tier limits

| Provider | Model | Requests per minute | Requests per day | Tokens per minute | Tokens per day |
|---|---|---|---|---|---|
| Groq (per organization) | `openai/gpt-oss-20b` | 30 | 1,000 | 8,000 | 200,000 |
| Groq (per organization) | `openai/gpt-oss-120b` | 30 | 1,000 | 8,000 | 200,000 |

Source: https://console.groq.com/docs/rate-limits. Gemini limits are set per project and AI Studio shows
them per model only once a model has been called; they are added here after the first gateway calls on D2.

What this means for us: at about 3k tokens per question, 8k tokens per minute allows two or three large model
questions a minute per organization. Eval runs will be throttled, which is why latency counts only the
successful attempt and backoff goes to `throttle_wait_ms`.
