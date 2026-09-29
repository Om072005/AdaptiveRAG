import { LABEL, METHOD } from '../../copy/reasons'
import type { RecordedRun } from '../../data/replay'
import { ScoreBar } from '../ScoreBar'

export function ClassifyStep({ run }: { run: RecordedRun }) {
  const route = run.response.route
  if (route.label === null) {
    return (
      <p className="text-small m-0 text-muted">
        Not classified: this run asked for the {route.requested} route directly, so the classifier did not run.
      </p>
    )
  }
  return (
    <dl className="m-0">
      <dt className="text-caption">Question type</dt>
      <dd className="m-0 mb-5 text-[15px] leading-6">{LABEL[route.label] ?? route.label}</dd>
      <dt className="text-caption">Classifier confidence</dt>
      <dd className="m-0 mb-5 text-[15px] leading-6">
        {route.label_confidence === null ? 'None' : <ScoreBar value={route.label_confidence} label="Confidence" />}
      </dd>
      <dt className="text-caption">Method</dt>
      <dd className="m-0 text-[15px] leading-6">{route.method ? (METHOD[route.method] ?? route.method) : 'None'}</dd>
    </dl>
  )
}
