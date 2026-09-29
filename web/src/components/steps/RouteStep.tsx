import { fallbackText, reasonText } from '../../copy/reasons'
import type { RecordedRun } from '../../data/replay'
import { RouteChip } from '../RouteChip'

/** The route decision in words; the lit flowchart joins it when the router diagram lands. */
export function RouteStep({ run }: { run: RecordedRun }) {
  const route = run.response.route
  return (
    <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
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
      <div>
        <p className="text-caption m-0 mb-2">Why</p>
        <ol className="m-0 pl-5 text-[15px] leading-6">
          {route.reasons.map((r) => (
            <li key={r} className="mb-3">
              {reasonText(r)}
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
