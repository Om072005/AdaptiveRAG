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
