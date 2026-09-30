import { type ReactNode, useState } from 'react'
import { Button } from '../components/Button'
import { center, diamond, labelPoint, pathD, route } from './geometry'
import type { Box, DiagramData, DiagramEdge, DiagramNode, EdgeStyle, Layout, Lit } from './types'

type Tone = 'rest' | 'on' | 'off'

const DASH: Record<EdgeStyle, string | undefined> = { solid: undefined, dashed: '6 4', dashdot: '10 3 2 3', dotted: '1 5' }
// route encoding: graph edges orange, hybrid edges green, the rest in the line gray; lit solid edges take the accent
const EDGE_REST: Record<EdgeStyle, string> = { solid: 'stroke-line', dashed: 'stroke-graph', dashdot: 'stroke-hybrid', dotted: 'stroke-line' }
const EDGE_ON: Record<EdgeStyle, string> = { solid: 'stroke-accent', dashed: 'stroke-graph', dashdot: 'stroke-hybrid', dotted: 'stroke-accent' }
const HEAD: Record<string, string> = {
  'stroke-line': 'fill-line',
  'stroke-graph': 'fill-graph',
  'stroke-hybrid': 'fill-hybrid',
  'stroke-accent': 'fill-accent',
  'stroke-faint': 'fill-faint',
}
const NODE_FILL: Record<DiagramNode['kind'], string> = { step: 'fill-surface', decision: 'fill-accent-soft', store: 'fill-sunken' }
const LINE_H = 18

function tone(lit: Lit | null, set: 'nodes' | 'edges', id: string): Tone {
  if (!lit) return 'rest'
  return lit[set].has(id) ? 'on' : 'off'
}

function edgeStroke(style: EdgeStyle, t: Tone): string {
  if (t === 'off') return 'stroke-faint'
  return t === 'on' ? EDGE_ON[style] : EDGE_REST[style]
}

function Shape({ node, box, t, picked }: { node: DiagramNode; box: Box; t: Tone; picked: boolean }) {
  const stroke = picked ? 'stroke-accent' : t === 'on' ? 'stroke-accent' : t === 'off' ? 'stroke-faint' : 'stroke-line'
  const fill = picked ? 'fill-accent' : t === 'off' ? 'fill-surface' : NODE_FILL[node.kind]
  const width = t === 'on' || picked ? 2 : 1
  const label = picked ? 'fill-accent-ink' : t === 'off' ? 'fill-muted' : 'fill-ink'
  const [cx, cy] = center(box)
  const top = cy - ((node.lines.length - 1) * LINE_H) / 2 + 5
  return (
    <>
      {node.kind === 'decision' ? (
        <polygon points={diamond(box)} className={`${fill} ${stroke} transition-colors duration-200`} strokeWidth={width} />
      ) : (
        <rect x={box.x} y={box.y} width={box.w} height={box.h} rx={node.kind === 'store' ? 6 : 10} className={`${fill} ${stroke} transition-colors duration-200`} strokeWidth={width} />
      )}
      {node.kind === 'store' && (
        <line x1={box.x + 6} y1={box.y + 7} x2={box.x + box.w - 6} y2={box.y + 7} className={stroke} strokeWidth="1" />
      )}
      <text textAnchor="middle" className={`font-sans text-[13.5px] ${t === 'on' || picked ? 'font-[600]' : 'font-[500]'} ${label}`}>
        {node.lines.map((line, i) => (
          <tspan key={i} x={cx} y={top + i * LINE_H}>
            {line}
          </tspan>
        ))}
      </text>
    </>
  )
}

function Edge({ edge, layout, kinds, t, marker, flow }: {
  edge: DiagramEdge
  layout: Layout
  kinds: Record<string, DiagramNode['kind']>
  t: Tone
  marker: string
  flow: boolean
}) {
  const a = layout.nodes[edge.from]
  const b = layout.nodes[edge.to]
  const points = route(a, kinds[edge.from], b, kinds[edge.to], layout.bends?.[edge.id])
  const placed = layout.labels?.[edge.id]
  const [lx, ly] = placed ?? labelPoint(points)
  const lines = edge.label?.split('\n') ?? [] // a label may take two lines where the gap is narrow
  const w = Math.max(0, ...lines.map((l) => l.length)) * 7 + 14
  const h = 20 * lines.length
  const style = edge.style ?? 'solid'
  const stroke = edgeStroke(style, t)
  const d = pathD(points)
  return (
    <g>
      <path
        d={d}
        fill="none"
        className={`${stroke} transition-colors duration-200`}
        strokeWidth={t === 'on' ? 2 : 1.25}
        strokeDasharray={DASH[style]}
        markerEnd={`url(#${marker}-${stroke})`}
      />
      {t === 'on' && flow && style !== 'dotted' && <path d={d} fill="none" strokeWidth="2.5" className="flow-dash stroke-surface" />}
      {edge.label && placed !== null && (
        <>
          <rect x={lx - w / 2} y={ly - h / 2} width={w} height={h} rx="6" className="fill-surface stroke-rule" strokeWidth="1" />
          <text x={lx} y={ly + 4 - 10 * (lines.length - 1)} textAnchor="middle" className={`font-sans text-[12.5px] ${t === 'on' ? 'fill-ink font-[600]' : 'fill-muted'}`}>
            {lines.map((l, i) => (
              <tspan key={l} x={lx} dy={i === 0 ? 0 : 20}>
                {l}
              </tspan>
            ))}
          </text>
        </>
      )}
    </g>
  )
}

function Drawing({ data, layout, which, lit, picked, onPick, flow }: {
  data: DiagramData
  layout: Layout
  which: 'wide' | 'tall'
  lit: Lit | null
  picked: string | null
  onPick: (id: string) => void
  flow: boolean
}) {
  const marker = `${data.id}-${which}`
  const kinds = Object.fromEntries(data.nodes.map((n) => [n.id, n.kind]))
  return (
    <svg
      viewBox={`-4 -4 ${layout.width + 8} ${layout.height + 8}`}
      role="group"
      aria-labelledby={`${marker}-title ${marker}-desc`}
      className="block h-auto w-full overflow-visible"
      shapeRendering="geometricPrecision"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <title id={`${marker}-title`}>{data.title}</title>
      <desc id={`${marker}-desc`}>{data.desc}</desc>
      <defs>
        {Object.entries(HEAD).map(([stroke, fill]) => (
          <marker key={stroke} id={`${marker}-${stroke}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M1 1 L7 4 L1 7 z" className={fill} />
          </marker>
        ))}
      </defs>
      {layout.groups?.map((g) => (
        <g key={g.label}>
          <rect x={g.box.x} y={g.box.y} width={g.box.w} height={g.box.h} rx="14" className="fill-sunken stroke-rule" strokeWidth="1" />
          <text x={g.box.x + 12} y={g.box.y + 18} className="fill-muted font-sans text-[12px] font-[600]">
            {g.label}
          </text>
        </g>
      ))}
      {data.edges.map((e) => (
        <Edge key={e.id} edge={e} layout={layout} kinds={kinds} t={tone(lit, 'edges', e.id)} marker={marker} flow={flow} />
      ))}
      {data.nodes.map((n) => (
        <g
          key={n.id}
          role="button"
          tabIndex={0}
          aria-label={n.lines.join(' ')}
          aria-pressed={picked === n.id}
          className="cursor-pointer outline-none [&:focus-visible>rect]:stroke-accent [&:hover>polygon]:stroke-accent [&:hover>rect:first-child]:stroke-accent"
          onClick={() => onPick(n.id)}
          onFocus={() => onPick(n.id)}
          onKeyDown={(ev) => {
            if (ev.key === 'Enter' || ev.key === ' ') {
              ev.preventDefault()
              onPick(n.id)
            }
          }}
        >
          <Shape node={n} box={layout.nodes[n.id]} t={tone(lit, 'nodes', n.id)} picked={picked === n.id} />
        </g>
      ))}
    </svg>
  )
}

/** The same nodes and edges as an ordered list: the diagram's text alternative. */
function AsText({ data, lit }: { data: DiagramData; lit: Lit | null }) {
  const name = Object.fromEntries(data.nodes.map((n) => [n.id, n.lines.join(' ')]))
  return (
    <ol className="m-0 max-w-[72ch] pl-5 text-[15px] leading-6">
      {data.nodes.map((n) => {
        const next = data.edges.filter((e) => e.from === n.id)
        return (
          <li key={n.id} className="mb-3">
            <span className="font-[600] text-ink">{name[n.id]}</span>
            {lit?.nodes.has(n.id) && <span className="text-muted"> (on the path taken)</span>}
            {n.detail && <span>{/[.?!]$/.test(name[n.id]) ? ' ' : '. '}{n.detail}</span>}
            {n.module && <span className="text-code text-muted"> {n.module}</span>}
            {n.status && <span className="text-muted"> {n.status}.</span>}
            {next.length > 0 && (
              <span className="text-muted">
                {' '}
                Next:{' '}
                {next
                  .map((e) => `${e.label ? `${e.label.replace('\n', ' ')}, ` : ''}${name[e.to]}${lit?.edges.has(e.id) ? ' (taken)' : ''}`)
                  .join('; ')}
                .
              </span>
            )}
          </li>
        )
      })}
    </ol>
  )
}

const STATUS_TONE: Record<string, string> = {
  'Built and measured': 'bg-good-soft text-good',
  Built: 'bg-accent-soft text-accent-text',
  'Not built': 'bg-warn-soft text-warn',
}

function Detail({ node, side }: { node: DiagramNode | undefined; side: boolean }) {
  return (
    <div className={`mt-5 rounded-[12px] border border-rule bg-raised p-5 ${side ? '@4xl:mt-0' : ''}`} aria-live="polite">
      {node ? (
        <div key={node.id} className="fade-in">
          <p className="m-0 text-[15.5px] leading-6 font-[620] text-ink">{node.lines.join(' ')}</p>
          {node.detail && <p className="text-small m-0 mt-2">{node.detail}</p>}
          {node.module && <p className="text-code m-0 mt-3 break-all text-muted">{node.module}</p>}
          {node.status && (
            <p className="m-0 mt-3">
              <span className={`inline-block rounded-full px-2.5 py-0.5 text-[12.5px] leading-5 font-[600] ${STATUS_TONE[node.status] ?? 'bg-sunken text-muted'}`}>
                {node.status}
              </span>
            </p>
          )}
        </div>
      ) : (
        <p className="text-caption m-0">Select a box to read what it does and where it lives in the code.</p>
      )}
    </div>
  )
}

function Legend({ data }: { data: DiagramData }) {
  const kinds = new Set(data.nodes.map((n) => n.kind))
  const styles = new Set(data.edges.map((e) => e.style ?? 'solid'))
  const item = 'inline-flex items-center gap-2'
  return (
    <ul className="text-caption m-0 flex list-none flex-wrap gap-x-5 gap-y-2 p-0" aria-label="Legend">
      <li className={item}>
        <span className="inline-block h-3.5 w-5 rounded-[4px] border border-line bg-surface" /> Step
      </li>
      {kinds.has('decision') && (
        <li className={item}>
          <span className="inline-block size-3 rotate-45 border border-line bg-accent-soft" /> Decision
        </li>
      )}
      {kinds.has('store') && (
        <li className={item}>
          <span className="inline-block h-3.5 w-5 rounded-[2px] border border-line bg-sunken" /> Stored data
        </li>
      )}
      {styles.has('dashed') && (
        <li className={item}>
          <svg width="22" height="4" aria-hidden="true"><line x1="1" y1="2" x2="21" y2="2" className="stroke-graph" strokeWidth="2" strokeDasharray="6 4" /></svg> Graph route
        </li>
      )}
      {styles.has('dashdot') && (
        <li className={item}>
          <svg width="22" height="4" aria-hidden="true"><line x1="1" y1="2" x2="21" y2="2" className="stroke-hybrid" strokeWidth="2" strokeDasharray="10 3 2 3" /></svg> Hybrid route
        </li>
      )}
      {styles.has('dotted') && (
        <li className={item}>
          <svg width="22" height="4" aria-hidden="true"><line x1="1" y1="2" x2="21" y2="2" className="stroke-line" strokeWidth="2" strokeDasharray="1 5" strokeLinecap="round" /></svg> Source link or feedback
        </li>
      )}
    </ul>
  )
}

/** A hand placed diagram: the wide layout when its own container is 896px or more, the tall one below
 * and never scaled up; nodes open their detail; the lit path flows; Show as text. */
export function Diagram({ data, lit = null, detailSide = false, caption, framed = true, flow = true, legend = true }: {
  data: DiagramData
  lit?: Lit | null // the taken path in the accent, everything else faded
  detailSide?: boolean // detail panel beside the diagram from 1024px, else below it
  caption?: ReactNode
  framed?: boolean // on its own card; off when the parent is already a card
  flow?: boolean // moving dashes along the lit path
  legend?: boolean
}) {
  const [asText, setAsText] = useState(false)
  const [picked, setPicked] = useState<string | null>(null)
  const node = data.nodes.find((n) => n.id === picked)
  return (
    <figure className={`@container m-0 ${framed ? 'card p-4 sm:p-6' : ''}`}>
      <div className={detailSide ? '@4xl:grid @4xl:grid-cols-[minmax(0,1fr)_280px] @4xl:items-start @4xl:gap-8' : ''}>
        <div className="min-w-0">
          {asText ? (
            <AsText data={data} lit={lit} />
          ) : (
            <>
              <div className="hidden @4xl:block">
                <Drawing data={data} layout={data.wide} which="wide" lit={lit} picked={picked} onPick={setPicked} flow={flow} />
              </div>
              <div className="mx-auto @4xl:hidden" style={{ maxWidth: data.tall.width }}>
                <Drawing data={data} layout={data.tall} which="tall" lit={lit} picked={picked} onPick={setPicked} flow={flow} />
              </div>
            </>
          )}
        </div>
        {!asText && (detailSide || node) && <Detail node={node} side={detailSide} />}
      </div>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-t border-rule pt-4">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {legend && !asText && <Legend data={data} />}
          {caption && <figcaption className="text-caption m-0">{caption}</figcaption>}
        </div>
        <Button kind="ghost" className="min-h-9 px-3 text-[13.5px]" onClick={() => setAsText((v) => !v)} aria-pressed={asText}>
          {asText ? 'Show as diagram' : 'Show as text'}
        </Button>
      </div>
    </figure>
  )
}
