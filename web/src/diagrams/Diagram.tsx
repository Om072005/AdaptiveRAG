import { type ReactNode, useState } from 'react'
import { Button } from '../components/Button'
import { center, diamond, labelPoint, pathD, route } from './geometry'
import type { Box, DiagramData, DiagramEdge, DiagramNode, Layout, Lit } from './types'

type Tone = 'rest' | 'on' | 'off'

const DASH: Record<string, string | undefined> = { dashed: '6 4', dashdot: '10 3 2 3', dotted: '1 4' }
const STROKE: Record<Tone, string> = { rest: 'stroke-cream-300', on: 'stroke-white', off: 'stroke-cream-600' }
const LABEL: Record<Tone, string> = { rest: 'fill-cream-300', on: 'fill-white', off: 'fill-muted' }
const LINE_H = 18

function tone(lit: Lit | null, set: 'nodes' | 'edges', id: string): Tone {
  if (!lit) return 'rest'
  return lit[set].has(id) ? 'on' : 'off'
}

function Shape({ node, box, t, picked }: { node: DiagramNode; box: Box; t: Tone; picked: boolean }) {
  const stroke = picked ? 'stroke-cream-100' : STROKE[t]
  const fill = picked ? 'fill-cream-100' : 'fill-black'
  const width = t === 'on' && !picked ? 1.5 : 1
  const [cx, cy] = center(box)
  const top = cy - ((node.lines.length - 1) * LINE_H) / 2 + 5
  return (
    <>
      {node.kind === 'decision' ? (
        <polygon points={diamond(box)} className={`${fill} ${stroke}`} strokeWidth={width} />
      ) : (
        <rect x={box.x} y={box.y} width={box.w} height={box.h} rx="2" className={`${fill} ${stroke}`} strokeWidth={width} />
      )}
      {node.kind === 'store' && (
        <line x1={box.x} y1={box.y + 4} x2={box.x + box.w} y2={box.y + 4} className={stroke} strokeWidth={width} />
      )}
      <text textAnchor="middle" className={`font-sans text-[14px] ${picked ? 'fill-black' : LABEL[t]}`}>
        {node.lines.map((line, i) => (
          <tspan key={i} x={cx} y={top + i * LINE_H}>
            {line}
          </tspan>
        ))}
      </text>
    </>
  )
}

function Edge({ edge, layout, kinds, t, marker }: {
  edge: DiagramEdge
  layout: Layout
  kinds: Record<string, DiagramNode['kind']>
  t: Tone
  marker: string
}) {
  const a = layout.nodes[edge.from]
  const b = layout.nodes[edge.to]
  const points = route(a, kinds[edge.from], b, kinds[edge.to], layout.bends?.[edge.id])
  const placed = layout.labels?.[edge.id]
  const [lx, ly] = placed ?? labelPoint(points)
  const lines = edge.label?.split('\n') ?? []  // a label may take two lines where the gap is narrow
  const w = Math.max(0, ...lines.map((l) => l.length)) * 7 + 12
  const h = 20 * lines.length
  return (
    <g>
      <path
        d={pathD(points)}
        fill="none"
        className={STROKE[t]}
        strokeWidth={t === 'on' ? 1.5 : 1}
        strokeDasharray={DASH[edge.style ?? 'solid']}
        markerEnd={`url(#${marker}-${t})`}
      />
      {edge.label && placed !== null && (
        <>
          <rect x={lx - w / 2} y={ly - h / 2} width={w} height={h} className="fill-black" />
          <text x={lx} y={ly + 4 - 10 * (lines.length - 1)} textAnchor="middle" className={`font-sans text-[13px] ${t === 'on' ? 'fill-white' : 'fill-muted'}`}>
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

function Drawing({ data, layout, which, lit, picked, onPick }: {
  data: DiagramData
  layout: Layout
  which: 'wide' | 'tall'
  lit: Lit | null
  picked: string | null
  onPick: (id: string) => void
}) {
  const marker = `${data.id}-${which}`
  const kinds = Object.fromEntries(data.nodes.map((n) => [n.id, n.kind]))
  return (
    <svg
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      role="group"
      aria-labelledby={`${marker}-title ${marker}-desc`}
      className="block h-auto w-full"
      shapeRendering="geometricPrecision"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <title id={`${marker}-title`}>{data.title}</title>
      <desc id={`${marker}-desc`}>{data.desc}</desc>
      <defs>
        {(['rest', 'on', 'off'] as const).map((t) => (
          <marker key={t} id={`${marker}-${t}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M1 1 L7 4 L1 7" fill="none" className={STROKE[t]} strokeWidth="1" />
          </marker>
        ))}
      </defs>
      {layout.groups?.map((g) => (
        <g key={g.label}>
          <rect x={g.box.x} y={g.box.y} width={g.box.w} height={g.box.h} fill="none" className="stroke-cream-600" strokeWidth="1" />
          <text x={g.box.x + 8} y={g.box.y + 16} className="fill-muted font-sans text-[13px]">
            {g.label}
          </text>
        </g>
      ))}
      {data.edges.map((e) => (
        <Edge key={e.id} edge={e} layout={layout} kinds={kinds} t={tone(lit, 'edges', e.id)} marker={marker} />
      ))}
      {data.nodes.map((n) => (
        <g
          key={n.id}
          role="button"
          tabIndex={0}
          aria-label={n.lines.join(' ')}
          aria-pressed={picked === n.id}
          className="cursor-pointer outline-none"
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
    <ol className="m-0 max-w-[68ch] pl-5 text-[15px] leading-6">
      {data.nodes.map((n) => {
        const next = data.edges.filter((e) => e.from === n.id)
        return (
          <li key={n.id} className="mb-3">
            <span className="text-white">{name[n.id]}</span>
            {lit?.nodes.has(n.id) && <span className="text-muted"> (on the path taken)</span>}
            {n.detail && <span>{/[.?!]$/.test(name[n.id]) ? ' ' : '. '}{n.detail}</span>}
            {n.module && <span className="text-code"> {n.module}</span>}
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

function Detail({ node }: { node: DiagramNode | undefined }) {
  return (
    <div className="mt-6 rounded-[6px] bg-raised p-5 @4xl:mt-0" aria-live="polite">
      {node ? (
        <>
          <p className="m-0 text-[15px] leading-6 text-white">{node.lines.join(' ')}</p>
          {node.detail && <p className="text-small m-0 mt-2">{node.detail}</p>}
          {node.module && <p className="text-code m-0 mt-3 break-all">{node.module}</p>}
          {node.status && <p className="text-caption m-0 mt-2">{node.status}</p>}
        </>
      ) : (
        <p className="text-caption m-0">Select a box to read what it does and where it lives in the code.</p>
      )}
    </div>
  )
}

/** A hand placed diagram: the wide layout when its own container is 896px or more (the page at
 * 1024px), the tall one below and never scaled up; nodes open their detail; Show as text. */
export function Diagram({ data, lit = null, detailSide = false, caption }: {
  data: DiagramData
  lit?: Lit | null // the taken path in white, everything else faded
  detailSide?: boolean // detail panel beside the diagram from 1024px, else below it
  caption?: ReactNode
}) {
  const [asText, setAsText] = useState(false)
  const [picked, setPicked] = useState<string | null>(null)
  const node = data.nodes.find((n) => n.id === picked)
  return (
    <figure className="@container m-0">
      <div className={detailSide ? '@4xl:grid @4xl:grid-cols-[minmax(0,1fr)_300px] @4xl:items-start @4xl:gap-8' : ''}>
        <div>
          {asText ? (
            <AsText data={data} lit={lit} />
          ) : (
            <>
              <div className="hidden @4xl:block">
                <Drawing data={data} layout={data.wide} which="wide" lit={lit} picked={picked} onPick={setPicked} />
              </div>
              <div className="@4xl:hidden" style={{ maxWidth: data.tall.width }}>
                <Drawing data={data} layout={data.tall} which="tall" lit={lit} picked={picked} onPick={setPicked} />
              </div>
            </>
          )}
        </div>
        {!asText && (detailSide || node) && <Detail node={node} />}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
        <Button onClick={() => setAsText((v) => !v)} aria-pressed={asText}>
          {asText ? 'Show as diagram' : 'Show as text'}
        </Button>
        {caption && <figcaption className="text-caption m-0">{caption}</figcaption>}
      </div>
    </figure>
  )
}
