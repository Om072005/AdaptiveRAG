// Hop layered layout for a retrieved graph path: seeds in the first layer, each hop one layer on,
// source chunks in a row below. Coordinates are SVG units; no layout engine.
import type { QueryResponse } from '../types.ts'

type Graph = QueryResponse['retrieval']['graph']
type GNode = Graph['nodes'][number]
type GEdge = Graph['edges'][number]

export type PlacedEdge = GEdge & { x1: number; y1: number; x2: number; y2: number; chunkX: number; chunkY: number }
export type Placed = {
  nodes: (GNode & { x: number; y: number })[]
  edges: PlacedEdge[]
  chunks: { id: string; n: number; x: number; y: number }[]
  hidden: number
  width: number
  height: number
}

export const NODE_W = 176
export const NODE_H = 40
export const CHUNK_W = 96
const PAD = 24

/** Hop number of every node, counted from the seeds over edges in either direction. */
export function layers(graph: Graph): Map<string, number> {
  const next = new Map<string, string[]>()
  for (const e of graph.edges) {
    next.set(e.source, [...(next.get(e.source) ?? []), e.target])
    next.set(e.target, [...(next.get(e.target) ?? []), e.source])
  }
  const hop = new Map<string, number>()
  let frontier = graph.nodes.filter((n) => n.seed).map((n) => n.id)
  if (!frontier.length && graph.nodes.length) frontier = [graph.nodes[0].id]
  frontier.forEach((id) => hop.set(id, 0))
  for (let depth = 1; frontier.length; depth++) {
    frontier = [...new Set(frontier.flatMap((id) => (next.get(id) ?? []).filter((m) => !hop.has(m))))]
    frontier.forEach((id) => hop.set(id, depth))
  }
  // nodes not connected to any seed go one layer past the last hop
  const last = Math.max(0, ...hop.values()) + 1
  graph.nodes.forEach((n) => {
    if (!hop.has(n.id)) hop.set(n.id, last)
  })
  return hop
}

export function layoutGraph(graph: Graph, cap = 12, vertical = false): Placed {
  const hop = layers(graph)
  const layerOf = (n: GNode) => hop.get(n.id) ?? 0
  const kept = [...graph.nodes].sort((a, b) => layerOf(a) - layerOf(b)).slice(0, cap)
  const keptIds = new Set(kept.map((n) => n.id))
  const layerList = [...new Set(kept.map(layerOf))].sort((a, b) => a - b)
  const [step, across] = vertical ? [112, NODE_W + 24] : [NODE_W + 144, 72]

  const nodes = layerList.flatMap((layer, li) =>
    kept
      .filter((n) => layerOf(n) === layer)
      .map((n, i) => {
        const along = PAD + li * step
        const side = PAD + i * across
        return { ...n, x: vertical ? side : along, y: vertical ? along : side }
      }),
  )
  const at = new Map(nodes.map((n) => [n.id, n]))
  const nodesRight = Math.max(0, ...nodes.map((n) => n.x + NODE_W))
  const nodesBottom = Math.max(0, ...nodes.map((n) => n.y + NODE_H))

  const shown = graph.edges
    .filter((e) => keptIds.has(e.source) && keptIds.has(e.target))
    .map((e) => {
      const s = at.get(e.source)!
      const t = at.get(e.target)!
      const [x1, y1, x2, y2] = vertical
        ? [s.x + NODE_W / 2, s.y + NODE_H, t.x + NODE_W / 2, t.y]
        : [s.x + NODE_W, s.y + NODE_H / 2, t.x, t.y + NODE_H / 2]
      return { ...e, x1, y1, x2, y2 }
    })
  const chunkIds = [...new Set(shown.map((e) => e.chunk_id))]
  const mid = (id: string) => {
    const own = shown.filter((e) => e.chunk_id === id)
    return own.reduce((sum, e) => sum + (vertical ? (e.y1 + e.y2) / 2 : (e.x1 + e.x2) / 2), 0) / own.length
  }
  // horizontal: a row of chunks below the nodes; vertical: a column to the right, level with its edges
  let chunks: Placed['chunks']
  if (vertical) {
    let floor = 0
    chunks = chunkIds.map((id, i) => {
      const y = Math.max(floor, mid(id) - 16)
      floor = y + 40
      return { id, n: i + 1, x: nodesRight + 48, y }
    })
  } else {
    let left = PAD
    chunks = chunkIds.map((id, i) => {
      const x = Math.max(left, mid(id) - CHUNK_W / 2)
      left = x + CHUNK_W + 16
      return { id, n: i + 1, x, y: nodesBottom + 72 }
    })
  }
  const chunkAt = new Map(chunks.map((c) => [c.id, c]))
  const edges = shown.map((e) => {
    const c = chunkAt.get(e.chunk_id)!
    return vertical ? { ...e, chunkX: c.x, chunkY: c.y + 16 } : { ...e, chunkX: c.x + CHUNK_W / 2, chunkY: c.y }
  })
  const width = Math.max(nodesRight, ...chunks.map((c) => c.x + CHUNK_W)) + PAD
  const height = Math.max(nodesBottom, ...chunks.map((c) => c.y + 32)) + PAD
  return { nodes, edges, chunks, hidden: graph.nodes.length - kept.length, width, height }
}
