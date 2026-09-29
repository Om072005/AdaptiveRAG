import { duration, money } from '../../copy/format'
import type { RecordedRun } from '../../data/replay'
import { Waterfall } from '../Waterfall'

export function CostStep({ run }: { run: RecordedRun }) {
  const t = run.response.trace
  const facts: [string, string][] = [
    ['Total time', duration(t.total_ms)],
    ['Total cost', money(t.cost.total)],
    ['Classifier', money(t.cost.classifier)],
    ['Generation', money(t.cost.generation)],
    ['Tokens in', String(t.tokens_in)],
    ['Tokens out', String(t.tokens_out)],
  ]
  return (
    <div>
      <Waterfall spans={t.spans} totalMs={t.total_ms} />
      <dl className="m-0 mt-8 grid grid-cols-2 gap-x-8 border-t border-rule pt-6 sm:grid-cols-3">
        {facts.map(([k, v]) => (
          <div key={k} className="mb-4">
            <dt className="text-caption">{k}</dt>
            <dd className="m-0 text-[15px] leading-6 tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
      <div className="text-caption mt-2">
        <p className="m-0">Costs are list prices, whatever key ran the question.</p>
        {t.throttle_wait_ms > 0 && (
          <p className="m-0 mt-1">
            {duration(t.throttle_wait_ms)} spent waiting on a provider rate limit is not counted in the time above.
          </p>
        )}
        {t.cached && (
          <p className="m-0 mt-1">Every model call came from the cache; time and cost are those of the original calls.</p>
        )}
      </div>
    </div>
  )
}
