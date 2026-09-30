// The one visual code a reader learns once: each retrieval route has a color (from the validated
// data-viz palette) and a line style, used in charts, chips, diagrams and the hero. The router is ink.
import type { Mode } from '../types.ts'

export const MODE_NAME: Record<Mode, string> = { auto: 'Router', vector: 'Vector only', graph: 'Graph only', hybrid: 'Hybrid only' }
export const ROUTE_NAME: Record<Mode, string> = { auto: 'Router', vector: 'Vector', graph: 'Graph', hybrid: 'Hybrid' }

// full class strings so the build keeps them
export const FILL: Record<Mode, string> = { auto: 'fill-ink', vector: 'fill-vector', graph: 'fill-graph', hybrid: 'fill-hybrid' }
export const STROKE: Record<Mode, string> = { auto: 'stroke-ink', vector: 'stroke-vector', graph: 'stroke-graph', hybrid: 'stroke-hybrid' }
export const BG: Record<Mode, string> = { auto: 'bg-ink', vector: 'bg-vector', graph: 'bg-graph', hybrid: 'bg-hybrid' }
export const DASH: Record<Mode, string | undefined> = { auto: undefined, vector: undefined, graph: '6 4', hybrid: '10 3 2 3' }

export const MODE_ORDER: Mode[] = ['auto', 'vector', 'graph', 'hybrid']
