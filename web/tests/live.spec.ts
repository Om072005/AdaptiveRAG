import { expect, test } from '@playwright/test'
import multi from '../public/data/replays/sample_multi.sample.json' with { type: 'json' }

test('a live answer renders in the replay panel with its trace id', async ({ page }) => {
  const response = { ...multi.runs.auto.response, trace_id: 'live-trace-1', question: 'Who founded Acme Rockets?' }
  let asked: unknown = null
  await page.route('**/api/query', async (route) => {
    asked = route.request().postDataJSON()
    await route.fulfill({ json: response })
  })
  await page.goto('/')
  await page.getByLabel('Ask your own question').fill('Who founded Acme Rockets?')
  await page.getByRole('button', { name: 'Ask' }).click()
  await expect(page.locator('#qtitle')).toHaveText('Who founded Acme Rockets?')
  await expect(page.getByText('Live answer, trace')).toContainText('live-trace-1')
  expect(asked).toEqual({ question: 'Who founded Acme Rockets?', mode: 'auto' })
  await page.getByRole('button', { name: '5 Answer' }).click()
  await expect(page.getByText('Gold answer')).toHaveCount(0)
})

test('an API error is shown, not thrown', async ({ page }) => {
  await page.route('**/api/query', (route) =>
    route.fulfill({ status: 429, json: { error: { message: 'Too many questions right now. Try a recorded run below.', fields: null } } }),
  )
  await page.goto('/')
  await page.getByLabel('Ask your own question').fill('Who founded Acme Rockets?')
  await page.getByRole('button', { name: 'Ask' }).click()
  await expect(page.getByRole('alert')).toHaveText('Too many questions right now. Try a recorded run below.')
})

test('the judge button asks the API and shows the queued state', async ({ page }) => {
  const response = { ...multi.runs.auto.response, trace_id: 'live-trace-2', question: 'Who founded Acme Rockets?' }
  await page.route('**/api/query', (route) => route.fulfill({ json: response }))
  let judged: unknown = null
  await page.route('**/api/judge', async (route) => {
    judged = route.request().postDataJSON()
    await route.fulfill({
      json: { faithfulness: 0.25, relevance: 1, completeness: 1, rationale: 'Not grounded.', cost_usd: 0.0004, flagged: true, queued: true },
    })
  })
  await page.goto('/')
  await page.getByLabel('Ask your own question').fill('Who founded Acme Rockets?')
  await page.getByRole('button', { name: 'Ask' }).click()
  await page.getByRole('button', { name: '5 Answer' }).click()
  await page.getByRole('button', { name: 'Judge this answer' }).click()
  await expect(page.getByText('Below the threshold, so it waits in the review queue.')).toBeVisible()
  expect(judged).toEqual({ trace_id: 'live-trace-2' })
})

test('a streamed answer shows each step, the reasoning and the answer as they arrive', async ({ page }) => {
  const response = { ...multi.runs.auto.response, trace_id: 'live-trace-3', question: 'Who founded Acme Rockets?' }
  const lines = [
    { type: 'step', step: 'embed', at_ms: 40, model: 'nomic-embed-text', dims: 768, cached: false, ms: 40 },
    { type: 'step', step: 'classify', at_ms: 45, label: 'multi_hop', confidence: 0.9, method: 'logreg', min_confidence: 0.85, probs: { multi_hop: 0.9 } },
    { type: 'step', step: 'model', at_ms: 900, size: 'small', model: 'gpt-oss:20b', reason: 'small:route hybrid' },
    { type: 'delta', kind: 'thinking', text: 'The founder is named in [1].' },
    { type: 'delta', kind: 'answer', text: 'Answer: Jane Roe' },
    { type: 'step', step: 'generated', at_ms: 5000, model: 'gpt-oss:20b', tokens_in: 900, tokens_out: 40, ms: 4000, cached: false, processor: '100% GPU' },
    { type: 'done', response },
  ]
  let asked: unknown = null
  await page.route('**/api/query/stream', async (route) => {
    asked = route.request().postDataJSON()
    await route.fulfill({ contentType: 'application/x-ndjson', body: lines.map((l) => JSON.stringify(l)).join('\n') + '\n' })
  })
  await page.goto('/')
  await page.getByLabel('Ask your own question').fill('Who founded Acme Rockets?')
  await page.getByRole('button', { name: 'Ask' }).click()
  const live = page.getByRole('region', { name: 'Live steps' })
  await expect(live).toContainText('multi_hop at 0.90 (logreg; trusted 0.85)')
  await expect(live).toContainText('The founder is named in [1].')
  await expect(live).toContainText('Answer: Jane Roe')
  await expect(live).toContainText('900 tokens in, 40 out, 4.0 s, 100% GPU')
  await expect(page.getByText('Live answer, trace')).toContainText('live-trace-3')
  expect(asked).toEqual({ question: 'Who founded Acme Rockets?', mode: 'auto' })
})

test('an error in the stream is shown, not thrown', async ({ page }) => {
  const lines = [{ type: 'error', message: 'gpt-oss:20b: provider busy (503), resume later' }]
  await page.route('**/api/query/stream', (route) =>
    route.fulfill({ contentType: 'application/x-ndjson', body: lines.map((l) => JSON.stringify(l)).join('\n') + '\n' }),
  )
  await page.goto('/')
  await page.getByLabel('Ask your own question').fill('Who founded Acme Rockets?')
  await page.getByRole('button', { name: 'Ask' }).click()
  await expect(page.getByRole('alert')).toHaveText('gpt-oss:20b: provider busy (503), resume later')
})
