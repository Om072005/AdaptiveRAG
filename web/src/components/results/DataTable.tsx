import type { ReactNode } from 'react'

export type Column<T> = { label: string; value: (row: T) => ReactNode; numeric?: boolean; wrap?: boolean }

/** Hairline rows, numbers right aligned; scrolls inside its card on a phone. */
export function DataTable<T>({ columns, rows }: { columns: Column<T>[]; rows: T[] }) {
  return (
    <table className="w-full border-collapse text-[14px] leading-6">
      <thead>
        <tr>
          {columns.map((c) => (
            <th
              key={c.label}
              scope="col"
              className={`border-b border-rule py-2.5 pr-4 text-[12.5px] font-[600] whitespace-nowrap text-muted ${c.numeric ? 'text-right' : 'text-left'}`}
            >
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="hover:bg-sunken">
            {columns.map((c) => (
              <td
                key={c.label}
                className={`border-b border-rule py-2.5 pr-4 align-top ${c.wrap ? 'min-w-48' : 'whitespace-nowrap'} ${c.numeric ? 'text-right tabular-nums' : 'text-left'}`}
              >
                {c.value(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
