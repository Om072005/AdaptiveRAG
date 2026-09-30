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
  await expect(page.locator('article').getByText(/Recorded run/)).toContainText('20260101-0000-dev-vector-sample')

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
  await expect(page.getByRole('listitem').filter({ hasText: 'Sample snippet.' })).toHaveClass(/border-accent/)
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
  await expect(page.locator('article').getByText('Question type', { exact: true })).toBeVisible()
  await expect(page.getByRole('img', { name: 'Confidence 0.50 of 1' })).toBeVisible()
  await page.getByRole('button', { name: 'Next step' }).click()
  await expect(page.getByText('This run asked for vector search, so the router did not choose.')).toBeVisible()
  await expect(page.locator('article').getByText('Route taken')).toBeVisible()
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
  const panel = page.locator('article')
  await expect(panel.getByText('Router', { exact: true })).toBeVisible()
  await expect(panel.getByText('Vector only')).toBeVisible()
  await expect(panel.getByText('Hybrid only')).toBeVisible()
  await expect(panel.getByText('Best', { exact: true })).toHaveCount(1)
})

test('the replay only build has no question box', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByLabel('Ask your own question')).toHaveCount(0)
})

test('recorded judge scores and the review queue note', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Sample single hop question/ }).click()
  await page.getByRole('button', { name: '5 Answer' }).click()
  const judge = page.getByRole('region', { name: 'Judge scores' })
  await expect(judge.getByRole('img', { name: 'Relevance 0.50 of 1' })).toBeVisible()
  await expect(judge).toContainText('Below the threshold, so it waits in the review queue.')
  await expect(judge.getByRole('button', { name: 'Judge this answer' })).toHaveCount(0)
})

test('run it yourself: copy buttons, and the team from site content', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('/')
  const run = page.locator('#run')
  await expect(run.locator('pre')).toHaveCount(8)
  await run.getByRole('button', { name: 'Copy' }).first().click()
  await expect(run.getByRole('button', { name: 'Copied' })).toHaveCount(1)
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('git clone')
  const team = page.locator('#team')
  await expect(team.getByText('Dhruvvv13')).toBeVisible()
  await expect(team.locator('li')).toHaveCount(4)
  await expect(team.getByRole('link', { name: 'Open an issue' })).toHaveAttribute('href', 'https://github.com/Om072005/AdaptiveRAG/issues')
})

test('workflows show all four README workflows, one tab at a time', async ({ page }) => {
  await page.goto('/')
  const flows = page.locator('#workflows')
  for (const name of ['Ingestion', 'Router decision logic', 'Graph schema', 'Evaluation loop']) {
    await flows.getByRole('tab', { name }).click()
    await expect(flows.getByRole('tab', { name })).toHaveAttribute('aria-selected', 'true')
    await expect(flows.getByRole('heading', { name })).toBeVisible()
  }
})

test('a workflow step lights its part of the diagram', async ({ page }) => {
  await page.goto('/')
  const flows = page.locator('#workflows')
  const step = flows.getByRole('button', { name: /Check facts/ })
  await step.click()
  await expect(step).toHaveAttribute('aria-pressed', 'true')
  await expect(flows.getByText('Step 4: Check facts')).toBeVisible()
  await flows.getByRole('tab', { name: 'Evaluation loop' }).click()
  await expect(flows.getByText('Pick a step or play the walkthrough. Select any box for detail.')).toBeVisible()
})

test('the theme toggle switches to dark and back, and is remembered', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/')
  await page.getByRole('button', { name: 'Switch to dark mode' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: 'Switch to light mode' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
})

test('a results chart switches to its table', async ({ page }) => {
  await page.goto('/')
  const card = page.locator('#results figure').first()
  await card.getByRole('button', { name: 'Table' }).click()
  await expect(card.getByRole('columnheader', { name: 'Faithfulness' })).toBeVisible()
})

test('a diagram node opens its detail and module path', async ({ page }) => {
  await page.goto('/')
  const node = page.getByRole('button', { name: 'Model selector: small or large' })
  await node.scrollIntoViewIfNeeded()
  await node.click()
  await expect(node).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText(/labels multi hop or comparison/)).toBeVisible()
  await expect(page.getByText('adaptiverag/generate/select.py')).toBeVisible()
})

test('the page requests nothing but its own files', async ({ page, baseURL }) => {
  const origin = new URL(baseURL ?? 'http://localhost').origin
  const foreign: string[] = []
  page.on('request', (r) => {
    const url = new URL(r.url())
    if (url.protocol !== 'data:' && url.origin !== origin) foreign.push(r.url())
  })
  await page.goto('/')
  await page.mouse.wheel(0, 20000)
  await page.waitForLoadState('networkidle')
  expect(foreign).toEqual([])
})

test('the journey: a route up front, a close on every chapter, and a recap of what was read', async ({ page }) => {
  await page.goto('/')
  const route = page.locator('#route')
  await expect(route.getByRole('heading', { name: 'Your route through this page' })).toBeVisible()
  await expect(route.getByRole('listitem')).toHaveCount(8)
  await expect(page.locator('[data-chapter-end]')).toHaveCount(8)

  // before any reading the recap marks everything skipped
  const recap = page.locator('#recap')
  await expect(recap).toContainText('0 read')

  // follow the first chapter's close to the next one, reading chapter one on the way
  await page.locator('#idea').scrollIntoViewIfNeeded()
  const end = page.locator('[data-chapter-end="idea"]')
  await end.scrollIntoViewIfNeeded()
  await end.getByRole('link', { name: /How it works/ }).click()
  await expect(page).toHaveURL(/#how$/)
  await expect(page.getByLabel('Journey progress')).toContainText('The idea: read')
  await expect(recap).toContainText('1 read')
  await expect(recap.getByRole('listitem').first()).toContainText('Read')
})
