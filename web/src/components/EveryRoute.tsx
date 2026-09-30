import { duration, money, score } from '../copy/format'
import { MODE_NAME, MODE_ORDER } from '../copy/routes'
import type { Replay } from '../types'
import { RouteChip } from './RouteChip'

/** The same question answered by every recorded mode, best F1 marked with a word. */
export function EveryRoute({ replay }: { replay: Replay }) {
  const runs = MODE_ORDER.flatMap((m) => {
    const run = replay.runs[m]
    return run ? [{ mode: m, run }] : []
  })
  const best = Math.max(...runs.map((r) => r.run.metrics.f1))
  return (
    <div>
      <p className="m-0 mb-5 inline-flex flex-wrap items-center gap-2 rounded-[10px] bg-sunken px-3 py-2 text-[14px] leading-5">
        <span className="text-muted">Gold answer:</span>
        <span className="font-[600] text-ink">{replay.gold_answer}</span>
      </p>
      <ul className={`m-0 grid list-none grid-cols-1 gap-4 p-0 ${runs.length > 1 ? 'md:grid-cols-2' : ''}`}>
        {runs.map(({ mode, run }) => {
          const r = run.response
          const isBest = run.metrics.f1 === best
          return (
            <li key={mode} className={`rounded-[14px] border p-5 ${isBest ? 'border-accent bg-accent-soft' : 'border-rule bg-surface'}`}>
              <div className="flex items-center justify-between gap-4">
                <span className="text-[15px] leading-6 font-[620] text-ink">{MODE_NAME[mode]}</span>
                {isBest && <span className="rounded-full bg-accent px-2.5 py-px text-[12px] leading-5 font-[650] text-accent-ink">Best</span>}
              </div>
              <div className="mt-2">
                <RouteChip route={r.route.final} />
              </div>
              <p className="m-0 mt-4 text-[19px] leading-7 font-[650] tracking-[-0.01em] text-ink">{r.answer.short}</p>
              <dl className="m-0 mt-4 grid grid-cols-3 gap-x-4 border-t border-rule pt-3">
                {[
                  ['F1', score(run.metrics.f1)],
                  ['Cost', money(r.trace.cost.total)],
                  ['Time', duration(r.trace.total_ms)],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-caption">{k}</dt>
                    <dd className="m-0 text-[15px] leading-6 font-[560] text-ink tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
              <p className="text-caption m-0 mt-3 font-mono text-[12px]">{run.run_id}</p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
