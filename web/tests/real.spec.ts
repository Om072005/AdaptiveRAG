import { expect, test } from '@playwright/test'

// The release build: every pinned table and every recorded replay must render from real data.
for (const width of [375, 768, 1280]) {
  test(`real data renders at ${width}px with no sample or missing data`, async ({ page, baseURL }) => {
    const problems: string[] = []
    const origin = new URL(baseURL ?? 'http://localhost').origin
    page.on('console', (m) => m.type() === 'error' && problems.push(m.text()))
    page.on('pageerror', (e) => problems.push(e.message))
    page.on('request', (r) => new URL(r.url()).origin !== origin && !r.url().startsWith('data:') && problems.push(`foreign ${r.url()}`))
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await expect(page.getByText(/Sample data/)).toHaveCount(0)
    await expect(page.getByText('20260930-1557-test-auto-baseline').first()).toBeAttached()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    expect(problems).toEqual([])
  })
}

test('every recorded replay steps through all six stages', async ({ page }) => {
  await page.goto('/')
  const replays = page.getByRole('button', { name: /(Correct|Partial|Wrong|Misrouted)$/ })
  await expect(replays.first()).toBeVisible()
  const n = await replays.count()
  expect(n).toBeGreaterThanOrEqual(12)
  for (let i = 0; i < n; i++) {
    await replays.nth(i).click()
    for (let s = 0; s < 5; s++) await page.getByRole('button', { name: 'Next step' }).click()
    await expect(page.getByRole('button', { name: 'Next step' })).toBeDisabled()
  }
})
