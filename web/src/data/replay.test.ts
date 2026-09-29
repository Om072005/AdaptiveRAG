import assert from 'node:assert/strict'
import { test } from 'node:test'
import { explanationParts } from './replay.ts'

test('explanation splits text and citation markers', () => {
  assert.deepEqual(explanationParts('Answer: X\nIt is X [1] and Y [2].'), ['It is X ', 1, ' and Y ', 2, '.'])
  assert.deepEqual(explanationParts('Answer: not enough context'), [])
})

test('explanation of a stored answer that starts with the short answer', () => {
  // the shape the generator stores in a real run (20260929-1753-mini-vector-smoke)
  assert.deepEqual(explanationParts('opera. Both are operas. [1] [2]', 'opera'), ['Both are operas. ', 1, ' ', 2])
  assert.deepEqual(explanationParts('not enough context', 'not enough context'), [])
  assert.deepEqual(explanationParts('Some text [3].', 'other'), ['Some text ', 3, '.'])
})
