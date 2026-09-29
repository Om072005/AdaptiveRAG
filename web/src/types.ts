// Mirrors 01_CONTRACTS.md sections 6 (local API) and 6b (static page data) exactly.
// Numbers are plain numbers, times in ms, money in USD.

export type Mode = 'auto' | 'vector' | 'graph' | 'hybrid'
export type Route = 'vector' | 'graph' | 'hybrid'
export type QType = 'single_hop' | 'multi_hop' | 'comparison'

export type QueryResponse = {
  trace_id: string
  question: string
  answer: {
    short: string
    text: string
    model: string
    size: 'small' | 'large'
    select_reason: string
    confidence: number
    flagged: boolean
    citations: { n: number; title: string; snippet: string; chunk_id: string }[]
  }
  route: {
    requested: Mode
    label: QType | null
    label_confidence: number | null
    method: string | null
    initial: Route
    final: Route
    fallbacks: string[]
    reasons: string[]
  }
  retrieval: {
    hits: { rank: number; title: string; snippet: string; score: number; source: Route; chunk_id: string }[]
    graph: {
      nodes: { id: string; name: string; type: string; seed: boolean }[]
      edges: { source: string; target: string; predicate: string; chunk_id: string; confidence: number }[]
    }
    top_score: number
    path_found: boolean
  }
  trace: {
    spans: { name: string; ms: number }[]
    tokens_in: number
    tokens_out: number
    cost: { classifier: number; generation: number; total: number }
    total_ms: number
    throttle_wait_ms: number
    cached: boolean
  }
  live: { budget_left_usd: number } | null // null everywhere except the stretch live mode
}

export type Judgement = {
  faithfulness: number
  relevance: number
  completeness: number
  rationale: string
  cost_usd: number
  flagged: boolean
  queued: boolean
}

export type Results = {
  sample: boolean
  generated_at: string
  git_sha: string
  runs: Record<
    string,
    { split: 'dev' | 'test'; mode: Mode; variant: string; n: number; created_at: string; config_hash: string }
  >
  tables: {
    routes: {
      run_id: string
      mode: Mode
      em: number
      f1: number
      recall_at_k: number
      faithfulness: number | null
      cost_per_query_usd: number
      p50_ms: number
      p95_ms: number
    }[]
    by_type: { run_id: string; mode: Mode; type: QType; f1: number; recall_at_k: number }[]
    quality_per_cost: {
      run_id: string
      variant: string
      f1: number
      faithfulness: number | null
      cost_per_query_usd: number
      eligible: boolean
    }[]
    selector: { run_id: string; variant: string; f1: number; cost_per_query_usd: number; large_share: number }[]
    classifier: { run_id: string; method: string; macro_f1: number; cost_per_query_usd: number; p50_ms: number }[]
    confusion: { run_id: string; labels: QType[]; matrix: number[][] }
    hnsw: {
      run_id: string
      index: string
      ef: number | null
      recall_at_10: number
      p50_ms: number
      p95_ms: number
      build_s: number | null
    }[]
    chunking: {
      run_id: string
      strategy: string
      params: string
      precision: number
      context_retention: number
      retrieval_score: number
      verdict: string
    }[] // the README table's columns, measured
    graph: { run_id: string; entities: number; relations: number; reject_rate: number; er_precision: number }
    failures: { n: number; symptom: string; root_cause: string; fix: string; status: string; run_id: string | null }[]
  }
}

export type ReplayIndex = {
  sample: boolean
  items: {
    question_id: string
    question: string
    type: QType
    why: string
    modes: Mode[]
    outcome: 'correct' | 'partial' | 'wrong' | 'misrouted'
  }[]
}

export type Replay = {
  sample: boolean
  question_id: string
  question: string
  type: QType
  gold_answer: string
  supporting_titles: string[]
  why: string // one plain sentence: why this question is on the page
  recorded_at: string
  git_sha: string
  config_hash: string
  runs: Partial<
    Record<
      Mode,
      {
        run_id: string
        response: QueryResponse
        metrics: { em: number; f1: number; recall_at_k: number }
        judgement: Judgement | null
      }
    >
  >
}

export type SiteContent = {
  repo_url: string
  contact_email: string
  license: string
  members: { name: string; role: string; github: string }[]
}
