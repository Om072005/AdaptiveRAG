// Pure helpers the replay components share.
import type { Mode, QueryResponse, Replay, ReplayIndex } from '../types.ts'

export type ReplayItem = ReplayIndex['items'][number]
export type RecordedRun = NonNullable<Replay['runs'][Mode]>

export const STAGES = ['Classify', 'Route', 'Retrieve', 'Model', 'Answer', 'Cost'] as const
export const OUTCOME = { correct: 'Correct', partial: 'Partial', wrong: 'Wrong', misrouted: 'Misrouted' }
const MODE_ORDER: Mode[] = ['auto', 'vector', 'graph', 'hybrid']

export const wentWrong = (i: ReplayItem) => i.outcome === 'wrong' || i.outcome === 'misrouted'

export const GROUPS: { title: string; pick: (i: ReplayItem) => boolean }[] = [
  { title: 'Single hop', pick: (i) => i.type === 'single_hop' && !wentWrong(i) },
  { title: 'Multi hop', pick: (i) => i.type === 'multi_hop' && !wentWrong(i) },
  { title: 'Comparison', pick: (i) => i.type === 'comparison' && !wentWrong(i) },
  { title: 'Went wrong', pick: wentWrong },
]

/** Questions in list order: the groups above, each in index order. */
export function ordered(items: ReplayItem[]): ReplayItem[] {
  return GROUPS.flatMap((g) => items.filter(g.pick))
}

/** The run the step by step view follows: the router's own choice when it was recorded. */
export function mainRun(replay: Replay): { mode: Mode; run: RecordedRun } | null {
  for (const mode of MODE_ORDER) {
    const run = replay.runs[mode]
    if (run) return { mode, run }
  }
  return null
}

export const NOT_ENOUGH = 'not enough context'

/** The explanation after the short answer, split into text and [n] citation markers. The stored
 * text is either "Answer: X" plus a line, or the short answer followed by the explanation. */
export function explanationParts(answerText: string, short = ''): (string | number)[] {
  let body = answerText.trim()
  if (/^answer:/i.test(body)) {
    body = body.includes('\n') ? body.slice(body.indexOf('\n') + 1) : ''
  } else if (short && body.toLowerCase().startsWith(short.trim().toLowerCase())) {
    body = body.slice(short.trim().length).replace(/^[.:,]?\s*/, '')
  }
  return body
    .split(/(\[\d+\])/)
    .filter((p) => p !== '')
    .map((p) => (/^\[\d+\]$/.test(p) ? Number(p.slice(1, -1)) : p))
}

export const LIVE_ID = 'live'

/** A live API answer in the Replay shape, so the same panel shows it; it has no gold answer. */
export function liveReplay(response: QueryResponse, mode: Mode): Replay {
  return {
    sample: false,
    question_id: LIVE_ID,
    question: response.question,
    type: response.route.label ?? 'single_hop',
    gold_answer: '',
    supporting_titles: [],
    why: '',
    recorded_at: new Date().toISOString(),
    git_sha: '',
    config_hash: '',
    runs: { [mode]: { run_id: response.trace_id, response, metrics: { em: 0, f1: 0, recall_at_k: 0 }, judgement: null } },
  }
}
