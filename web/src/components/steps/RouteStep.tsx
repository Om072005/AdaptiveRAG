import { fallbackText, reasonText } from '../../copy/reasons'
import type { RecordedRun } from '../../data/replay'
import { RouterFlow } from '../../diagrams/RouterFlow'
import { RouteChip } from '../RouteChip'

/** The router flowchart with this question's path lit; the decision in words sits beside it. */
export function RouteStep({ run }: { run: RecordedRun }) {
  const route = run.response.route
  return (
    <div className="grid grid-cols-1 gap-x-10 gap-y-8 md:grid-cols-[minmax(0,352px)_minmax(0,1fr)]">
      <div className="min-w-0">
        <RouterFlow route={route} flagged={run.response.answer.flagged} />
      </div>
      <div className="min-w-0 border-t border-rule pt-6 md:border-t-0 md:pt-0">
        <dl className="m-0">
          <dt className="text-caption">Route taken</dt>
          <dd className="m-0 mb-5">
            <RouteChip route={route.final} />
          </dd>
          {route.initial !== route.final && (
            <>
              <dt className="text-caption">First choice</dt>
              <dd className="m-0 mb-5">
                <RouteChip route={route.initial} />
              </dd>
            </>
          )}
        </dl>
        <p className="text-caption m-0 mb-2">Why</p>
        <ol className="m-0 pl-5 text-[15px] leading-6">
          {route.reasons.map((r) => (
            <li key={r} className="mb-3">
              {reasonText(r, route.initial)}
            </li>
          ))}
          {route.fallbacks.map((f) => (
            <li key={f} className="mb-3">
              {fallbackText(f)}
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
