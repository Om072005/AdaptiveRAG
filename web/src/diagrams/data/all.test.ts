import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { DiagramData } from '../types.ts'
import { ARCHITECTURE } from './architecture.ts'
import { EVAL_LOOP } from './evalLoop.ts'
import { INGESTION } from './ingestion.ts'
import { ROUTER } from './router.ts'
import { SCHEMA } from './schema.ts'

const ALL: DiagramData[] = [ARCHITECTURE, INGESTION, ROUTER, SCHEMA, EVAL_LOOP]

for (const d of ALL) {
  test(`${d.id}: ids are unique and every edge joins two nodes`, () => {
    const nodes = new Set(d.nodes.map((n) => n.id))
    assert.equal(nodes.size, d.nodes.length)
    assert.equal(new Set(d.edges.map((e) => e.id)).size, d.edges.length)
    for (const e of d.edges) assert.ok(nodes.has(e.from) && nodes.has(e.to), e.id)
    assert.ok(d.title && d.desc)
  })

  test(`${d.id}: both layouts place every node inside the canvas on the 8px grid`, () => {
    const nodes = d.nodes.map((n) => n.id).sort()
    const edges = new Set(d.edges.map((e) => e.id))
    for (const layout of [d.wide, d.tall]) {
      assert.deepEqual(Object.keys(layout.nodes).sort(), nodes)
      for (const [id, b] of Object.entries(layout.nodes)) {
        assert.ok(b.x >= 0 && b.y >= 0 && b.x + b.w <= layout.width && b.y + b.h <= layout.height, id)
        assert.ok([b.x, b.y, b.w, b.h].every((v) => v % 8 === 0), `${id} is on the grid`)
      }
      for (const id of [...Object.keys(layout.bends ?? {}), ...Object.keys(layout.labels ?? {})]) {
        assert.ok(edges.has(id), `${id} is an edge`)
      }
    }
    assert.ok(d.tall.width <= 384, 'the tall layout fits a phone at about 14px labels')
  })

  test(`${d.id}: no dash or arrow characters in any label`, () => {
    const text = JSON.stringify([d.nodes, d.edges, d.title, d.desc])
    const banned = [0x2013, 0x2014, 0x2192].map((c) => String.fromCharCode(c))
    assert.ok(!banned.some((ch) => text.includes(ch)))
  })
}

test('every architecture node names its module and a status word', () => {
  for (const n of ARCHITECTURE.nodes) {
    assert.ok(n.module && n.detail, n.id)
    assert.ok(['Built and measured', 'Built', 'Not built'].includes(n.status ?? ''), n.id)
  }
})
