export type Point = { x: number; y: number; label: string; filled: boolean }

const W = 640
const H = 360
const M = { left: 56, right: 40, top: 32, bottom: 48 }

function ticks(min: number, max: number): number[] {
  return [0, 0.25, 0.5, 0.75, 1].map((f) => min + f * (max - min))
}

/** Labelled points on two axes; filled and hollow points carry the meaning, never color. */
export function Scatter({ points, xLabel, yLabel, formatX, formatY, title }: {
  points: Point[]
  xLabel: string
  yLabel: string
  formatX: (v: number) => string
  formatY: (v: number) => string
  title: string
}) {
  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const [x0, x1] = [0, Math.max(...xs, 0) * 1.1 || 1]
  const [y0, y1] = [Math.min(0, ...ys), Math.max(1, ...ys)]
  const px = (v: number) => M.left + ((v - x0) / (x1 - x0)) * (W - M.left - M.right)
  const py = (v: number) => H - M.bottom - ((v - y0) / (y1 - y0)) * (H - M.top - M.bottom)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className="block h-auto w-full max-w-[720px] min-w-[480px]">
      <line x1={M.left} y1={H - M.bottom} x2={W - M.right} y2={H - M.bottom} className="stroke-cream-600" strokeWidth="1" />
      <line x1={M.left} y1={M.top} x2={M.left} y2={H - M.bottom} className="stroke-cream-600" strokeWidth="1" />
      {ticks(x0, x1).map((t) => (
        <text key={`x${t}`} x={px(t)} y={H - M.bottom + 18} textAnchor={t === x1 ? 'end' : 'middle'} className="fill-muted font-sans text-[12px]">
          {formatX(t)}
        </text>
      ))}
      {ticks(y0, y1).map((t) => (
        <text key={`y${t}`} x={M.left - 8} y={py(t) + 4} textAnchor="end" className="fill-muted font-sans text-[12px]">
          {formatY(t)}
        </text>
      ))}
      <text x={(M.left + W - M.right) / 2} y={H - 8} textAnchor="middle" className="fill-muted font-sans text-[13px]">
        {xLabel}
      </text>
      <text x="14" y={(M.top + H - M.bottom) / 2} textAnchor="middle" transform={`rotate(-90 14 ${(M.top + H - M.bottom) / 2})`} className="fill-muted font-sans text-[13px]">
        {yLabel}
      </text>
      {points.map((p) => (
        <g key={p.label}>
          <circle
            cx={px(p.x)}
            cy={py(p.y)}
            r="5"
            className={p.filled ? 'fill-cream-300 stroke-cream-300' : 'fill-black stroke-cream-300'}
            strokeWidth="1.5"
          />
          <text
            x={px(p.x) > W - 160 ? px(p.x) - 10 : px(p.x) + 10}
            y={py(p.y) - 8}
            textAnchor={px(p.x) > W - 160 ? 'end' : 'start'}
            className="fill-cream-300 font-sans text-[13px]"
          >
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  )
}
