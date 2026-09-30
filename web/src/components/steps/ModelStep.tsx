import { selectText } from '../../copy/reasons'
import type { RecordedRun } from '../../data/replay'
import { Facts } from './Facts'

export function ModelStep({ run }: { run: RecordedRun }) {
  const a = run.response.answer
  return (
    <div>
      <Facts
        cols={2}
        items={[
          [
            'Model',
            <>
              {a.size === 'large' ? 'Large' : 'Small'} <span className="font-mono text-[13px] font-normal text-muted">{a.model}</span>
            </>,
          ],
          [
            'Answer confidence',
            <>
              {a.confidence.toFixed(2)}
              {a.flagged && <span className="font-normal text-muted"> (below the threshold, flagged for review)</span>}
            </>,
          ],
        ]}
      />
      <div className="mt-3 rounded-[2px] border border-rule p-4">
        <p className="text-caption m-0">Why this model</p>
        <p className="m-0 mt-1 max-w-[64ch] text-[15px] leading-6 text-ink">{selectText(a.select_reason)}</p>
      </div>
    </div>
  )
}
