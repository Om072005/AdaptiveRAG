import { LABEL, METHOD } from '../../copy/reasons'
import type { RecordedRun } from '../../data/replay'
import { ScoreBar } from '../ScoreBar'
import { Facts } from './Facts'

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
    <Facts
      items={[
        ['Question type', LABEL[route.label] ?? route.label],
        ['Classifier confidence', route.label_confidence === null ? 'None' : <ScoreBar key="c" value={route.label_confidence} label="Confidence" />],
        ['Method', route.method ? (METHOD[route.method] ?? route.method).replace(/^./, (c) => c.toUpperCase()) : 'None'],
      ]}
    />
  )
}
