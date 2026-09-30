import { type ReactNode, useState } from 'react'
import { ChartIcon, TableIcon } from '../Icons'
import { RunId } from '../RunId'

export type LegendItem = { label: string; swatch: string } // swatch: a bg-* class

/** A result on its own card: title, the one sentence it shows, legend, the chart or its table, and
 * the split and run ids it came from. */
export function ChartCard({ title, takeaway, legend, chart, table, split, runIds, note, wide = false }: {
  title: string
  takeaway?: ReactNode
  legend?: LegendItem[]
  chart?: ReactNode // without one the table is the figure
  table?: ReactNode
  split?: string
  runIds: string[]
  note?: ReactNode
  wide?: boolean
}) {
  const [asTable, setAsTable] = useState(false)
  const showTable = !chart || asTable
  return (
    <figure className={`card m-0 flex min-w-0 flex-col p-5 md:p-7 ${wide ? 'lg:col-span-2' : ''}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 max-w-[60ch]">
          <h3 className="text-title m-0">{title}</h3>
          {takeaway && <p className="text-small m-0 mt-1.5 text-text">{takeaway}</p>}
        </div>
        {chart && table && (
          <div role="group" aria-label="View" className="inline-flex shrink-0 rounded-[2px] border border-rule bg-sunken p-0.5">
            {[
              [false, 'Chart', <ChartIcon key="c" size={15} />],
              [true, 'Table', <TableIcon key="t" size={15} />],
            ].map(([value, label, icon]) => (
              <button
                key={label as string}
                type="button"
                aria-pressed={asTable === value}
                onClick={() => setAsTable(value as boolean)}
                className="inline-flex min-h-8 cursor-pointer items-center gap-1.5 rounded-[2px] border-0 bg-transparent px-3 text-[13px] font-[560] text-muted aria-pressed:bg-surface aria-pressed:text-ink aria-pressed:shadow-sm"
              >
                {icon}
                {label as string}
              </button>
            ))}
          </div>
        )}
      </div>
      {legend && !showTable && (
        <ul className="m-0 mt-4 flex list-none flex-wrap gap-x-4 gap-y-1.5 p-0" aria-label="Legend">
          {legend.map((l) => (
            <li key={l.label} className="inline-flex items-center gap-1.5 text-[13px] leading-5 text-text">
              <span aria-hidden="true" className={`size-2.5 rounded-[2px] ${l.swatch}`} />
              {l.label}
            </li>
          ))}
        </ul>
      )}
      {/* focusable so a keyboard can scroll a wide table or chart on a phone */}
      <div className="relative mt-5 min-w-0 flex-1 overflow-x-auto" tabIndex={0} role="region" aria-label={title}>
        {showTable ? table : chart}
      </div>
      {note && <p className="text-caption m-0 mt-4 max-w-[72ch]">{note}</p>}
      <figcaption className="text-caption mt-5 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-rule pt-4">
        <span>Source{split ? `: ${split} split,` : ':'}</span>
        {runIds.map((id) => (
          <RunId key={id} id={id} />
        ))}
      </figcaption>
    </figure>
  )
}
