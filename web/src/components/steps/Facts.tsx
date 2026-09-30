import type { ReactNode } from 'react'

/** Label and value tiles for a stage's facts. */
export function Facts({ items, cols = 3 }: { items: [string, ReactNode][]; cols?: 2 | 3 }) {
  return (
    <dl className={`m-0 grid gap-3 ${cols === 3 ? 'grid-cols-2 sm:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2'}`}>
      {items.map(([k, v]) => (
        <div key={k} className="rounded-[12px] border border-rule bg-sunken p-4">
          <dt className="text-caption">{k}</dt>
          <dd className="m-0 mt-1 text-[15px] leading-6 font-[560] text-ink">{v}</dd>
        </div>
      ))}
    </dl>
  )
}
