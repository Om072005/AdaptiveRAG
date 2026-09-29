import { expect, type Page, test } from '@playwright/test'

function watchConsole(page: Page): string[] {
  const errors: string[] = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('requestfailed', (r) => errors.push(`failed ${r.url()}`))
  page.on('response', (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`))
  return errors
}

const current = (page: Page) => page.getByRole('list', { name: 'Stages' }).locator('[aria-current="step"]')

test('replay list, panel and every way to move between stages', async ({ page }) => {
  const errors = watchConsole(page)
  await page.goto('/')
  await expect(page.getByText('Sample data. Numbers on this build are placeholders.')).toBeVisible()

  await page.getByRole('button', { name: /Sample multi hop question/ }).click()
  await expect(page.locator('#qtitle')).toHaveText(/Sample multi hop question/)
  await expect(page.getByText(/Recorded run/)).toContainText('20260101-0000-dev-vector-sample')

  await expect(current(page)).toHaveText('1 Classify')
  await page.getByRole('button', { name: 'Next step' }).click()
  await expect(current(page)).toHaveText('2 Route')
  await page.getByRole('button', { name: 'Previous step' }).click()
  await expect(current(page)).toHaveText('1 Classify')

  await page.getByRole('button', { name: '5 Answer' }).click()
  await expect(current(page)).toHaveText('5 Answer')
  await page.keyboard.press('ArrowRight')
  await expect(current(page)).toHaveText('6 Cost')
  await expect(page.getByRole('button', { name: 'Next step' })).toBeDisabled()
  await page.keyboard.press('ArrowLeft')
  await expect(current(page)).toHaveText('5 Answer')

  await page.getByRole('tab', { name: 'Every route' }).click()
  await expect(page.getByRole('tab', { name: 'Every route' })).toHaveAttribute('aria-selected', 'true')
  expect(errors).toEqual([])
})

test('went wrong questions are grouped with their outcome word', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Went wrong' })).toBeVisible()
  await expect(page.getByRole('button', { name: /which is older.*Misrouted/ })).toBeVisible()
})

test('answer step: citation marker highlights its source, gold answer and scores', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Sample single hop question/ }).click()
  await page.getByRole('button', { name: '5 Answer' }).click()
  await expect(page.getByText('Sample answer', { exact: true }).first()).toBeVisible()
  const marker = page.getByRole('button', { name: 'Source 1' })
  await marker.click()
  await expect(marker).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('listitem').filter({ hasText: 'Sample snippet.' })).toHaveClass(/border-cream-100/)
  await expect(page.getByText('Gold answer')).toBeVisible()
  await expect(page.getByText('Token F1')).toBeVisible()
})

test('a not enough context answer is shown, in muted text', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /which is older/ }).click()
  await page.getByRole('button', { name: '5 Answer' }).click()
  await expect(page.getByText('Not enough context')).toHaveClass(/text-muted/)
})

test('classify and route steps read the recorded decision', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Sample single hop question/ }).click()
  await expect(page.getByText('Question type')).toBeVisible()
  await expect(page.getByRole('img', { name: 'Confidence 0.50 of 1' })).toBeVisible()
  await page.getByRole('button', { name: 'Next step' }).click()
  await expect(page.getByText('This run asked for vector search, so the router did not choose.')).toBeVisible()
  await expect(page.getByText('Route taken')).toBeVisible()
})

test('retrieve step: graph edge shows the chunk it came from', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Sample multi hop question/ }).click()
  await page.getByRole('button', { name: '3 Retrieve' }).click()
  const edge = page.getByRole('button', { name: 'worked_for, from chunk sample:jane:1' }).first()
  await edge.click()
  await expect(edge).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText('worked_for, confidence 0.80')).toBeVisible()
  await expect(page.locator('.bg-raised').getByText('She later worked for Globex.')).toBeVisible()
})

test('model and cost steps: selector reason, waterfall and the throttle note', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Sample multi hop question/ }).click()
  await page.getByRole('button', { name: '4 Model' }).click()
  await expect(page.getByText('The graph traversal route brings harder context, so the large model answered.')).toBeVisible()
  await page.getByRole('button', { name: '6 Cost' }).click()
  await expect(page.getByRole('img', { name: 'Time per step, 1.1 s in total' })).toBeVisible()
  await expect(page.getByText('$0.0002').first()).toBeVisible()
  await expect(page.getByText('500 ms spent waiting on a provider rate limit is not counted in the time above.')).toBeVisible()
})

test('every route shows each recorded mode and marks the best F1 in words', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Sample multi hop question/ }).click()
  await page.getByRole('tab', { name: 'Every route' }).click()
  await expect(page.getByText('Router', { exact: true })).toBeVisible()
  await expect(page.getByText('Vector only')).toBeVisible()
  await expect(page.getByText('Hybrid only')).toBeVisible()
  await expect(page.getByText('Best', { exact: true })).toHaveCount(1)
})

test('the replay only build has no question box', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByLabel('Ask your own question')).toHaveCount(0)
})
