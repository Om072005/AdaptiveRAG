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
