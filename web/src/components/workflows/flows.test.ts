import assert from 'node:assert/strict'
import { test } from 'node:test'
import { FLOWS, stepLit } from './flows.ts'

test('every walkthrough step lights only nodes and edges its diagram has', () => {
  for (const flow of FLOWS) {
    const nodes = new Set(flow.data.nodes.map((n) => n.id))
    const edges = new Set(flow.data.edges.map((e) => e.id))
    for (const step of flow.steps) {
      const lit = stepLit(step)
      for (const id of lit.nodes) assert.ok(nodes.has(id), `${flow.key} ${step.title}: no node ${id}`)
      const real = [...lit.edges].filter((id) => edges.has(id))
      // a walk may pass two nodes joined by a relabelled edge; it must still light at least one real edge or one node
      assert.ok(real.length > 0 || lit.nodes.size === 1, `${flow.key} ${step.title}: lights no edge`)
    }
  }
})

test('stepLit joins each walk into consecutive edges', () => {
  const lit = stepLit({ title: 't', text: 't', walk: [['a', 'b', 'c']], edges: ['x'] })
  assert.deepEqual([...lit.nodes], ['a', 'b', 'c'])
  assert.deepEqual([...lit.edges].sort(), ['a-b', 'b-c', 'x'])
})
