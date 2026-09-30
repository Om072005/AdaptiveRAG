import { TipBody } from './TipBody'
import { useTooltip } from './Tooltip'

export type Bar = {
  id: string
  label: string
  value: number
  color: string // a bg-* class from copy/routes
  strong?: boolean // the bar the chart is about: its label and value in ink weight
  tip?: [string, string][]
}

/** Horizontal bars from one baseline, value at the tip, a tooltip with the rest of the row on hover. */
export function BarList({ bars, max, format, thin = false, labelWidth = 'minmax(88px,max-content)' }: {
  bars: Bar[]
  max: number
  format: (v: number) => string
  thin?: boolean
  labelWidth?: string
}) {
  const { box, show, showAt, hide, layer } = useTooltip()
  return (
    <div ref={box} className="relative">
      <ul className="m-0 grid list-none items-center gap-x-4 gap-y-2.5 p-0" style={{ gridTemplateColumns: `${labelWidth} minmax(0,1fr)` }}>
        {bars.map((b) => {
          const tip = <TipBody title={b.label} rows={[['Value', format(b.value)], ...(b.tip ?? [])]} />
          return (
            <li key={b.id} className="contents">
              <span className={`text-[14px] leading-5 ${b.strong ? 'font-[620] text-ink' : 'text-text'}`}>{b.label}</span>
              <span
                className="flex min-w-0 items-center gap-2.5 border-l border-line py-0.5 outline-none"
                tabIndex={0}
                role="img"
                aria-label={`${b.label}: ${format(b.value)}${(b.tip ?? []).map(([k, v]) => `, ${k} ${v}`).join('')}`}
                onKeyDown={(e) => e.key === 'Escape' && hide()}
                onMouseMove={(e) => show(e, tip)}
                onMouseLeave={hide}
                onFocus={(e) => showAt(e.currentTarget, tip)}
                onBlur={hide}
              >
                <span
                  className={`block shrink-0 rounded-r-[4px] transition-[width] duration-500 ease-page ${b.color} ${thin ? 'h-3' : 'h-5'}`}
                  style={{ width: `calc((100% - 64px) * ${max > 0 ? Math.max(0, Math.min(1, b.value / max)) : 0})`, minWidth: 2 }}
                />
                <span className={`text-[13.5px] leading-5 tabular-nums ${b.strong ? 'font-[650] text-ink' : 'text-muted'}`}>{format(b.value)}</span>
              </span>
            </li>
          )
        })}
      </ul>
      {layer}
    </div>
  )
}
