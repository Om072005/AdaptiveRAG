import { AxeBuilder } from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

for (const width of [320, 375, 768, 1280]) {
  test(`no page level horizontal scroll at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await expect(page.locator('#results figure').first()).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBe(0)
  })
}

for (const [width, scheme] of [[375, 'light'], [1280, 'light'], [1280, 'dark']] as const) {
  test(`no serious accessibility violations at ${width}px in ${scheme} mode`, async ({ page }) => {
    // entrance fades run at reduced opacity; reduced motion shows every element in its final state
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: 'reduce' })
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await expect(page.locator('#results figure').first()).toBeVisible()
    await page.waitForLoadState('networkidle')
    const result = await new AxeBuilder({ page }).analyze()
    const serious = result.violations
      .filter((v) => v.impact === 'serious' || v.impact === 'critical')
      .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).slice(0, 3).join(', ')}`)
    expect(serious).toEqual([])
  })
}
