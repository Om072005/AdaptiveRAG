import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fallbackText, reasonText, selectText } from './reasons.ts'

test('every selector reason becomes a sentence', () => {
  assert.equal(selectText('large:route graph'), 'The graph traversal route brings harder context, so the large model answered.')
  assert.equal(selectText('large:label comparison'), 'The question is a comparison, so the large model answered.')
  assert.match(selectText('large:context 2710 tokens > 2500'), /2710 tokens, above the 2500 token limit/)
  assert.equal(
    selectText('small:route vector, label single_hop, 812 tokens'),
    'A vector search route, a single hop question and 812 tokens of context fit the small model.',
  )
  assert.match(selectText('small:route vector, label none, 90 tokens'), /an unclassified question/)
  assert.equal(selectText('sample'), 'sample')
})

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
  assert.match(reasonText('relational:multi_hop', 'hybrid'), /used hybrid/)
  assert.match(reasonText('relational:multi_hop', 'graph'), /walked the graph/)
  assert.equal(fallbackText('vector_low_score->hybrid'), reasonText('vector_low_score'))
})

test('an unknown string is shown as it is', () => {
  assert.equal(reasonText('something_new'), 'something_new')
})
