import assert from 'node:assert/strict'
import { test } from 'node:test'
import { explanationParts } from './replay.ts'

test('explanation splits text and citation markers', () => {
  assert.deepEqual(explanationParts('Answer: X\nIt is X [1] and Y [2].'), ['It is X ', 1, ' and Y ', 2, '.'])
  assert.deepEqual(explanationParts('Answer: not enough context'), [])
})
