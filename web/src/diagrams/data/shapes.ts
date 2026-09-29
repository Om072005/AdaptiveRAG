// Small builders for hand placed diagram data.
import type { Box, DiagramEdge } from '../types.ts'

/** A box given by its center, so columns and rows read as numbers on the 8px grid. */
export const box = (cx: number, cy: number, w: number, h: number): Box => ({ x: cx - w / 2, y: cy - h / 2, w, h })

/** An edge whose id is 'from-to', or the given id when two edges join the same nodes. */
export const edge = (
  from: string,
  to: string,
  label?: string,
  style?: DiagramEdge['style'],
  id = `${from}-${to}`,
): DiagramEdge => ({ id, from, to, label, style })
