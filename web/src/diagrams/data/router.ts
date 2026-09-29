// The README "Router decision logic" flowchart, plus the Unsure edge (decision table row 2) that the
// README chart leaves out. Node ids follow the chart; an edge id is 'from-to'.
import type { QueryResponse } from '../../types.ts'
import type { Box, DiagramData, DiagramEdge, Lit } from '../types.ts'

type RouteBlock = QueryResponse['route']

const box = (cx: number, cy: number, w: number, h: number): Box => ({ x: cx - w / 2, y: cy - h / 2, w, h })
const edge = (from: string, to: string, label?: string, style?: DiagramEdge['style']): DiagramEdge => ({
  id: `${from}-${to}`,
  from,
  to,
  label,
  style,
})

export const ROUTER: DiagramData = {
  id: 'router',
  title: 'Router decision logic',
  desc: 'From the incoming query, the router checks for relational or comparative structure, then whether the entities are in the graph, and routes to vector search or graph traversal. A weak result falls back to hybrid once. An unsure classification goes to hybrid directly. The answer is returned, and flagged for review when its confidence is low.',
  nodes: [
    { id: 'q', lines: ['Incoming', 'query'], kind: 'step', detail: 'The question as it was asked. The classifier reads it first.', module: 'adaptiverag/router/route.py' },
    { id: 'relational', lines: ['Relational or', 'comparative', 'structure?'], kind: 'decision', detail: 'The classifier labels the question single hop, multi hop or comparison. Below classifier.min_confidence it counts as unsure.', module: 'adaptiverag/router/classify.py' },
    { id: 'entities', lines: ['Entities', 'resolvable', 'in graph?'], kind: 'decision', detail: 'Entity linking looks the names in the question up in the alias table. A seed at or above graph.min_seed_score counts as found.', module: 'adaptiverag/stores/graph.py' },
    { id: 'vector', lines: ['Route: vector', 'search'], kind: 'step', detail: 'Nearest chunks by cosine similarity, from the pgvector HNSW index.', module: 'adaptiverag/stores/vector.py' },
    { id: 'graph', lines: ['Route: graph', 'traversal'], kind: 'step', detail: 'Breadth first search from the seed entities, graph.depth hops at most, every edge citing its chunk.', module: 'adaptiverag/stores/graph.py' },
    { id: 'topk', lines: ['Top k score', 'above', 'threshold?'], kind: 'decision', detail: 'The best cosine score must reach vector.min_top_score.', module: 'adaptiverag/router/policy.py' },
    { id: 'path', lines: ['Connected', 'path', 'returned?'], kind: 'decision', detail: 'A path joining two seeds, or a single seed path above graph.min_path_score.', module: 'adaptiverag/router/policy.py' },
    { id: 'fallback', lines: ['Fallback:', 'escalate to', 'hybrid'], kind: 'step', detail: 'At most one fallback per question, and always to hybrid.', module: 'adaptiverag/router/route.py' },
    { id: 'hybrid', lines: ['Hybrid: both', 'backends merge', 'and re-rank'], kind: 'step', detail: 'Vector and graph hits fused by reciprocal rank, then a diversity pass drops near duplicates.', module: 'adaptiverag/router/hybrid.py' },
    { id: 'answer', lines: ['Generate', 'answer'], kind: 'step', detail: 'The selected model writes a short answer that cites numbered context blocks.', module: 'adaptiverag/generate/answer.py' },
    { id: 'confident', lines: ['Answer', 'confidence above', 'threshold?'], kind: 'decision', detail: 'Citation coverage and retrieval strength, weighted. It is a different number from the classifier confidence.', module: 'adaptiverag/generate/confidence.py' },
    { id: 'out', lines: ['Return with', 'citations'], kind: 'step', detail: 'The answer goes back with its sources.', module: 'adaptiverag/pipeline.py' },
    { id: 'flag', lines: ['Return and', 'flag for', 'review'], kind: 'step', detail: 'The answer still goes back, and the trace joins the review queue.', module: 'adaptiverag/eval/review.py' },
  ],
  edges: [
    edge('q', 'relational'),
    edge('relational', 'vector', 'No'),
    edge('relational', 'entities', 'Yes'),
    edge('relational', 'fallback', 'Unsure'),
    edge('entities', 'vector', 'No'),
    edge('entities', 'graph', 'Yes', 'dashed'),
    edge('vector', 'topk'),
    edge('graph', 'path', undefined, 'dashed'),
    edge('topk', 'answer', 'Yes'),
    edge('topk', 'fallback', 'No'),
    edge('path', 'answer', 'Yes'),
    edge('path', 'fallback', 'No'),
    edge('fallback', 'hybrid', undefined, 'dashdot'),
    edge('hybrid', 'answer', undefined, 'dashdot'),
    edge('answer', 'confident'),
    edge('confident', 'out', 'Yes'),
    edge('confident', 'flag', 'No'),
  ],
  // columns 72 224 376 544 696 848 1000, rows 64 208 352
  wide: {
    width: 1080,
    height: 424,
    nodes: {
      q: box(72, 208, 112, 64),
      relational: box(224, 208, 144, 112),
      vector: box(376, 64, 128, 64),
      entities: box(376, 352, 144, 112),
      topk: box(544, 64, 144, 112),
      fallback: box(544, 208, 128, 80),
      graph: box(544, 352, 128, 64),
      hybrid: box(696, 208, 128, 80),
      path: box(696, 352, 144, 112),
      answer: box(848, 208, 128, 64),
      out: box(1000, 64, 128, 64),
      confident: box(1000, 208, 144, 112),
      flag: box(1000, 352, 128, 80),
    },
    bends: {
      'relational-vector': [[224, 64]],
      'relational-entities': [[224, 352]],
      'topk-answer': [[848, 64]],
      'path-fallback': [
        [696, 272],
        [544, 272],
      ],
      'path-answer': [[848, 352]],
    },
    labels: {
      'relational-vector': [224, 112],
      'relational-entities': [224, 304],
      'relational-fallback': [336, 208],
      'entities-vector': [376, 152],
      'topk-fallback': [544, 144],
      'topk-answer': [720, 64],
      'path-answer': [792, 352],
      'path-fallback': [620, 272],
      'confident-out': [1000, 124],
      'confident-flag': [1000, 290],
    },
  },
  // columns 88 176 264 with the Unsure edge down the middle, one row every 120 or so
  tall: {
    width: 352,
    height: 1240,
    nodes: {
      q: box(176, 40, 128, 64),
      relational: box(176, 160, 160, 112),
      vector: box(88, 296, 144, 64),
      entities: box(264, 296, 144, 112),
      topk: box(88, 432, 144, 112),
      graph: box(264, 432, 144, 64),
      path: box(264, 568, 144, 112),
      fallback: box(176, 696, 128, 80),
      hybrid: box(176, 816, 144, 80),
      answer: box(176, 936, 144, 64),
      confident: box(176, 1056, 160, 112),
      out: box(88, 1184, 144, 64),
      flag: box(264, 1184, 144, 80),
    },
    bends: {
      'relational-vector': [[88, 160]],
      'relational-entities': [[264, 160]],
      'topk-answer': [
        [8, 432],
        [8, 936],
      ],
      'topk-fallback': [[88, 696]],
      'path-answer': [
        [344, 568],
        [344, 936],
      ],
      'path-fallback': [[264, 696]],
      'confident-out': [[88, 1056]],
      'confident-flag': [[264, 1056]],
    },
    labels: {
      'relational-vector': [88, 212],
      'relational-entities': [264, 212],
      'relational-fallback': [176, 384],
      'entities-vector': [176, 272],
      'topk-answer': [52, 936],
      'topk-fallback': [88, 600],
      'path-answer': [300, 936],
      'path-fallback': [264, 660],
      'confident-out': [88, 1116],
      'confident-flag': [264, 1112],
    },
  },
}

const ROUTE_NODE = { vector: 'vector', graph: 'graph', hybrid: 'hybrid' } as const

/** The nodes and edges a recorded route decision passed through; flagged lights the last branch. */
export function litPath(route: RouteBlock, flagged: boolean | null = null): Lit {
  const nodes = new Set<string>()
  const edges = new Set<string>()
  const walk = (...ids: string[]) => {
    ids.forEach((id, i) => {
      nodes.add(id)
      if (i > 0) edges.add(`${ids[i - 1]}-${id}`)
    })
  }
  const has = (prefix: string) => route.reasons.some((r) => r.startsWith(prefix))
  const forced = route.requested !== 'auto'

  if (forced || has('low_budget')) {
    // the route was set, not reached by the chart's questions: light the route, not the way there
    if (!forced) walk('q', 'relational')
    nodes.add(ROUTE_NODE[route.initial])
  } else if (has('ambiguous')) walk('q', 'relational', 'fallback')
  else if (has('no_relational_structure')) walk('q', 'relational', 'vector')
  else if (has('entities_not_in_graph')) walk('q', 'relational', 'entities', 'vector')
  else if (has('relational')) walk('q', 'relational', 'entities', 'graph')
  else nodes.add('q')

  const fellBack = route.fallbacks.length > 0
  if (route.initial === 'vector' && !forced) walk('vector', 'topk', ...(fellBack ? ['fallback'] : ['answer']))
  if (route.initial === 'graph' && !forced) walk('graph', 'path', ...(fellBack ? ['fallback'] : ['answer']))
  if (route.final === 'hybrid') {
    if (nodes.has('fallback')) walk('fallback', 'hybrid')
    walk('hybrid', 'answer')
  } else if (forced) nodes.add('answer')
  if (flagged !== null) walk('answer', 'confident', flagged ? 'flag' : 'out')
  return { nodes, edges }
}
