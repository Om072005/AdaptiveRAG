// Diagram data: nodes and edges once, then two hand placed layouts (02_DESIGN_SYSTEM.md section 6).

export type Point = [number, number]
export type NodeKind = 'step' | 'decision' | 'store'
// route encoding: vector solid, graph dashed, hybrid dash dot; provenance and feedback dotted
export type EdgeStyle = 'solid' | 'dashed' | 'dashdot' | 'dotted'

export type DiagramNode = {
  id: string
  lines: string[] // the label, one entry per line
  kind: NodeKind
  detail?: string // what it does, in one or two sentences
  module?: string // where it lives in the code
  status?: string // 'Built and measured' | 'Built' | 'Not built'
}

export type DiagramEdge = {
  id: string
  from: string
  to: string
  label?: string
  style?: EdgeStyle
}

export type Box = { x: number; y: number; w: number; h: number }

export type Layout = {
  width: number
  height: number
  nodes: Record<string, Box>
  // corner points between the two ends, when the default elbow is not the right path
  bends?: Record<string, Point[]>
  // where an edge label sits, when the middle of the longest segment is not the right place
  labels?: Record<string, Point>
}

export type DiagramData = {
  id: string
  title: string
  desc: string
  nodes: DiagramNode[]
  edges: DiagramEdge[]
  wide: Layout // from 1024px: used when the diagram container is 896px or wider
  tall: Layout // narrower containers, never drawn wider than its own width
}

export type Lit = { nodes: Set<string>; edges: Set<string> }
