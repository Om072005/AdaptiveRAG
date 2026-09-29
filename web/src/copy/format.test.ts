import assert from 'node:assert/strict'
import { test } from 'node:test'
import { day, duration, money, percent, score } from './format.ts'

test('money has at most 5 decimals', () => {
  assert.equal(money(0.00031), '$0.00031')
  assert.equal(money(0.0012), '$0.0012')
  assert.equal(money(0), '$0')
  assert.equal(money(0.000001), '< $0.00001')
  assert.equal(money(1.5), '$1.5')
})

test('duration is ms below a second, seconds with one decimal above', () => {
  assert.equal(duration(340), '340 ms')
  assert.equal(duration(1830), '1.8 s')
})

test('percent, score and day', () => {
  assert.equal(percent(0.8134), '81.3%')
  assert.equal(score(0.5), '0.50')
  assert.equal(day('2026-09-29T23:30:00Z'), '29 Sep 2026')
})
