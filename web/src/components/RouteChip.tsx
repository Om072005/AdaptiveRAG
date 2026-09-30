import { BG, ROUTE_NAME } from '../copy/routes'
import type { Route } from '../types'

/** A route named in words beside its color dot; the word carries the meaning, the dot the identity. */
export function RouteChip({ route }: { route: Route }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-rule bg-surface px-2.5 py-0.5 text-[13.5px] leading-6 font-[500] text-ink">
      <span aria-hidden="true" className={`size-2 rounded-full ${BG[route]}`} />
      {ROUTE_NAME[route]}
    </span>
  )
}
