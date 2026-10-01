// The live stream of POST /api/query/stream (local only): one JSON object per line while the
// question runs. Steps arrive as each part of the pipeline ends; deltas carry the model's own
// reasoning and its answer as they are written.

export type LiveStep = { type: 'step'; step: string; at_ms: number; [key: string]: unknown }
export type LiveDelta = { type: 'delta'; kind: 'thinking' | 'answer'; text: string }
export type LiveEvent = LiveStep | LiveDelta | { type: 'done'; response: unknown } | { type: 'error'; message: string }

type Hit = { n: number; title: string; score: number; source: string }
type Path = { score: number; edges: [string, string, string][] }
type Seed = { name: string; score: number }
type Call = { role: string; model: string }

const SHOWN_SEEDS = 5 // a long question can match dozens of aliases
const seconds = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`)
const fixed = (n: unknown, digits = 2) => Number(n).toFixed(digits)

/** Split a buffer of streamed text into whole lines and the unfinished rest. */
export function splitLines(buffer: string): { lines: string[]; rest: string } {
  const parts = buffer.split('\n')
  const rest = parts.pop() ?? ''
  return { lines: parts.filter((l) => l.trim() !== ''), rest }
}

function retrieve(e: LiveStep): { headline: string; details: string[] } {
  const hits = e.hits as Hit[]
  let headline = `${e.route}: ${hits.length} chunks, top score ${fixed(e.top_score)}`
  if (e.route !== 'vector') headline += e.path_found ? ', a path was found' : ', no path'
  const details = hits.map((h) => `[${h.n}] ${h.title}  ${fixed(h.score, 4)} ${h.source}`)
  for (const p of e.paths as Path[]) {
    const walk = p.edges.map(([s, pred, o], i) => (i === 0 ? `${s} (${pred}) ${o}` : `(${pred}) ${o}`)).join(' ')
    details.push(`path ${fixed(p.score)}: ${walk}`)
  }
  return { headline: `${headline}, ${seconds(Number(e.ms))}`, details }
}

/** One step as a headline and detail lines, the same reading as the terminal view. */
export function describeStep(e: LiveStep): { headline: string; details: string[] } {
  switch (e.step) {
    case 'embed':
      return { headline: `${e.model}, ${e.dims} dims${e.cached ? ', cached' : ''}, ${seconds(Number(e.ms))}`, details: [] }
    case 'classify': {
      const trusted = Number(e.confidence) >= Number(e.min_confidence) ? 'trusted' : 'below the bar of'
      const probs = Object.entries(e.probs as Record<string, number>).sort((a, b) => b[1] - a[1])
      return {
        headline: `${e.label} at ${fixed(e.confidence)} (${e.method}; ${trusted} ${e.min_confidence})`,
        details: [probs.map(([k, v]) => `${k} ${fixed(v)}`).join(', ')],
      }
    }
    case 'link': {
      const seeds = e.seeds as Seed[]
      const shown = seeds.slice(0, SHOWN_SEEDS).map((s) => `${s.name} ${fixed(s.score)}`)
      if (seeds.length > SHOWN_SEEDS) shown.push(`and ${seeds.length - SHOWN_SEEDS} more`)
      return { headline: shown.length ? shown.join(', ') : 'no entity found in the question', details: [] }
    }
    case 'route':
      return { headline: `${e.initial} (asked for ${e.requested})`, details: e.reasons as string[] }
    case 'retrieve':
      return retrieve(e)
    case 'fallback':
      return { headline: `${e.why}, so ${e.to}`, details: [] }
    case 'model':
      return e.model === null
        ? { headline: 'no chunks, so no model call', details: [] }
        : { headline: `${e.size} model ${e.model}`, details: [String(e.reason)] }
    case 'generated': {
      const where = e.processor ? `, ${e.processor}` : ''
      return { headline: `${e.tokens_in} tokens in, ${e.tokens_out} out, ${seconds(Number(e.ms))}${where}${e.cached ? ', cached' : ''}`, details: [] }
    }
    case 'answer':
      return { headline: `${e.short} (confidence ${fixed(e.confidence)}${e.flagged ? ', flagged for review' : ''})`, details: [] }
    case 'cost':
      return {
        headline: `$${Number(e.total_cost_usd).toFixed(6)} in ${seconds(Number(e.total_latency_ms))}`,
        details: [(e.calls as Call[]).map((c) => `${c.role} ${c.model}`).join(', '), `trace ${e.trace_id}`],
      }
    default:
      return { headline: e.step, details: [] }
  }
}
