import { LABEL } from '../../copy/reasons'
import type { Results } from '../../types'

/** Gold type by predicted type as a grid of counts; the diagonal (correct) is framed in white. */
export function ConfusionMatrix({ confusion }: { confusion: Results['tables']['confusion'] }) {
  const names = confusion.labels.map((l) => LABEL[l] ?? l)
  return (
    <table className="border-collapse text-[15px] leading-6">
      <caption className="text-caption pb-3 text-left">Rows are the true type, columns what the classifier predicted.</caption>
      <thead>
        <tr>
          <th scope="col" className="p-3 font-normal text-muted" />
          {names.map((n) => (
            <th key={n} scope="col" className="p-3 text-right font-normal whitespace-nowrap text-muted">
              {n}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {confusion.matrix.map((row, i) => (
          <tr key={names[i]}>
            <th scope="row" className="p-3 text-left font-normal whitespace-nowrap text-muted">
              {names[i]}
            </th>
            {row.map((count, j) => (
              <td
                key={j}
                className={`w-24 border border-rule p-3 text-right tabular-nums ${i === j ? 'text-white outline outline-1 -outline-offset-2 outline-white' : ''}`}
              >
                {count}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
