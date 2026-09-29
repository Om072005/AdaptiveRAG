import type { ReactNode } from 'react'
import { RouterFlow } from '../diagrams/RouterFlow'

// The four README workflows. A block shows its SVG diagram from web/src/diagrams (which has its own
// Show as text); blocks whose diagram has not landed yet show the same steps as a list.
const BLOCKS: { title: string; text: string; steps: string[]; diagram?: ReactNode }[] = [
  {
    title: 'Ingestion',
    text: 'Every document becomes two things: chunks with embeddings for similarity search, and validated triples for traversal. Each graph edge keeps the chunk it came from, so a graph answer can still cite text.',
    steps: [
      'Documents are parsed and normalized.',
      'Text is chunked three ways (fixed size, sentence boundary, topic shift) and embedded into the vector database.',
      'Chunks also go to triple extraction by a language model.',
      'Each triple is validated against its source text; hallucinated entities are rejected and logged.',
      'Entities are resolved and aliases merged into the graph database, every relation keeping its chunk.',
    ],
  },
  {
    title: 'Router decision logic',
    text: 'The router reads the question and picks the cheapest route that can answer it. A weak result falls back to hybrid once, never more.',
    diagram: <RouterFlow />,
    steps: [
      'Relational or comparative structure? No: route to vector search.',
      'Yes: are the entities in the graph? No: vector search; yes: graph traversal.',
      'Vector top score below the threshold, or no connected graph path: fall back to hybrid.',
      'Generate the answer; if its confidence is below the threshold, return it and flag it for review.',
    ],
  },
  {
    title: 'Graph schema',
    text: 'Entities, their aliases and the relations between them sit in the same database as the chunks. A relation cannot exist without the chunk it was read from.',
    steps: [
      'Entity: canonical id, name, type and embedding.',
      'Alias: a surface form pointing at an entity, with a confidence.',
      'Relation: subject, predicate, object, extraction confidence and the chunk it came from.',
      'Chunk: a span of a document, with its embedding.',
    ],
  },
  {
    title: 'Evaluation loop',
    text: 'Every judged answer either passes or waits for a person. What the person finds decides whether the router, retrieval or extraction gets tuned.',
    steps: [
      'Answered, then judged by a model from a different family.',
      'All scores above the threshold: passed. Any below: flagged into the review queue.',
      'Manual review labels it a misroute, bad chunks or bad triples.',
      'Each label feeds router, retrieval or extraction tuning.',
    ],
  },
]

export function Workflows() {
  return (
    <div>
      {BLOCKS.map((b) => (
        <div key={b.title} className="mb-16 md:mb-24">
          <h3 className="text-title m-0">{b.title}</h3>
          <p className="text-small m-0 mt-3 max-w-[60ch]">{b.text}</p>
          {b.diagram ? (
            <div className="mt-8">{b.diagram}</div>
          ) : (
            <ol className="m-0 mt-6 max-w-[68ch] pl-5 text-[15px] leading-6">
              {b.steps.map((s) => (
                <li key={s} className="mb-2">
                  {s}
                </li>
              ))}
            </ol>
          )}
        </div>
      ))}
    </div>
  )
}
