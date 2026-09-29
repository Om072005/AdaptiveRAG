import { duration, money, score } from '../copy/format'
import type { Mode, Replay } from '../types'
import { RouteChip } from './RouteChip'

const ORDER: Mode[] = ['auto', 'vector', 'graph', 'hybrid']
const MODE_NAME: Record<Mode, string> = { auto: 'Router', vector: 'Vector only', graph: 'Graph only', hybrid: 'Hybrid only' }

/** The same question answered by every recorded mode, best F1 marked with a word. */
export function EveryRoute({ replay }: { replay: Replay }) {
  const runs = ORDER.flatMap((m) => {
    const run = replay.runs[m]
    return run ? [{ mode: m, run }] : []
  })
  const best = Math.max(...runs.map((r) => r.run.metrics.f1))
  return (
    <div>
      <p className="text-caption m-0 mb-6">Gold answer: {replay.gold_answer}</p>
      <ul className={`m-0 grid list-none grid-cols-1 gap-4 p-0 ${runs.length > 1 ? 'md:grid-cols-2' : ''}`}>
        {runs.map(({ mode, run }) => {
          const r = run.response
          return (
            <li key={mode} className="rounded-[6px] border border-rule p-5">
              <div className="flex items-baseline justify-between gap-4">
                <span className="text-[15px] leading-6 text-white">{MODE_NAME[mode]}</span>
                {run.metrics.f1 === best && <span className="text-caption text-white">Best</span>}
              </div>
              <div className="mt-2">
                <RouteChip route={r.route.final} />
              </div>
              <p className="m-0 mt-4 font-serif text-[21px] leading-7 text-white">{r.answer.short}</p>
              <dl className="m-0 mt-4 grid grid-cols-3 gap-x-4">
                {[
                  ['F1', score(run.metrics.f1)],
                  ['Cost', money(r.trace.cost.total)],
                  ['Time', duration(r.trace.total_ms)],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-caption">{k}</dt>
                    <dd className="m-0 text-[15px] leading-6 tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
              <p className="text-caption m-0 mt-3 font-mono">{run.run_id}</p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
