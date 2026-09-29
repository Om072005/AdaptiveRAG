// Number formats from 02_DESIGN_SYSTEM.md section 2. Values are shown as measured, never rounded into claims.

/** USD with at most 5 decimals, trailing zeros trimmed: $0.00031, $0.0012, $0 */
export function money(usd: number): string {
  if (usd === 0) return '$0'
  const text = usd.toFixed(5).replace(/0+$/, '').replace(/\.$/, '')
  return text === '0' ? '< $0.00001' : `$${text}`
}

/** ms below one second, seconds with one decimal above: 340 ms, 1.8 s */
export function duration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`
}

/** A share in 0..1 as a percent with one decimal: 81.3% */
export function percent(share: number): string {
  return `${(share * 100).toFixed(1)}%`
}

/** A score in 0..1 with two decimals. */
export function score(value: number): string {
  return value.toFixed(2)
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** ISO date to 29 Sep 2026, in UTC so every reader sees the recording date the same way. */
export function day(iso: string): string {
  const d = new Date(iso)
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}
