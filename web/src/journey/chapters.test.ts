import assert from 'node:assert/strict'
import { test } from 'node:test'
import { CHAPTERS, chapterNo, nextChapter, summarize, TOTAL_MINUTES } from './chapters.ts'

test('chapters are unique and each answers a question with a takeaway', () => {
  assert.equal(new Set(CHAPTERS.map((c) => c.id)).size, CHAPTERS.length)
  for (const c of CHAPTERS) {
    assert.ok(c.question.endsWith('?'), c.id)
    assert.ok(c.takeaway.length > 20, c.id)
    const banned = new RegExp(`[${String.fromCharCode(0x2013, 0x2014, 0x2192)}]`)
    assert.ok(!banned.test(c.question + c.takeaway), `${c.id}: dash or arrow glyph`)
  }
  assert.equal(TOTAL_MINUTES, CHAPTERS.reduce((s, c) => s + c.minutes, 0))
})

test('next chapter walks the list and stops at the end', () => {
  assert.equal(nextChapter('idea')?.chapter.id, 'how')
  assert.equal(nextChapter('idea')?.index, 1)
  assert.equal(nextChapter(CHAPTERS[CHAPTERS.length - 1].id), null)
  assert.equal(nextChapter('nope'), null)
  assert.equal(chapterNo(0), '01')
})

test('summarize counts every chapter once, unseen by default', () => {
  assert.deepEqual(summarize({ idea: 'finished', how: 'started' }), { finished: 1, started: 1, unseen: CHAPTERS.length - 2 })
})
