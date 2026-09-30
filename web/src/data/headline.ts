// The hero's headline numbers, read from the pinned router and single route runs.
import { money, percent, score } from '../copy/format.ts'
import type { Results } from '../types.ts'

export type Stat = { value: string; label: string; detail: string }

/** Headline numbers from the pinned test runs, as measured; the tile row hides when a table is missing. */
export function headlineStats(results: Results): { stats: Stat[]; runId: string; n: number } | null {
  const t = results.tables
  const router = t.routes.find((r) => r.mode === 'auto')
  const singles = t.routes.filter((r) => r.mode !== 'auto')
  if (!router || singles.length === 0) return null
  const best = singles.reduce((a, b) => (b.f1 > a.f1 ? b : a))
  const multi = (mode: string) => t.by_type.find((r) => r.mode === mode && r.type === 'multi_hop')
  const [rm, vm] = [multi('auto'), multi('vector')]
  const stats: Stat[] = [
    { value: score(router.f1), label: 'Answer accuracy (F1)', detail: `vs ${score(best.f1)} for the best single method (${best.mode})` },
  ]
  if (rm && vm) {
    stats.push({ value: score(rm.f1), label: 'On multi step questions', detail: `vs ${score(vm.f1)} for vector search alone` })
  }
  stats.push(
    { value: percent(router.recall_at_k), label: 'Right passage found', detail: 'share of questions with a supporting passage retrieved' },
    { value: money(router.cost_per_query_usd), label: 'Cost per question', detail: 'list price of the open models used' },
  )
  return { stats, runId: router.run_id, n: results.runs[router.run_id]?.n ?? 0 }
}
