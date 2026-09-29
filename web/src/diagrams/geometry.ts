// Edge geometry for hand placed diagrams: orthogonal paths with 8px rounded corners, no layout engine.
import type { Box, NodeKind, Point } from './types.ts'

const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), hi)

export function center(b: Box): Point {
  return [b.x + b.w / 2, b.y + b.h / 2]
}

/** Where an edge meets a node on the side facing a point. A decision is met at a corner of its diamond. */
export function anchor(b: Box, kind: NodeKind, toward: Point): Point {
  const [cx, cy] = center(b)
  const [tx, ty] = toward
  const straightDown = tx >= b.x && tx <= b.x + b.w
  if (straightDown && ty >= b.y + b.h) return [kind === 'decision' ? cx : tx, b.y + b.h]
  if (straightDown && ty <= b.y) return [kind === 'decision' ? cx : tx, b.y]
  const y = kind === 'decision' ? cy : clamp(ty, b.y, b.y + b.h)
  return tx >= b.x + b.w ? [b.x + b.w, y] : [b.x, y]
}

/** Points of an edge from box a to box b: through the given bends, else a straight line or one elbow. */
export function route(a: Box, ak: NodeKind, b: Box, bk: NodeKind, bends: Point[] = []): Point[] {
  if (bends.length) return [anchor(a, ak, bends[0]), ...bends, anchor(b, bk, bends[bends.length - 1])]
  const [ax, ay] = center(a)
  const [bx, by] = center(b)
  if (b.y >= a.y + a.h || b.y + b.h <= a.y) {
    const down = by > ay
    const s: Point = [ax, down ? a.y + a.h : a.y]
    const e: Point = [bx, down ? b.y : b.y + b.h]
    if (s[0] === e[0]) return [s, e]
    const my = (s[1] + e[1]) / 2
    return [s, [s[0], my], [e[0], my], e]
  }
  const right = bx > ax
  const s: Point = [right ? a.x + a.w : a.x, ay]
  const e: Point = [right ? b.x : b.x + b.w, by]
  if (s[1] === e[1]) return [s, e]
  const mx = (s[0] + e[0]) / 2
  return [s, [mx, s[1]], [mx, e[1]], e]
}

const dist = (p: Point, q: Point) => Math.hypot(q[0] - p[0], q[1] - p[1])

function toward(from: Point, to: Point, r: number): string {
  const d = dist(from, to) || 1
  return `${from[0] + ((to[0] - from[0]) * r) / d} ${from[1] + ((to[1] - from[1]) * r) / d}`
}

/** SVG path through the points, each corner rounded with an 8px radius (less on a short segment). */
export function pathD(points: Point[], radius = 8): string {
  let d = `M${points[0][0]} ${points[0][1]}`
  for (let i = 1; i < points.length - 1; i++) {
    const [prev, cur, next] = [points[i - 1], points[i], points[i + 1]]
    const r = Math.min(radius, dist(prev, cur) / 2, dist(cur, next) / 2)
    d += ` L${toward(cur, prev, r)} Q${cur[0]} ${cur[1]} ${toward(cur, next, r)}`
  }
  const last = points[points.length - 1]
  return `${d} L${last[0]} ${last[1]}`
}

/** Middle of the longest segment: where an edge label goes unless the layout places it. */
export function labelPoint(points: Point[]): Point {
  let best = 0
  for (let i = 1; i < points.length - 1; i++) {
    if (dist(points[i], points[i + 1]) > dist(points[best], points[best + 1])) best = i
  }
  const [p, q] = [points[best], points[best + 1]]
  return [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2]
}

/** Diamond outline inside a box. */
export function diamond(b: Box): string {
  const [cx, cy] = center(b)
  return `${cx},${b.y} ${b.x + b.w},${cy} ${cx},${b.y + b.h} ${b.x},${cy}`
}
