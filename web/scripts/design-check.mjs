// The mechanical rules of 02_DESIGN_SYSTEM.md section 10. Run from web/:
// colors and fonts come from tokens.css only, so both themes stay complete; copy keeps its style.
//   node scripts/design-check.mjs          source rules on src/ and index.html
//   node scripts/design-check.mjs --data   refuse sample data in public/ unless VITE_ALLOW_SAMPLE=1
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const TOKENS = join('src', 'styles', 'tokens.css')
const FONTS = ['Paper Serif', 'Bahnschrift', 'Barlow Condensed', 'sans-serif', 'IBM Plex Mono']
const RULES = [
  [/→/, 'arrow glyph'],
  [/—|–/, 'em or en dash'],
]
const COLOR = /#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(/gi
const FONT_NAME = /font-family\s*:\s*([^;}]+)|--font-[a-z]+\s*:\s*([^;}]+)/gi

function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? files(path) : [path]
  })
}

function sourceProblems(path, text) {
  const found = RULES.filter(([re]) => re.test(text)).map(([, why]) => why)
  if (path !== TOKENS) {
    const colors = text.match(COLOR)
    if (colors) found.push(`color outside tokens.css: ${[...new Set(colors)].join(' ')}`)
    for (const m of text.matchAll(FONT_NAME)) {
      const names = (m[1] ?? m[2]).split(',').map((s) => s.trim().replace(/['"]/g, ''))
      if (!names.every((n) => n.startsWith('var(') || FONTS.includes(n))) {
        found.push(`font family outside tokens.css: ${names.join(', ')}`)
      }
    }
  }
  return found
}

function checkSource() {
  const targets = [...files('src'), 'index.html'].filter((p) => /\.(tsx?|css|html|json|svg)$/.test(p))
  return targets.flatMap((p) =>
    sourceProblems(p, readFileSync(p, 'utf8')).map((why) => `${relative('.', p)}: ${why}`),
  )
}

function checkData() {
  if (process.env.VITE_ALLOW_SAMPLE === '1') return []
  let found = []
  try {
    found = files('public').filter((p) => p.endsWith('.json'))
  } catch {
    return []
  }
  // *.sample.json files are stripped from a production build, everything else ships
  return found
    .filter((p) => !p.endsWith('.sample.json') && JSON.parse(readFileSync(p, 'utf8')).sample === true)
    .map((p) => `${relative('.', p)}: sample data in a production build (set VITE_ALLOW_SAMPLE=1 only locally)`)
}

const problems = process.argv.includes('--data') ? checkData() : checkSource()
if (problems.length) {
  console.error(`design check failed:\n  ${problems.join('\n  ')}`)
  process.exit(1)
}
