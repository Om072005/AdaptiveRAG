import assert from 'node:assert/strict'
import { test } from 'node:test'
import { CHAPTERS, chapterNo, summarize, TOTAL_MINUTES } from './chapters.ts'

test('chapters are unique and each has a short takeaway', () => {
  assert.equal(new Set(CHAPTERS.map((c) => c.id)).size, CHAPTERS.length)
  for (const c of CHAPTERS) {
    assert.ok(c.takeaway.length > 20, c.id)
    assert.ok(c.takeaway.length <= 100, `${c.id}: takeaway over one line`)
    const banned = new RegExp(`[${String.fromCharCode(0x2013, 0x2014, 0x2192)}]`)
    assert.ok(!banned.test(c.takeaway), `${c.id}: dash or arrow glyph`)
  }
  assert.equal(TOTAL_MINUTES, CHAPTERS.reduce((s, c) => s + c.minutes, 0))
})

test('chapter numbers are two digits', () => {
  assert.equal(chapterNo(0), '01')
})

test('summarize counts every chapter once, unseen by default', () => {
  assert.deepEqual(summarize({ idea: 'finished', how: 'started' }), { finished: 1, started: 1, unseen: CHAPTERS.length - 2 })
})
