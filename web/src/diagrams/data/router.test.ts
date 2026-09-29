import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { QueryResponse } from '../../types.ts'
import { litPath, ROUTER } from './router.ts'

type RouteBlock = QueryResponse['route']

const decision = (over: Partial<RouteBlock>): RouteBlock => ({
  requested: 'auto',
  label: 'single_hop',
  label_confidence: 0.9,
  method: 'logreg',
  initial: 'vector',
  final: 'vector',
  fallbacks: [],
  reasons: [],
  ...over,
})

const sorted = (s: Set<string>) => [...s].sort()

test('every edge joins two nodes and both layouts place every node', () => {
  const ids = new Set(ROUTER.nodes.map((n) => n.id))
  for (const e of ROUTER.edges) assert.ok(ids.has(e.from) && ids.has(e.to), e.id)
  for (const layout of [ROUTER.wide, ROUTER.tall]) {
    assert.deepEqual(Object.keys(layout.nodes).sort(), [...ids].sort())
    for (const b of Object.values(layout.nodes)) {
      assert.ok(b.x >= 0 && b.y >= 0 && b.x + b.w <= layout.width && b.y + b.h <= layout.height)
      assert.ok([b.x, b.y, b.w, b.h].every((v) => v % 8 === 0), 'on the 8px grid')
    }
  }
})

test('row 1: a forced route lights only the route and the answer', () => {
  const lit = litPath(decision({ requested: 'graph', initial: 'graph', final: 'graph', reasons: ['forced:graph'] }))
  assert.deepEqual(sorted(lit.nodes), ['answer', 'graph'])
  assert.equal(lit.edges.size, 0)
})

test('row 2: an unsure classification goes to hybrid through the fallback box', () => {
  const lit = litPath(
    decision({ initial: 'hybrid', final: 'hybrid', label: 'multi_hop', reasons: ['ambiguous:multi_hop 0.42'] }),
  )
  assert.deepEqual(sorted(lit.edges), ['fallback-hybrid', 'hybrid-answer', 'q-relational', 'relational-fallback'])
})

test('row 3 with a good top score: vector and straight to the answer', () => {
  const lit = litPath(decision({ reasons: ['no_relational_structure'] }))
  assert.deepEqual(sorted(lit.edges), ['q-relational', 'relational-vector', 'topk-answer', 'vector-topk'])
})

test('row 4: relational but not in the graph goes to vector through the entity check', () => {
  const lit = litPath(decision({ label: 'multi_hop', reasons: ['entities_not_in_graph'] }))
  assert.ok(lit.edges.has('relational-entities') && lit.edges.has('entities-vector'))
  assert.ok(!lit.nodes.has('graph'))
})

test('row 5 with a connected path: graph and straight to the answer', () => {
  const lit = litPath(decision({ label: 'multi_hop', initial: 'graph', final: 'graph', reasons: ['relational:multi_hop'] }))
  assert.deepEqual(sorted(lit.edges), ['entities-graph', 'graph-path', 'path-answer', 'q-relational', 'relational-entities'])
})

test('row 6: a low budget lights vector without claiming the question had no structure', () => {
  const lit = litPath(decision({ label: 'multi_hop', reasons: ['relational:multi_hop', 'low_budget'] }))
  assert.ok(lit.nodes.has('vector') && lit.edges.has('vector-topk'))
  assert.ok(!lit.edges.has('relational-vector') && !lit.nodes.has('graph'))
})

test('F1 and F2: a weak result falls back to hybrid once', () => {
  const f1 = litPath(
    decision({ final: 'hybrid', fallbacks: ['vector_low_score->hybrid'], reasons: ['no_relational_structure'] }),
  )
  assert.ok(['topk-fallback', 'fallback-hybrid', 'hybrid-answer'].every((e) => f1.edges.has(e)))
  assert.ok(!f1.edges.has('topk-answer'))
  const f2 = litPath(
    decision({
      label: 'comparison',
      initial: 'graph',
      final: 'hybrid',
      fallbacks: ['graph_no_path->hybrid'],
      reasons: ['relational:comparison'],
    }),
  )
  assert.ok(['path-fallback', 'fallback-hybrid', 'hybrid-answer'].every((e) => f2.edges.has(e)))
})

test('the answer branch lights only when the flag is known', () => {
  const base = decision({ reasons: ['no_relational_structure'] })
  assert.ok(!litPath(base).nodes.has('confident'))
  assert.ok(litPath(base, false).edges.has('confident-out'))
  assert.ok(litPath(base, true).edges.has('confident-flag'))
})

test('every lit edge exists in the chart', () => {
  const ids = new Set(ROUTER.edges.map((e) => e.id))
  const all = litPath(
    decision({ final: 'hybrid', fallbacks: ['vector_low_score->hybrid'], reasons: ['no_relational_structure'] }),
    true,
  )
  for (const e of all.edges) assert.ok(ids.has(e), e)
})
