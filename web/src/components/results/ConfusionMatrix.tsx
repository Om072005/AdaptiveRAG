import { LABEL } from '../../copy/reasons'
import type { Results } from '../../types'

/** True type by predicted type as a heatmap of counts: one hue, darker for more; the diagonal is correct. */
export function ConfusionMatrix({ confusion }: { confusion: Results['tables']['confusion'] }) {
  const names = confusion.labels.map((l) => LABEL[l] ?? l)
  const max = Math.max(1, ...confusion.matrix.flat())
  return (
    <table className="border-separate border-spacing-1.5 text-[14px] leading-6">
      <caption className="text-caption pb-2 text-left">Rows are the true type, columns what the classifier predicted.</caption>
      <thead>
        <tr>
          <th scope="col" className="p-2" />
          {names.map((n) => (
            <th key={n} scope="col" className="px-2 pb-1 text-center text-[12.5px] font-[600] whitespace-nowrap text-muted">
              {n}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {confusion.matrix.map((row, i) => (
          <tr key={names[i]}>
            <th scope="row" className="pr-3 text-left text-[12.5px] font-[600] whitespace-nowrap text-muted">
              {names[i]}
            </th>
            {row.map((count, j) => {
              const share = Math.round((count / max) * 88) + 6
              return (
                <td
                  key={j}
                  className={`relative h-14 w-20 rounded-[2px] text-center text-[16px] font-[650] tabular-nums md:w-24 ${share > 50 ? 'text-accent-ink' : 'text-ink'} ${i === j ? 'outline-2 outline-offset-1 outline-accent' : ''}`}
                  style={{ background: `color-mix(in srgb, var(--accent) ${share}%, var(--surface))` }}
                >
                  {count}
                  {i === j && <span className="sr-only"> (correct)</span>}
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
