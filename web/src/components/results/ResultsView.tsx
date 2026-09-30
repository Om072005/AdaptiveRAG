import { useState } from 'react'
import { duration, money, percent } from '../../copy/format'
import { LABEL, METHOD } from '../../copy/reasons'
import { BG, FILL, MODE_NAME, MODE_ORDER, STROKE } from '../../copy/routes'
import type { Mode, Results } from '../../types'
import { BarList } from '../charts/BarList'
import { XYChart, type XYSeries } from '../charts/XYChart'
import { RouteChip } from '../RouteChip'
import { ChartCard, type LegendItem } from './ChartCard'
import { ConfusionMatrix } from './ConfusionMatrix'
import { DataTable } from './DataTable'

type T = Results['tables']
const metric = (v: number | null) => (v === null ? 'Not judged' : v.toFixed(3))
const two = (v: number) => v.toFixed(2)
const per1k = (usd: number) => `$${(usd * 1000).toFixed(usd * 1000 < 0.1 ? 3 : 2)}`
const ids = (rows: { run_id: string }[]) => [...new Set(rows.map((r) => r.run_id))]
const byMode = <R extends { mode: Mode }>(rows: R[]) => MODE_ORDER.flatMap((m) => rows.filter((r) => r.mode === m))
const ROUTE_LEGEND: LegendItem[] = MODE_ORDER.map((m) => ({ label: MODE_NAME[m], swatch: BG[m] }))

const METRICS = [
  { key: 'f1', label: 'Accuracy (F1)', what: 'How much of the correct answer our answer contains, from 0 to 1.' },
  { key: 'em', label: 'Exact match', what: 'Share of answers that match the correct one word for word.' },
  { key: 'recall_at_k', label: 'Right passage found', what: 'Share of questions where a passage holding the answer was retrieved.' },
  { key: 'faithfulness', label: 'Faithfulness', what: 'The judge model\'s score for sticking to the retrieved sources.' },
] as const
type MetricKey = (typeof METRICS)[number]['key']

function Segmented<K extends string>({ options, value, onPick, label }: { options: readonly { key: K; label: string }[]; value: K; onPick: (k: K) => void; label: string }) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          aria-pressed={o.key === value}
          onClick={() => onPick(o.key)}
          className="min-h-9 cursor-pointer rounded-full border border-rule bg-surface px-3.5 text-[13.5px] font-[560] text-muted transition-colors hover:text-ink aria-pressed:border-transparent aria-pressed:bg-ink aria-pressed:text-canvas"
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

function RoutesCard({ t, split }: { t: T; split?: string }) {
  const [key, setKey] = useState<MetricKey>('f1')
  const m = METRICS.find((x) => x.key === key) ?? METRICS[0]
  const rows = byMode(t.routes)
  return (
    <ChartCard
      wide
      title="Letting the router choose beats any single method"
      takeaway={<>The same held out questions, answered four ways. {m.what}</>}
      legend={ROUTE_LEGEND}
      split={split}
      runIds={ids(t.routes)}
      chart={
        <div>
          <Segmented options={METRICS} value={key} onPick={setKey} label="Metric" />
          <div className="mt-5">
            <BarList
              max={1}
              format={(v) => (key === 'f1' ? two(v) : percent(v))}
              bars={rows
                .filter((r) => r[key] !== null)
                .map((r) => ({
                  id: r.mode,
                  label: MODE_NAME[r.mode],
                  value: r[key] as number,
                  color: BG[r.mode],
                  strong: r.mode === 'auto',
                  tip: [
                    ['Cost per question', money(r.cost_per_query_usd)],
                    ['Median time', duration(r.p50_ms)],
                  ],
                }))}
            />
          </div>
        </div>
      }
      table={
        <DataTable
          rows={rows}
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
      }
    />
  )
}

function CostCard({ t, split }: { t: T; split?: string }) {
  const rows = byMode(t.routes)
  const bars = (value: (r: T['routes'][number]) => number) =>
    rows.map((r) => ({ id: r.mode, label: MODE_NAME[r.mode], value: value(r), color: BG[r.mode], strong: r.mode === 'auto' }))
  return (
    <ChartCard
      title="What that accuracy costs"
      takeaway="The router spends more: hard questions go to the large model and to hybrid search, which is slower. Costs are list prices of the open models."
      split={split}
      runIds={ids(t.routes)}
      chart={
        <div className="grid grid-cols-1 gap-7">
          <div>
            <p className="text-caption m-0 mb-3 font-[600]">Cost per 1,000 questions</p>
            <BarList max={Math.max(...rows.map((r) => r.cost_per_query_usd)) * 1000} format={(v) => `$${v.toFixed(2)}`} bars={bars((r) => r.cost_per_query_usd * 1000)} />
          </div>
          <div>
            <p className="text-caption m-0 mb-3 font-[600]">Median time per question</p>
            <BarList max={Math.max(...rows.map((r) => r.p50_ms)) / 1000} format={(v) => `${v.toFixed(1)} s`} bars={bars((r) => r.p50_ms / 1000)} />
          </div>
        </div>
      }
      table={
        <DataTable
          rows={rows}
          columns={[
            { label: 'Mode', value: (r) => MODE_NAME[r.mode] },
            { label: 'Per question', value: (r) => money(r.cost_per_query_usd), numeric: true },
            { label: 'Per 1,000', value: (r) => per1k(r.cost_per_query_usd), numeric: true },
            { label: 'p50', value: (r) => duration(r.p50_ms), numeric: true },
            { label: 'p95', value: (r) => duration(r.p95_ms), numeric: true },
          ]}
        />
      }
    />
  )
}

function ByTypeCard({ t, split }: { t: T; split?: string }) {
  const types = [...new Set(t.by_type.map((r) => r.type))]
  return (
    <ChartCard
      title="The biggest gain is on multi step questions"
      takeaway="Accuracy (F1) for each kind of question. Questions that chain two facts are where a single method struggles most."
      legend={ROUTE_LEGEND}
      split={split}
      runIds={ids(t.by_type)}
      chart={
        <div className="grid grid-cols-1 gap-6">
          {types.map((type) => (
            <div key={type}>
              <p className="m-0 mb-2.5 text-[13.5px] font-[620] text-ink">{LABEL[type] ?? type}</p>
              <BarList
                thin
                max={1}
                format={two}
                bars={byMode(t.by_type.filter((r) => r.type === type)).map((r) => ({
                  id: r.mode,
                  label: MODE_NAME[r.mode],
                  value: r.f1,
                  color: BG[r.mode],
                  strong: r.mode === 'auto',
                  tip: [['Right passage found', percent(r.recall_at_k)]],
                }))}
              />
            </div>
          ))}
        </div>
      }
      table={
        <DataTable
          rows={t.by_type}
          columns={[
            { label: 'Mode', value: (r) => MODE_NAME[r.mode] ?? r.mode },
            { label: 'Type', value: (r) => LABEL[r.type] ?? r.type },
            { label: 'F1', value: (r) => metric(r.f1), numeric: true },
            { label: 'Recall at k', value: (r) => metric(r.recall_at_k), numeric: true },
          ]}
        />
      }
    />
  )
}

const VARIANT: Record<string, string> = {
  baseline: 'Router as served',
  selector: 'Router as served',
  'always-small': 'Router, small model only',
  'always-large': 'Router, large model only',
}

/** Quality per cost points, one per distinct result: runs that measured the same numbers share a point. */
function qualityPoints(results: Results) {
  const rows = results.tables.quality_per_cost
  const groups = new Map<string, { mode: Mode; names: string[]; row: (typeof rows)[number] }>()
  for (const r of rows) {
    const mode = results.runs[r.run_id]?.mode ?? 'auto'
    const name = mode === 'auto' ? (VARIANT[r.variant] ?? r.variant) : MODE_NAME[mode]
    const key = `${r.f1.toFixed(3)} ${r.cost_per_query_usd.toPrecision(2)} ${mode === 'auto'}`
    const g = groups.get(key)
    if (g) g.names = [...new Set([...g.names, name])]
    else groups.set(key, { mode, names: [name], row: r })
  }
  return [...groups.values()]
}

function QualityCostCard({ results, split }: { results: Results; split?: string }) {
  const t = results.tables
  const points = qualityPoints(results)
  const series: XYSeries[] = MODE_ORDER.map((m) => ({
    id: m,
    name: MODE_NAME[m],
    fill: FILL[m],
    stroke: STROKE[m],
    points: points
      .filter((p) => p.mode === m)
      .map((p) => ({
        x: p.row.cost_per_query_usd * 1000,
        y: p.row.f1,
        label: p.names.join(', '),
        hollow: !p.row.eligible,
        tip: [['Faithfulness', metric(p.row.faithfulness)]] as [string, string][],
      })),
  }))
  const xs = points.map((p) => p.row.cost_per_query_usd * 1000)
  const ys = points.map((p) => p.row.f1)
  return (
    <ChartCard
      wide
      title="Quality against cost"
      takeaway="Up is more accurate, right is more expensive (a log scale: each step is ten times the cost). The served router sits between the cheap single methods and always using the large model."
      legend={ROUTE_LEGEND}
      split={split}
      runIds={ids(t.quality_per_cost)}
      note="Filled points meet the faithfulness floor; a hollow point would fall below it and is not a win at any cost. Runs with identical results share one point."
      chart={
        points.length > 0 && (
        <XYChart
          wide
          title="Accuracy against cost per 1,000 questions for each variant"
          series={series}
          xLog
          xDomain={[10 ** Math.floor(Math.log10(Math.min(...xs))), 10 ** Math.ceil(Math.log10(Math.max(...xs)))]}
          yDomain={[Math.floor(Math.min(...ys) * 10) / 10, Math.min(1, Math.ceil(Math.max(...ys) * 10) / 10)]}
          xLabel="Cost per 1,000 questions (list price)"
          yLabel="Accuracy (F1)"
          formatX={(v) => `$${v < 1 ? v.toString() : v.toFixed(0)}`}
          formatY={two}
        />
        )
      }
      table={
        <DataTable
          rows={t.quality_per_cost}
          columns={[
            { label: 'Run', value: (r) => <span className="font-mono text-[12.5px]">{r.run_id}</span> },
            { label: 'Variant', value: (r) => r.variant },
            { label: 'F1', value: (r) => metric(r.f1), numeric: true },
            { label: 'Faithfulness', value: (r) => metric(r.faithfulness), numeric: true },
            { label: 'Cost per query', value: (r) => money(r.cost_per_query_usd), numeric: true },
            { label: 'Eligible', value: (r) => (r.eligible ? 'Yes' : 'No') },
          ]}
        />
      }
    />
  )
}

const SELECTOR_NAME: Record<string, string> = { 'always-small': 'Small model only', 'always-large': 'Large model only', selector: 'Selector (served)' }

function SelectorCard({ t, split }: { t: T; split?: string }) {
  const sel = t.selector.find((r) => r.variant === 'selector')
  const small = t.selector.find((r) => r.variant === 'always-small')
  const large = t.selector.find((r) => r.variant === 'always-large')
  const gain = sel && small && large && large.f1 > small.f1 ? (sel.f1 - small.f1) / (large.f1 - small.f1) : null
  const bars = (value: (r: T['selector'][number]) => number) =>
    t.selector.map((r) => ({
      id: r.variant,
      label: SELECTOR_NAME[r.variant] ?? r.variant,
      value: value(r),
      color: r.variant === 'selector' ? 'bg-accent' : 'bg-line',
      strong: r.variant === 'selector',
      tip: [['Answered by the large model', percent(r.large_share)]] as [string, string][],
    }))
  return (
    <ChartCard
      title="Small or large model, per question"
      takeaway={
        sel && large && gain !== null
          ? `The selector sent ${percent(sel.large_share)} of questions to the large model, keeping ${percent(gain)} of its accuracy gain at ${percent(sel.cost_per_query_usd / large.cost_per_query_usd)} of its cost.`
          : undefined
      }
      split={split}
      runIds={ids(t.selector)}
      chart={
        <div className="grid grid-cols-1 gap-7">
          <div>
            <p className="text-caption m-0 mb-3 font-[600]">Accuracy (F1)</p>
            <BarList max={1} format={two} bars={bars((r) => r.f1)} labelWidth="minmax(120px,max-content)" />
          </div>
          <div>
            <p className="text-caption m-0 mb-3 font-[600]">Cost per 1,000 questions</p>
            <BarList
              max={Math.max(...t.selector.map((r) => r.cost_per_query_usd)) * 1000}
              format={(v) => `$${v.toFixed(2)}`}
              bars={bars((r) => r.cost_per_query_usd * 1000)}
              labelWidth="minmax(120px,max-content)"
            />
          </div>
        </div>
      }
      table={
        <DataTable
          rows={t.selector}
          columns={[
            { label: 'Variant', value: (r) => r.variant },
            { label: 'F1', value: (r) => metric(r.f1), numeric: true },
            { label: 'Cost per query', value: (r) => money(r.cost_per_query_usd), numeric: true },
            { label: 'Answered by the large model', value: (r) => percent(r.large_share), numeric: true },
          ]}
        />
      }
    />
  )
}

function ClassifierCard({ t }: { t: T }) {
  const best = t.classifier.reduce((a, b) => (b.macro_f1 > a.macro_f1 ? b : a), t.classifier[0])
  return (
    <ChartCard
      title="Reading the question"
      takeaway="Three ways to label a question as single hop, multi hop or comparison. A small trained model won, and runs in no measurable time."
      runIds={ids(t.classifier)}
      chart={
        <BarList
          max={1}
          format={two}
          labelWidth="minmax(130px,max-content)"
          bars={t.classifier.map((r) => ({
            id: r.method,
            label: (METHOD[r.method] ?? r.method).replace(/^./, (c) => c.toUpperCase()),
            value: r.macro_f1,
            color: r === best ? 'bg-accent' : 'bg-line',
            strong: r === best,
            tip: [
              ['Cost per question', money(r.cost_per_query_usd)],
              ['Median time', duration(r.p50_ms)],
            ],
          }))}
        />
      }
      table={
        <DataTable
          rows={t.classifier}
          columns={[
            { label: 'Method', value: (r) => r.method },
            { label: 'Macro F1', value: (r) => metric(r.macro_f1), numeric: true },
            { label: 'Cost per query', value: (r) => money(r.cost_per_query_usd), numeric: true },
            { label: 'p50', value: (r) => duration(r.p50_ms), numeric: true },
          ]}
        />
      }
      note="Score is macro F1 across the three question types, on the dev split."
    />
  )
}

function ConfusionCard({ t, split }: { t: T; split?: string }) {
  const total = t.confusion.matrix.flat().reduce((a, b) => a + b, 0)
  const right = t.confusion.matrix.reduce((s, row, i) => s + row[i], 0)
  return (
    <ChartCard
      title="Where the classifier gets it wrong"
      takeaway={`${right} of ${total} test questions labelled correctly. A multi hop question read as a comparison is the most common slip, and both go to hybrid anyway.`}
      split={split}
      runIds={[t.confusion.run_id]}
      table={<ConfusionMatrix confusion={t.confusion} />}
    />
  )
}

function IndexCard({ t }: { t: T }) {
  const ours = t.hnsw.filter((r) => r.index === 'hnsw' && r.ef !== null)
  const pg = t.hnsw.filter((r) => r.index === 'pgvector hnsw' && r.ef !== null)
  const pt = (r: T['hnsw'][number]) => ({
    x: r.ef as number,
    y: r.recall_at_10,
    label: `ef ${r.ef}`,
    tip: [['Median time', `${r.p50_ms.toFixed(r.p50_ms < 10 ? 2 : 0)} ms`]] as [string, string][],
  })
  const series: XYSeries[] = [
    { id: 'ours', name: 'Our HNSW (in memory)', fill: 'fill-accent', stroke: 'stroke-accent', line: true, points: ours.map(pt) },
    { id: 'pg', name: 'pgvector HNSW (served, over the network)', fill: 'fill-line', stroke: 'stroke-line', line: true, dash: '6 4', points: pg.map(pt) },
  ]
  const efs = [...ours, ...pg].map((r) => r.ef as number)
  const recalls = [...ours, ...pg].map((r) => r.recall_at_10)
  return (
    <ChartCard
      wide
      title="Our own vector index, against the library"
      takeaway="How many of the true 10 nearest passages the index finds (recall), as its search effort ef grows. Ours reaches 0.99 at ef 32, level with pgvector, the library index that serves real queries."
      legend={[
        { label: series[0].name, swatch: 'bg-accent' },
        { label: series[1].name, swatch: 'bg-line' },
      ]}
      runIds={ids(t.hnsw)}
      note="Exact search finds every neighbour by definition. Hover a point for its median search time; pgvector times include the database round trip."
      chart={
        efs.length > 0 && (
        <XYChart
          wide
          title="Recall at 10 against ef for our HNSW and pgvector"
          series={series}
          xLog
          xDomain={[Math.min(...efs), Math.max(...efs)]}
          yDomain={[Math.floor(Math.min(...recalls) * 50) / 50, 1]}
          xLabel="Search effort (ef, log scale)"
          yLabel="Recall at 10"
          formatX={(v) => String(Math.round(v))}
          formatY={two}
          reference={{ y: 1, label: 'Exact search' }}
        />
        )
      }
      table={
        <DataTable
          rows={t.hnsw}
          columns={[
            { label: 'Index', value: (r) => r.index },
            { label: 'ef', value: (r) => (r.ef === null ? 'None' : String(r.ef)), numeric: true },
            { label: 'Recall at 10', value: (r) => metric(r.recall_at_10), numeric: true },
            { label: 'p50 (ms)', value: (r) => r.p50_ms.toFixed(2), numeric: true },
            { label: 'p95 (ms)', value: (r) => r.p95_ms.toFixed(2), numeric: true },
          ]}
        />
      }
    />
  )
}

function ChunkingCard({ t }: { t: T }) {
  return (
    <ChartCard
      title="Cutting documents into chunks"
      takeaway="Three ways to split text for search, measured on the small corpus. Sentence chunks serve real queries; the other two were too close to call."
      runIds={ids(t.chunking)}
      table={
        <DataTable
          rows={t.chunking}
          columns={[
            { label: 'Strategy', value: (r) => `${r.strategy} (${r.params})`, wrap: true },
            { label: 'Precision', value: (r) => metric(r.precision), numeric: true },
            { label: 'Context kept', value: (r) => metric(r.context_retention), numeric: true },
            { label: 'Retrieval', value: (r) => metric(r.retrieval_score), numeric: true },
            { label: 'Verdict', value: (r) => r.verdict, wrap: true },
          ]}
        />
      }
    />
  )
}

function GraphCard({ t }: { t: T }) {
  const tiles: [string, string, string][] = [
    ['Entities', t.graph.entities.toLocaleString('en-US'), 'people, places and works'],
    ['Relations', t.graph.relations.toLocaleString('en-US'), 'facts linking them'],
    ['Facts rejected', percent(t.graph.reject_rate), 'failed the check against their source'],
    ['Merge precision', percent(t.graph.er_precision), 'of name merges were right'],
  ]
  return (
    <ChartCard
      wide
      title="The knowledge graph"
      takeaway="Built from the documents behind the gold questions, every fact checked against the text it came from."
      runIds={[t.graph.run_id]}
      table={
        <dl className="m-0 grid grid-cols-2 gap-3 md:grid-cols-4">
          {tiles.map(([k, v, sub]) => (
            <div key={k} className="rounded-[12px] border border-rule bg-sunken p-4">
              <dt className="text-caption font-[600]">{k}</dt>
              <dd className="m-0 mt-1">
                <span className="block text-[28px] leading-9 font-[680] tracking-[-0.02em] text-ink">{v}</span>
                <span className="text-caption block">{sub}</span>
              </dd>
            </div>
          ))}
        </dl>
      }
    />
  )
}

export function ResultsView({ results }: { results: Results }) {
  const t = results.tables
  const splitOf = (rows: { run_id: string }[]) => {
    const splits = [...new Set(rows.map((r) => results.runs[r.run_id]?.split).filter(Boolean))]
    return splits.join(' and ') || undefined
  }

  return (
    <div>
      <dl className="m-0 mb-8 grid grid-cols-1 gap-3 md:grid-cols-4">
        {METRICS.map((m) => (
          <div key={m.key} className="rounded-[12px] border border-dashed border-faint p-4">
            <dt className="text-[13.5px] font-[620] text-ink">{m.label}</dt>
            <dd className="text-caption m-0 mt-1">{m.what}</dd>
          </div>
        ))}
      </dl>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <RoutesCard t={t} split={splitOf(t.routes)} />
        <ByTypeCard t={t} split={splitOf(t.by_type)} />
        <CostCard t={t} split={splitOf(t.routes)} />
        <QualityCostCard results={results} split={splitOf(t.quality_per_cost)} />
        <SelectorCard t={t} split={splitOf(t.selector)} />
        <ClassifierCard t={t} />
        <ConfusionCard t={t} split={splitOf([t.confusion])} />
        <ChunkingCard t={t} />
        <IndexCard t={t} />
        <GraphCard t={t} />
      </div>
    </div>
  )
}
