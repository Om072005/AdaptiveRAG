import { duration, money, score } from '../../copy/format'
import type { RecordedRun } from '../../data/replay'

/** A plain reading of one stage of a recorded response, used until the stage has its full view. */
export function StageSummary({ stage, run }: { stage: number; run: RecordedRun }) {
  const r = run.response
  const byStage: [string, string][][] = [
    [
      ['Label', r.route.label ?? 'Not classified (forced route)'],
      ['Confidence', r.route.label_confidence === null ? 'None' : score(r.route.label_confidence)],
      ['Method', r.route.method ?? 'None'],
    ],
    [
      ['Route taken', r.route.final],
      ['Fallbacks', r.route.fallbacks.join(', ') || 'None'],
      ['Reasons', r.route.reasons.join('; ')],
    ],
    [
      ['Hits', r.retrieval.hits.map((h) => `${h.rank}. ${h.title}`).join('; ') || 'None'],
      ['Top score', score(r.retrieval.top_score)],
      ['Graph path found', r.retrieval.path_found ? 'Yes' : 'No'],
    ],
    [
      ['Model', `${r.answer.model} (${r.answer.size})`],
      ['Why', r.answer.select_reason],
    ],
    [['Answer', r.answer.short]],
    [
      ['Total cost', money(r.trace.cost.total)],
      ['Total time', duration(r.trace.total_ms)],
    ],
  ]
  return (
    <dl className="m-0">
      {byStage[stage].map(([k, v]) => (
        <div key={k} className="mb-5">
          <dt className="text-caption">{k}</dt>
          <dd className="m-0 text-[15px] leading-6">{v}</dd>
        </div>
      ))}
    </dl>
  )
}
