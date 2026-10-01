import assert from 'node:assert/strict'
import { test } from 'node:test'
import { describeStep, splitLines, type LiveStep } from './liveSteps.ts'

const step = (step: string, data: Record<string, unknown>): LiveStep => ({ type: 'step', step, at_ms: 10, ...data })

test('a stream buffer splits into whole lines and the unfinished rest', () => {
  assert.deepEqual(splitLines('{"a":1}\n{"b":2}\n{"c"'), { lines: ['{"a":1}', '{"b":2}'], rest: '{"c"' })
  assert.deepEqual(splitLines('{"a":1}\n\n'), { lines: ['{"a":1}'], rest: '' })
})

test('classify says whether the router trusts the label', () => {
  const below = describeStep(step('classify', { label: 'single_hop', confidence: 0.77, method: 'logreg', min_confidence: 0.85, probs: { multi_hop: 0.2, single_hop: 0.77 } }))
  assert.equal(below.headline, 'single_hop at 0.77 (logreg; below the bar of 0.85)')
  assert.deepEqual(below.details, ['single_hop 0.77, multi_hop 0.20'])
})

test('retrieve lists hits and graph paths', () => {
  const r = describeStep(
    step('retrieve', {
      route: 'graph',
      hits: [{ n: 1, title: 'Roy Scheider', score: 0.42, source: 'graph' }],
      top_score: 0.42,
      path_found: true,
      paths: [{ score: 0.42, edges: [['Nathan Bridger', 'played_by', 'Roy Scheider']] }],
      ms: 1200,
    }),
  )
  assert.equal(r.headline, 'graph: 1 chunks, top score 0.42, a path was found, 1.2 s')
  assert.deepEqual(r.details, ['[1] Roy Scheider  0.4200 graph', 'path 0.42: Nathan Bridger (played_by) Roy Scheider'])
})

test('generated names where the model ran', () => {
  const g = describeStep(step('generated', { tokens_in: 900, tokens_out: 40, ms: 8100, processor: '100% GPU', cached: false }))
  assert.equal(g.headline, '900 tokens in, 40 out, 8.1 s, 100% GPU')
})

test('a step with no model call says so', () => {
  assert.equal(describeStep(step('model', { size: null, model: null, reason: 'no_context' })).headline, 'no chunks, so no model call')
})

test('link names the first five entities and counts the rest', () => {
  const seeds = Array.from({ length: 7 }, (_, i) => ({ name: `E${i}`, score: 1 - i / 10 }))
  assert.equal(describeStep(step('link', { seeds })).headline, 'E0 1.00, E1 0.90, E2 0.80, E3 0.70, E4 0.60, and 2 more')
})

test('entities that share a name show once with a count', () => {
  const seeds = [
    { name: 'Bryce Courtenay', score: 1 },
    { name: 'Bryce Courtenay', score: 1 },
    { name: 'Juan Carlos', score: 0.86 },
  ]
  assert.equal(describeStep(step('link', { seeds })).headline, 'Bryce Courtenay 1.00 (2 entities), Juan Carlos 0.86')
})
