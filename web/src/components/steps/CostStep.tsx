import { duration, money } from '../../copy/format'
import type { RecordedRun } from '../../data/replay'
import { Waterfall } from '../Waterfall'
import { Facts } from './Facts'

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
      <div className="mt-6">
        <Facts items={facts} />
      </div>
      <div className="text-caption mt-4">
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
