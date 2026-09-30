import { score } from '../../copy/format'
import type { RecordedRun } from '../../data/replay'
import { GraphPath } from '../GraphPath'
import { RouteChip } from '../RouteChip'

export function RetrieveStep({ run }: { run: RecordedRun }) {
  const r = run.response.retrieval
  const hasGraph = r.graph.nodes.length > 0
  return (
    <div>
      {hasGraph && (
        <div className="mb-10">
          <GraphPath graph={r.graph} hits={r.hits} />
        </div>
      )}
      <dl className="m-0 mb-6 flex flex-wrap gap-3">
        <div className="rounded-[2px] border border-rule bg-sunken px-4 py-2.5">
          <dt className="text-caption">Top score</dt>
          <dd className="m-0 text-[15px] leading-6">{score(r.top_score)}</dd>
        </div>
        <div className="rounded-[2px] border border-rule bg-sunken px-4 py-2.5">
          <dt className="text-caption">Connected graph path</dt>
          <dd className="m-0 text-[15px] leading-6">{r.path_found ? 'Found' : 'Not found'}</dd>
        </div>
      </dl>
      {r.hits.length === 0 && <p className="text-small m-0 text-muted">Nothing was retrieved.</p>}
      <ol className="m-0 list-none p-0">
        {r.hits.map((h) => (
          <li key={`${h.rank}-${h.chunk_id}`} className="border-t border-rule py-3.5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
              <span className="text-[15px] leading-6 font-[560] text-ink">
                <span className="mr-1.5 inline-flex size-5 items-center justify-center rounded-[2px] bg-sunken text-[12px] font-[650] text-muted">{h.rank}</span>
                {h.title}
              </span>
              <span className="text-caption flex items-center gap-4">
                <RouteChip route={h.source} />
                <span className="tabular-nums">score {score(h.score)}</span>
              </span>
            </div>
            <p className="text-caption m-0 mt-1">{h.snippet}</p>
          </li>
        ))}
      </ol>
    </div>
  )
}
