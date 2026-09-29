import assert from 'node:assert/strict'
import { test } from 'node:test'
import { layers, layoutGraph } from './graphLayout.ts'

const node = (id: string, seed = false) => ({ id, name: id, type: 'OTHER', seed })
const edge = (source: string, target: string, chunk_id: string) => ({
  source,
  target,
  predicate: 'p',
  chunk_id,
  confidence: 0.9,
})
const GRAPH = {
  nodes: [node('b'), node('a', true), node('c'), node('lone')],
  edges: [edge('a', 'b', 'c1'), edge('c', 'b', 'c2')],
}

test('layers count hops from the seeds in either direction', () => {
  const hop = layers(GRAPH)
  assert.deepEqual([hop.get('a'), hop.get('b'), hop.get('c'), hop.get('lone')], [0, 1, 2, 3])
})

test('horizontal layout places one layer per column and a chunk row below', () => {
  const g = layoutGraph(GRAPH)
  const x = Object.fromEntries(g.nodes.map((n) => [n.id, n.x]))
  assert.ok(x.a < x.b && x.b < x.c)
  assert.equal(g.chunks.length, 2)
  assert.ok(g.chunks.every((c) => c.y > Math.max(...g.nodes.map((n) => n.y))))
  assert.ok(g.chunks[0].x < g.chunks[1].x)
  assert.equal(g.hidden, 0)
})

test('the node cap hides the farthest nodes and their edges', () => {
  const g = layoutGraph(GRAPH, 2)
  assert.deepEqual(g.nodes.map((n) => n.id).sort(), ['a', 'b'])
  assert.equal(g.hidden, 2)
  assert.deepEqual(g.edges.map((e) => e.chunk_id), ['c1'])
})

test('vertical layout stacks layers as rows', () => {
  const g = layoutGraph(GRAPH, 12, true)
  const y = Object.fromEntries(g.nodes.map((n) => [n.id, n.y]))
  assert.ok(y.a < y.b && y.b < y.c)
})

test('vertical layout puts chunks in a column right of the nodes', () => {
  const g = layoutGraph(GRAPH, 12, true)
  const right = Math.max(...g.nodes.map((n) => n.x)) + 176
  assert.ok(g.chunks.every((c) => c.x > right))
  assert.ok(g.chunks[0].y < g.chunks[1].y)
})
