// Pure helpers the replay components share.
import type { Mode, Replay, ReplayIndex } from '../types.ts'

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

/** The explanation under the "Answer:" line, split into text and [n] citation markers. */
export function explanationParts(answerText: string): (string | number)[] {
  const body = answerText.includes('\n') ? answerText.slice(answerText.indexOf('\n') + 1) : ''
  return body
    .split(/(\[\d+\])/)
    .filter((p) => p !== '')
    .map((p) => (/^\[\d+\]$/.test(p) ? Number(p.slice(1, -1)) : p))
}
