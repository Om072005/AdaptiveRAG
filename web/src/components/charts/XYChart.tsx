import { TipBody } from './TipBody'
import { useTooltip } from './Tooltip'

export type XYPoint = { x: number; y: number; label?: string; tip?: [string, string][]; hollow?: boolean }
export type XYSeries = {
  id: string
  name: string
  fill: string // fill-* class for the markers
  stroke: string // stroke-* class for the line
  line?: boolean // join the points in x order
  dash?: string
  points: XYPoint[]
}

const M = { left: 52, right: 24, top: 28, bottom: 52 }
const LABEL_H = 16

type Placed = { key: string; x: number; y: number; right: boolean; w: number }

/** Direct labels beside their points, nudged down where two would overlap. */
function placeLabels(items: { key: string; cx: number; cy: number; text: string }[], width: number): Map<string, Placed> {
  const placed: Placed[] = []
  for (const it of [...items].sort((a, b) => a.cy - b.cy)) {
    const w = it.text.length * 6.6
    const right = it.cx + 11 + w < width - 8
    let y = it.cy + 4
    const x0 = right ? it.cx + 11 : it.cx - 11 - w
    for (;;) {
      const clash = placed.find((p) => Math.abs(p.y - y) < LABEL_H && x0 < (p.right ? p.x + p.w : p.x) && x0 + w > (p.right ? p.x : p.x - p.w))
      if (!clash) break
      y = clash.y + LABEL_H
    }
    placed.push({ key: it.key, x: right ? it.cx + 11 : it.cx - 11, y, right, w })
  }
  return new Map(placed.map((p) => [p.key, p]))
}

function logTicks(lo: number, hi: number): number[] {
  const out: number[] = []
  for (let p = Math.floor(Math.log10(lo)); p <= Math.ceil(Math.log10(hi)); p++) out.push(10 ** p)
  const inside = out.filter((t) => t >= lo && t <= hi)
  // a domain inside one decade still gets its two ends as ticks
  return inside.length >= 2 ? inside : [lo, hi]
}

/** A domain that can be drawn: positive on a log axis, and never zero wide (one point, equal values). */
function safeDomain([lo, hi]: [number, number], log: boolean): [number, number] {
  if (log) {
    const a = Math.max(Number.isFinite(lo) ? lo : 1, 1e-9)
    const b = Math.max(Number.isFinite(hi) ? hi : a, a)
    return b / a < 1.0001 ? [a / 10, b * 10] : [a, b]
  }
  const a = Number.isFinite(lo) ? lo : 0
  const b = Number.isFinite(hi) ? hi : 1
  return b > a ? [a, b] : [a - 0.05, a + 0.05]
}

function linTicks(lo: number, hi: number, n = 5): number[] {
  return Array.from({ length: n }, (_, i) => lo + (i * (hi - lo)) / (n - 1))
}

/** Points on two axes, optionally joined into lines; direct labels where given, a tooltip on every point. */
export function XYChart({ wide = false, series, xLog = false, xDomain, yDomain, xLabel, yLabel, formatX, formatY, title, reference }: {
  series: XYSeries[]
  xLog?: boolean
  xDomain: [number, number]
  yDomain: [number, number]
  xLabel: string
  yLabel: string
  formatX: (v: number) => string
  formatY: (v: number) => string
  title: string
  reference?: { y: number; label: string }
  wide?: boolean // drawn for a full width card: a wider canvas, so text keeps its size
}) {
  const W = wide ? 960 : 640
  const H = wide ? 360 : 340
  const { box, show, showAt, hide, layer } = useTooltip()
  const xd = safeDomain(xDomain, xLog)
  const yd = safeDomain(yDomain, false)
  const [x0, x1] = xLog ? [Math.log10(xd[0]), Math.log10(xd[1])] : xd
  const px = (v: number) => M.left + (((xLog ? Math.log10(v) : v) - x0) / (x1 - x0)) * (W - M.left - M.right)
  const py = (v: number) => H - M.bottom - ((v - yd[0]) / (yd[1] - yd[0])) * (H - M.top - M.bottom)
  const xt = xLog ? logTicks(xd[0], xd[1]) : linTicks(...xd)
  const yt = linTicks(...yd, 6)

  return (
    <div ref={box} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className={`block h-auto w-full ${wide ? 'min-w-[640px]' : 'min-w-[520px]'}`} shapeRendering="geometricPrecision">
        {yt.map((t) => (
          <g key={`y${t}`}>
            <line x1={M.left} x2={W - M.right} y1={py(t)} y2={py(t)} className="stroke-rule" strokeWidth="1" />
            <text x={M.left - 10} y={py(t) + 4} textAnchor="end" className="fill-muted font-sans text-[12px] tabular-nums">
              {formatY(t)}
            </text>
          </g>
        ))}
        {xt.map((t) => (
          <text key={`x${t}`} x={px(t)} y={H - M.bottom + 20} textAnchor="middle" className="fill-muted font-sans text-[12px] tabular-nums">
            {formatX(t)}
          </text>
        ))}
        <line x1={M.left} x2={W - M.right} y1={H - M.bottom} y2={H - M.bottom} className="stroke-line" strokeWidth="1" />
        <text x={(M.left + W - M.right) / 2} y={H - 10} textAnchor="middle" className="fill-muted font-sans text-[12.5px]">
          {xLabel}
        </text>
        <text x={M.left} y={M.top - 6} className="fill-muted font-sans text-[12.5px]">
          {yLabel}
        </text>
        {reference && (
          <g>
            <line x1={M.left} x2={W - M.right} y1={py(reference.y)} y2={py(reference.y)} className="stroke-line" strokeWidth="1" strokeDasharray="4 4" />
            <text x={W - M.right} y={py(reference.y) - 6} textAnchor="end" className="fill-muted font-sans text-[12px]">
              {reference.label}
            </text>
          </g>
        )}
        {(() => {
          const labels = placeLabels(
            series.flatMap((s) => (s.line ? [] : s.points.flatMap((p, i) => (p.label ? [{ key: `${s.id}${i}`, cx: px(p.x), cy: py(p.y), text: p.label }] : [])))),
            W,
          )
          return series.map((s) => {
          const pts = [...s.points].sort((a, b) => a.x - b.x)
          return (
            <g key={s.id}>
              {s.line && (
                <polyline
                  points={pts.map((p) => `${px(p.x)},${py(p.y)}`).join(' ')}
                  fill="none"
                  className={s.stroke}
                  strokeWidth="2"
                  strokeDasharray={s.dash}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              )}
              {pts.map((p, i) => {
                const cx = px(p.x)
                const cy = py(p.y)
                const tip = <TipBody title={p.label ?? s.name} rows={[[xLabel, formatX(p.x)], [yLabel, formatY(p.y)], ...(p.tip ?? [])]} />
                const lab = labels.get(`${s.id}${s.points.indexOf(p)}`)
                return (
                  <g
                    key={`${s.id}${i}`}
                    tabIndex={0}
                    role="img"
                    aria-label={`${p.label ?? s.name}: ${xLabel} ${formatX(p.x)}, ${yLabel} ${formatY(p.y)}`}
                    onKeyDown={(e) => e.key === 'Escape' && hide()}
                    className="cursor-default outline-none [&:focus-visible>circle:nth-child(2)]:stroke-accent"
                    onMouseMove={(e) => show(e, tip)}
                    onMouseLeave={hide}
                    onFocus={(e) => showAt(e.currentTarget, tip)}
                    onBlur={hide}
                  >
                    <circle cx={cx} cy={cy} r="14" fill="transparent" />
                    <circle
                      cx={cx}
                      cy={cy}
                      r="5.5"
                      className={`${p.hollow ? 'fill-surface' : s.fill} ${p.hollow ? s.stroke : 'stroke-surface'}`}
                      strokeWidth="2"
                    />
                    {p.label && lab && (
                      <text x={lab.x} y={lab.y} textAnchor={lab.right ? 'start' : 'end'} className="fill-text font-sans text-[12.5px] font-[500]">
                        {p.label}
                      </text>
                    )}
                  </g>
                )
              })}
            </g>
          )
        })
        })()}
      </svg>
      {layer}
    </div>
  )
}
