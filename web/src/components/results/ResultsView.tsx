import { duration, money, percent } from '../../copy/format'
import { LABEL } from '../../copy/reasons'
import type { Results } from '../../types'
import { RouteChip } from '../RouteChip'
import { ConfusionMatrix } from './ConfusionMatrix'
import { DataTable } from './DataTable'
import { Figure } from './Figure'
import { Scatter } from './Scatter'

const metric = (v: number | null) => (v === null ? 'Not judged' : v.toFixed(3))
const MODE_NAME: Record<string, string> = { auto: 'Router', vector: 'Vector only', graph: 'Graph only', hybrid: 'Hybrid only' }
const ids = (rows: { run_id: string }[]) => [...new Set(rows.map((r) => r.run_id))]

export function ResultsView({ results }: { results: Results }) {
  const t = results.tables
  const splitOf = (rows: { run_id: string }[]) => {
    const splits = [...new Set(rows.map((r) => results.runs[r.run_id]?.split).filter(Boolean))]
    return splits.join(' and ') || undefined
  }

  return (
    <div>
      <Figure title="Every route on the same questions" split={splitOf(t.routes)} runIds={ids(t.routes)}>
        <DataTable
          rows={t.routes}
          columns={[
            { label: 'Mode', value: (r) => (r.mode === 'auto' ? MODE_NAME.auto : <RouteChip route={r.mode} />) },
            { label: 'EM', value: (r) => metric(r.em), numeric: true },
            { label: 'F1', value: (r) => metric(r.f1), numeric: true },
            { label: 'Recall at k', value: (r) => metric(r.recall_at_k), numeric: true },
            { label: 'Faithfulness', value: (r) => metric(r.faithfulness), numeric: true },
            { label: 'Cost per query', value: (r) => money(r.cost_per_query_usd), numeric: true },
            { label: 'p50', value: (r) => duration(r.p50_ms), numeric: true },
            { label: 'p95', value: (r) => duration(r.p95_ms), numeric: true },
          ]}
        />
      </Figure>

      <Figure title="Quality by question type" split={splitOf(t.by_type)} runIds={ids(t.by_type)}>
        <DataTable
          rows={t.by_type}
          columns={[
            { label: 'Mode', value: (r) => MODE_NAME[r.mode] ?? r.mode },
            { label: 'Type', value: (r) => LABEL[r.type] ?? r.type },
            { label: 'F1', value: (r) => metric(r.f1), numeric: true },
            { label: 'Recall at k', value: (r) => metric(r.recall_at_k), numeric: true },
          ]}
        />
      </Figure>

      <Figure
        title="Quality per unit cost"
        split={splitOf(t.quality_per_cost)}
        runIds={ids(t.quality_per_cost)}
        note="Filled points meet the faithfulness floor. Hollow points fall below it and are not a win at any cost."
      >
        <Scatter
          title="F1 against cost per query for each variant"
          points={t.quality_per_cost.map((r) => ({ x: r.cost_per_query_usd, y: r.f1, label: r.variant, filled: r.eligible }))}
          xLabel="Cost per query (USD, list price)"
          yLabel="F1"
          formatX={money}
          formatY={(v) => v.toFixed(2)}
        />
      </Figure>

      <Figure title="Small or large model" split={splitOf(t.selector)} runIds={ids(t.selector)}>
        <DataTable
          rows={t.selector}
          columns={[
            { label: 'Variant', value: (r) => r.variant },
            { label: 'F1', value: (r) => metric(r.f1), numeric: true },
            { label: 'Cost per query', value: (r) => money(r.cost_per_query_usd), numeric: true },
            { label: 'Answered by the large model', value: (r) => percent(r.large_share), numeric: true },
          ]}
        />
      </Figure>

      <Figure title="Question classifiers" runIds={ids(t.classifier)}>
        <DataTable
          rows={t.classifier}
          columns={[
            { label: 'Method', value: (r) => r.method },
            { label: 'Macro F1', value: (r) => metric(r.macro_f1), numeric: true },
            { label: 'Cost per query', value: (r) => money(r.cost_per_query_usd), numeric: true },
            { label: 'p50', value: (r) => duration(r.p50_ms), numeric: true },
          ]}
        />
      </Figure>

      <Figure title="Where the router's classifier goes wrong" split={splitOf([t.confusion])} runIds={[t.confusion.run_id]}>
        <ConfusionMatrix confusion={t.confusion} />
      </Figure>

      <Figure
        title="Our HNSW against exact search"
        runIds={ids(t.hnsw)}
        note="Serving uses pgvector's HNSW index; this compares our own HNSW (filled points) with exact search (the hollow point)."
      >
        <Scatter
          title="Recall at 10 against median latency per index setting"
          points={t.hnsw.map((r) => ({
            x: r.p50_ms,
            y: r.recall_at_10,
            label: r.ef === null ? r.index : `${r.index} ef ${r.ef}`,
            filled: r.index !== 'flat',
          }))}
          xLabel="Median query time (ms)"
          yLabel="Recall at 10"
          formatX={(v) => v.toFixed(1)}
          formatY={(v) => v.toFixed(2)}
        />
      </Figure>

      <Figure title="Chunking strategies" runIds={ids(t.chunking)}>
        <DataTable
          rows={t.chunking}
          columns={[
            { label: 'Strategy', value: (r) => `${r.strategy} (${r.params})` },
            { label: 'Precision', value: (r) => metric(r.precision), numeric: true },
            { label: 'Context retention', value: (r) => metric(r.context_retention), numeric: true },
            { label: 'Retrieval score', value: (r) => metric(r.retrieval_score), numeric: true },
            { label: 'Verdict', value: (r) => r.verdict, wrap: true },
          ]}
        />
      </Figure>

      <Figure title="Graph quality" runIds={[t.graph.run_id]}>
        <dl className="m-0 grid grid-cols-2 gap-x-8 gap-y-4 md:grid-cols-4">
          {[
            ['Entities', String(t.graph.entities)],
            ['Relations', String(t.graph.relations)],
            ['Triples rejected by validation', percent(t.graph.reject_rate)],
            ['Entity resolution precision', percent(t.graph.er_precision)],
          ].map(([k, v]) => (
            <div key={k}>
              <dt className="text-caption">{k}</dt>
              <dd className="m-0 text-[21px] leading-7 tabular-nums">{v}</dd>
            </div>
          ))}
        </dl>
      </Figure>
    </div>
  )
}
