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
