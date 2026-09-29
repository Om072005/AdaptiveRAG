import { useState } from 'react'
import { CHUNK_W, NODE_H, NODE_W, type Placed, layoutGraph } from '../data/graphLayout'
import type { QueryResponse } from '../types'

type Graph = QueryResponse['retrieval']['graph']
type Hit = QueryResponse['retrieval']['hits'][number]

function Drawing({ placed, selected, onSelect, hits }: {
  placed: Placed
  selected: number | null
  onSelect: (i: number | null) => void
  hits: Hit[]
}) {
  const title = hits.length ? 'Graph path with the chunk each fact came from' : 'Graph path'
  return (
    <svg viewBox={`0 0 ${placed.width} ${placed.height}`} role="group" aria-label={title} className="block h-auto w-full">
      <defs>
        <marker id="gp-ah" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M1 1 L7 4 L1 7" fill="none" className="stroke-cream-300" strokeWidth="1" />
        </marker>
      </defs>
      {placed.edges.map((e, i) => (
        <line
          key={`p${i}`}
          x1={(e.x1 + e.x2) / 2}
          y1={(e.y1 + e.y2) / 2}
          x2={e.chunkX}
          y2={e.chunkY}
          className={selected === i ? 'stroke-white' : 'stroke-cream-600'}
          strokeWidth="1"
          strokeDasharray="1 4"
        />
      ))}
      {placed.edges.map((e, i) => {
        const mx = (e.x1 + e.x2) / 2
        const my = (e.y1 + e.y2) / 2
        const on = selected === i
        return (
          <g
            key={`e${i}`}
            role="button"
            tabIndex={0}
            aria-pressed={on}
            aria-label={`${e.predicate}, from chunk ${e.chunk_id}`}
            className="cursor-pointer outline-none"
            onClick={() => onSelect(on ? null : i)}
            onKeyDown={(ev) => {
              if (ev.key === 'Enter' || ev.key === ' ') {
                ev.preventDefault()
                onSelect(on ? null : i)
              }
            }}
          >
            <line x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2} stroke="transparent" strokeWidth="16" />
            <line
              x1={e.x1}
              y1={e.y1}
              x2={e.x2}
              y2={e.y2}
              className={on ? 'stroke-white' : 'stroke-cream-300'}
              strokeWidth={on ? 1.5 : 1}
              strokeDasharray="6 4"
              markerEnd="url(#gp-ah)"
            />
            <rect x={mx - (e.predicate.length * 7 + 12) / 2} y={my - 11} width={e.predicate.length * 7 + 12} height="22" className="fill-black" />
            <text x={mx} y={my + 4} textAnchor="middle" className={`font-sans text-[13px] ${on ? 'fill-white' : 'fill-muted'}`}>
              {e.predicate}
            </text>
          </g>
        )
      })}
      {placed.nodes.map((n) => (
        <g key={n.id}>
          <rect
            x={n.x}
            y={n.y}
            width={NODE_W}
            height={NODE_H}
            rx="2"
            className={n.seed ? 'fill-cream-100 stroke-cream-100' : 'fill-black stroke-cream-300'}
            strokeWidth="1"
          />
          <text
            x={n.x + NODE_W / 2}
            y={n.y + 25}
            textAnchor="middle"
            className={`font-sans text-[14px] ${n.seed ? 'fill-black' : 'fill-cream-300'}`}
          >
            {n.name.length > 22 ? `${n.name.slice(0, 21)}...` : n.name}
          </text>
        </g>
      ))}
      {placed.chunks.map((c) => (
        <g key={c.id}>
          <rect x={c.x} y={c.y} width={CHUNK_W} height="32" rx="2" className="fill-black stroke-cream-600" strokeWidth="1" />
          <text x={c.x + CHUNK_W / 2} y={c.y + 21} textAnchor="middle" className="fill-muted font-sans text-[13px]">
            chunk {c.n}
          </text>
        </g>
      ))}
    </svg>
  )
}

/** The graph a route walked: seeds filled, hops to the right, dotted lines to each fact's chunk. */
export function GraphPath({ graph, hits }: { graph: Graph; hits: Hit[] }) {
  const [selected, setSelected] = useState<number | null>(null)
  const wide = layoutGraph(graph)
  const tall = layoutGraph(graph, 12, true)
  const edge = selected === null ? null : wide.edges[selected]
  const source = edge ? hits.find((h) => h.chunk_id === edge.chunk_id) : undefined

  return (
    <figure className="m-0">
      <div className="hidden md:block">
        <Drawing placed={wide} selected={selected} onSelect={setSelected} hits={hits} />
      </div>
      <div className="md:hidden">
        <Drawing placed={tall} selected={selected} onSelect={setSelected} hits={hits} />
      </div>
      <figcaption className="text-caption mt-3">
        Filled boxes are the entities found in the question. Select an edge to read the chunk it came from.
        {wide.hidden > 0 && ` And ${wide.hidden} more entities, not drawn.`}
      </figcaption>
      {edge && (
        <div className="mt-4 rounded-[6px] bg-raised p-5" aria-live="polite">
          <p className="text-caption m-0">
            {edge.predicate}, confidence {edge.confidence.toFixed(2)}
          </p>
          <p className="text-small m-0 mt-2">
            {source ? (
              <>
                <span className="text-white">{source.title}.</span> {source.snippet}
              </>
            ) : (
              `Chunk ${edge.chunk_id} is not among the retrieved hits.`
            )}
          </p>
        </div>
      )}
    </figure>
  )
}
