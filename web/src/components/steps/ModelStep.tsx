import { selectText } from '../../copy/reasons'
import type { RecordedRun } from '../../data/replay'

export function ModelStep({ run }: { run: RecordedRun }) {
  const a = run.response.answer
  return (
    <dl className="m-0">
      <dt className="text-caption">Model</dt>
      <dd className="m-0 mb-5 text-[15px] leading-6">
        {a.size === 'large' ? 'Large' : 'Small'} <span className="font-mono text-[14px] text-muted">{a.model}</span>
      </dd>
      <dt className="text-caption">Why this model</dt>
      <dd className="m-0 mb-5 max-w-[60ch] text-[15px] leading-6">{selectText(a.select_reason)}</dd>
      <dt className="text-caption">Answer confidence</dt>
      <dd className="m-0 text-[15px] leading-6">
        {a.confidence.toFixed(2)}
        {a.flagged && <span className="text-muted"> (below the threshold, flagged for review)</span>}
      </dd>
    </dl>
  )
}
