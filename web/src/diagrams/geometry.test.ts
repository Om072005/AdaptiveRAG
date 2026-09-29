import assert from 'node:assert/strict'
import { test } from 'node:test'
import { anchor, diamond, labelPoint, pathD, route } from './geometry.ts'
import type { Box } from './types.ts'

const A: Box = { x: 0, y: 0, w: 100, h: 40 }

test('a node below is reached straight down when centers line up, else with one elbow', () => {
  assert.deepEqual(route(A, 'step', { x: 0, y: 100, w: 100, h: 40 }, 'step'), [
    [50, 40],
    [50, 100],
  ])
  assert.deepEqual(route(A, 'step', { x: 200, y: 100, w: 100, h: 40 }, 'step'), [
    [50, 40],
    [50, 70],
    [250, 70],
    [250, 100],
  ])
})

test('a node beside is reached from the facing side', () => {
  assert.deepEqual(route(A, 'step', { x: 200, y: 0, w: 60, h: 40 }, 'step'), [
    [100, 20],
    [200, 20],
  ])
  assert.deepEqual(route({ x: 200, y: 0, w: 60, h: 40 }, 'step', A, 'step'), [
    [200, 20],
    [100, 20],
  ])
})

test('bends are kept and the ends meet the facing sides', () => {
  const pts = route(A, 'step', { x: 300, y: 200, w: 100, h: 40 }, 'step', [
    [80, -20],
    [350, -20],
  ])
  assert.deepEqual(pts, [
    [80, 0],
    [80, -20],
    [350, -20],
    [350, 0 + 200],
  ])
})

test('a decision is always met at a corner of its diamond', () => {
  const d: Box = { x: 0, y: 0, w: 120, h: 80 }
  assert.deepEqual(anchor(d, 'decision', [20, 200]), [60, 80])
  assert.deepEqual(anchor(d, 'decision', [300, 5]), [120, 40])
  assert.deepEqual(anchor(d, 'decision', [-50, 70]), [0, 40])
  assert.equal(diamond(d), '60,0 120,40 60,80 0,40')
})

test('corners are rounded with at most 8px and never past half a short segment', () => {
  assert.equal(pathD([[0, 0], [0, 100]]), 'M0 0 L0 100')
  assert.equal(pathD([[0, 0], [0, 100], [50, 100]]), 'M0 0 L0 92 Q0 100 8 100 L50 100')
  assert.equal(pathD([[0, 0], [0, 6], [50, 6]]), 'M0 0 L0 3 Q0 6 3 6 L50 6')
})

test('labels sit in the middle of the longest segment', () => {
  assert.deepEqual(
    labelPoint([
      [0, 0],
      [0, 10],
      [100, 10],
      [100, 20],
    ]),
    [50, 10],
  )
})
