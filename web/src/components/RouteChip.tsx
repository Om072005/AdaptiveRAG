import type { Route } from '../types'

// The route encoding of the design system: solid, dashed, dash dot. Never a color.
const DASH: Record<Route, string | undefined> = { vector: undefined, graph: '6 4', hybrid: '10 3 2 3' }
const NAME: Record<Route, string> = { vector: 'Vector', graph: 'Graph', hybrid: 'Hybrid' }

export function RouteChip({ route }: { route: Route }) {
  return (
    <span className="inline-flex items-center gap-2 text-[15px]">
      <svg viewBox="0 0 20 2" width="20" height="2" aria-hidden="true" className="overflow-visible">
        <line x1="0" y1="1" x2="20" y2="1" className="stroke-white" strokeWidth="1.5" strokeDasharray={DASH[route]} />
      </svg>
      {NAME[route]}
    </span>
  )
}
