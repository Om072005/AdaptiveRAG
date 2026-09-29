import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fallbackText, reasonText } from './reasons.ts'

// every string router/policy.py can emit, one per decision table row
const EMITTED = [
  'forced:vector',
  'forced:graph',
  'forced:hybrid',
  'ambiguous:multi_hop 0.52',
  'no_relational_structure',
  'entities_not_in_graph',
  'relational:multi_hop',
  'relational:comparison',
  'low_budget',
  'vector_low_score',
  'graph_no_path',
  'vector_low_score->hybrid',
  'graph_no_path->hybrid',
]

test('every emitted reason becomes a sentence', () => {
  for (const r of EMITTED) {
    const text = reasonText(r)
    assert.notEqual(text, r, r)
    assert.match(text, /^[A-Z].*\.$/, r)
  }
})

test('details from the reason string are kept', () => {
  assert.equal(reasonText('forced:graph'), 'This run asked for graph traversal, so the router did not choose.')
  assert.match(reasonText('ambiguous:multi_hop 0.52'), /multi hop at 0\.52/)
  assert.match(reasonText('relational:comparison'), /a comparison/)
  assert.equal(fallbackText('vector_low_score->hybrid'), reasonText('vector_low_score'))
})

test('an unknown string is shown as it is', () => {
  assert.equal(reasonText('something_new'), 'something_new')
})
