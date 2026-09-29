-- Initial schema, exactly as the contract (01 section 1). schema_migrations uses "if not exists"
-- because the migration runner creates it before applying any file.

create extension if not exists vector;
create extension if not exists pg_trgm;

create table if not exists schema_migrations (version text primary key, applied_at timestamptz not null default now());

-- corpus ------------------------------------------------------------------
create table documents (
  doc_id      text primary key,               -- first 16 hex of sha1(source || '|' || title)
  source      text not null,                  -- 'hotpotqa-dev'
  title       text not null,                  -- Wikipedia title from HotpotQA
  text        text not null,                  -- normalized, sentences joined with one space
  sentences   jsonb not null,                 -- [[start, end], ...] char offsets per original sentence
  ingested_at timestamptz not null default now()
);
create table chunks (
  chunk_id     text primary key,              -- '{doc_id}:{strategy}:{ord}'
  doc_id       text not null references documents on delete cascade,
  strategy     text not null check (strategy in ('fixed','sentence','semantic')),
  ord          int  not null,
  start_offset int  not null,
  end_offset   int  not null,
  text         text not null,
  n_words      int  not null,
  embedding    vector(768)
);
create index chunks_doc on chunks (doc_id, strategy);
create index chunks_hnsw_fixed    on chunks using hnsw (embedding vector_cosine_ops) where strategy = 'fixed';
create index chunks_hnsw_sentence on chunks using hnsw (embedding vector_cosine_ops) where strategy = 'sentence';
create index chunks_hnsw_semantic on chunks using hnsw (embedding vector_cosine_ops) where strategy = 'semantic';

-- graph (README "Graph schema") -------------------------------------------
create table entities (
  canonical_id   text primary key,            -- 'e_' || first 12 hex of sha1(type || '|' || normalized name)
  canonical_name text not null,
  type           text not null check (type in ('PERSON','ORG','PLACE','WORK','EVENT','DATE','OTHER')),
  embedding      vector(768)
);
create table aliases (
  surface_form text not null,
  canonical_id text not null references entities on delete cascade,
  confidence   real not null,
  primary key (surface_form, canonical_id)    -- deviation from README: one surface form may point at two people with the same name
);
create index aliases_trgm on aliases using gin (lower(surface_form) gin_trgm_ops);
create table relations (
  rel_id                text primary key,     -- first 16 hex of sha1(subject_id|predicate|object_id|chunk_id)
  subject_id            text not null references entities,
  predicate             text not null,        -- lower snake case, e.g. 'founded', 'born_in'
  object_id             text not null references entities,
  chunk_id              text not null references chunks,     -- provenance, never null, no cascade
  doc_id                text not null references documents,
  evidence_start        int  not null,        -- char offsets in documents.text
  evidence_end          int  not null,
  extraction_confidence real not null,
  embedding             vector(768)           -- embedding of 'subject predicate object'
);
create index relations_subject on relations (subject_id);
create index relations_object  on relations (object_id);
create table extraction_rejects (
  id bigserial primary key, chunk_id text references chunks, raw jsonb not null,
  reason text not null check (reason in ('subject_not_in_source','object_not_in_source','bad_json','empty','self_loop')),
  created_at timestamptz not null default now()
);

-- LLM ledger + cache ------------------------------------------------------
create table llm_cache (
  key text primary key,                       -- sha256 of canonical json {model, messages, params}
  role text not null, model text not null, response jsonb not null,
  tokens_in int not null, tokens_out int not null, latency_ms int not null,   -- from the original, uncached call
  created_at timestamptz not null default now()
);

-- traces (README "Cost & latency accounting") -----------------------------
create table traces (
  trace_id uuid primary key,
  created_at timestamptz not null default now(),
  source text not null check (source in ('demo','eval','cli','example')),
  question text not null,
  mode text not null check (mode in ('auto','vector','graph','hybrid')),
  classifier_label text, classifier_confidence real, classifier_method text,
  route_initial text, route_taken text not null, fallbacks text[] not null default '{}',
  retrieval_latency_ms int, n_results int, top_score real, path_found boolean,
  model_selected text, select_reason text,
  tokens_in int not null default 0, tokens_out int not null default 0,
  classifier_cost_usd numeric(12,8) not null default 0,
  generation_cost_usd numeric(12,8) not null default 0,
  eval_cost_usd       numeric(12,8) not null default 0,
  total_cost_usd      numeric(12,8) not null default 0,
  total_latency_ms int,                        -- successful attempts only, never backoff waits
  throttle_wait_ms int not null default 0,      -- time spent waiting on 429 backoff (free tier), reported apart
  answer_confidence real, flagged boolean not null default false,
  cached boolean not null default false,       -- true if every LLM call on this trace was a cache hit
  git_sha text, git_dirty boolean, config_hash text,
  detail jsonb not null default '{}'           -- spans, hits, paths, answer, citations (the API response body)
);
create index traces_created on traces (created_at);
create index traces_source  on traces (source, created_at);
create table llm_calls (
  id bigserial primary key, trace_id uuid references traces on delete cascade,
  role text not null, model text not null, tokens_in int not null, tokens_out int not null,
  cost_usd numeric(12,8) not null, latency_ms int not null, cached boolean not null, estimated boolean not null,
  retries int not null default 0, wait_ms int not null default 0,
  created_at timestamptz not null default now()
);
create table judgements (
  trace_id uuid primary key references traces on delete cascade,
  faithfulness real not null, relevance real not null, completeness real not null,   -- 0..1
  rationale text not null, model text not null, cost_usd numeric(12,8) not null,
  created_at timestamptz not null default now()
);

-- evaluation + feedback loop ----------------------------------------------
create table eval_runs (
  run_id text primary key,                     -- '{yyyymmdd-hhmm}-{split}-{mode}-{variant}'
  created_at timestamptz not null default now(),
  split text not null check (split in ('mini','dev','test')), mode text not null, variant text not null,
  git_sha text not null, git_dirty boolean not null, config_hash text not null, n int not null,
  summary jsonb not null default '{}'
);
create table eval_results (
  run_id text references eval_runs on delete cascade, question_id text not null, trace_id uuid references traces,
  gold_type text not null, predicted_type text, route_taken text not null,
  em real not null, f1 real not null, recall_at_k real not null, mrr real not null, sp_precision real,
  faithfulness real, relevance real, completeness real,
  cost_usd numeric(12,8) not null, latency_ms int not null,
  primary key (run_id, question_id)
);
create table review_queue (
  id bigserial primary key, trace_id uuid references traces, run_id text,
  reason text not null,                        -- 'judge_below_threshold' | 'answer_confidence_low' | 'misroute' | 'manual'
  metric text, score real,
  status text not null default 'open'
    check (status in ('open','ok','misroute','bad_chunks','bad_triples','bad_generation')),
  notes text, reviewer text,
  created_at timestamptz not null default now(), resolved_at timestamptz
);
create table manual_scores (
  run_id text not null, question_id text not null, reviewer text not null,
  faithfulness real not null, relevance real not null, completeness real not null, notes text,
  primary key (run_id, question_id, reviewer)
);

-- live mode only (stretch, see 00_MASTER_PLAN.md section 8) ---------------
create table rate_limits (ip_hash text, window_start timestamptz, count int not null default 0, primary key (ip_hash, window_start));
