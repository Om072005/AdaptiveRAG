import { duration } from '../copy/format'

type Span = { name: string; ms: number }

const NAME: Record<string, string> = {
  classify: 'Classify',
  link: 'Link entities',
  retrieve: 'Retrieve',
  merge: 'Merge',
  generate: 'Generate',
  judge: 'Judge',
}

/** Spans in the order they ran, each bar starting where the previous one ended, to scale. */
export function Waterfall({ spans, totalMs }: { spans: Span[]; totalMs: number }) {
  const scale = Math.max(totalMs, spans.reduce((s, x) => s + x.ms, 0), 1)
  const rowH = 32
  const labelW = 136
  const barW = 480
  const rows = spans.map((s, i) => ({ ...s, start: spans.slice(0, i).reduce((sum, x) => sum + x.ms, 0) }))

  return (
    <div>
      <svg
        viewBox={`0 0 ${labelW + barW + 88} ${rows.length * rowH + 8}`}
        role="img"
        aria-label={`Time per step, ${duration(totalMs)} in total`}
        className="hidden h-auto w-full md:block"
      >
        <line x1={labelW} y1="0" x2={labelW} y2={rows.length * rowH + 8} className="stroke-line" strokeWidth="1" />
        {rows.map((r, i) => {
          const x = labelW + (r.start / scale) * barW
          const w = Math.max(1, (r.ms / scale) * barW)
          const y = i * rowH + 8
          return (
            <g key={`${r.name}-${i}`}>
              <text x="0" y={y + 13} className="fill-text font-sans text-[13.5px]">
                {NAME[r.name] ?? r.name}
              </text>
              <rect x={x} y={y + 2} width={w} height="14" rx="3" className="fill-accent" />
              <text x={x + w + 8} y={y + 13} className="fill-muted font-sans text-[13px]">
                {duration(r.ms)}
              </text>
            </g>
          )
        })}
      </svg>
      <ol className="m-0 list-none p-0 md:hidden">
        {rows.map((r, i) => (
          <li key={`${r.name}-${i}`} className="flex justify-between border-b border-rule py-2 text-[15px] leading-6 last:border-b-0">
            <span>{NAME[r.name] ?? r.name}</span>
            <span className="tabular-nums text-muted">{duration(r.ms)}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
