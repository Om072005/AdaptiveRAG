// The four README workflows as guided walkthroughs: each step names the path it lights in the diagram.
import { EVAL_LOOP } from '../../diagrams/data/evalLoop.ts'
import { INGESTION } from '../../diagrams/data/ingestion.ts'
import { ROUTER } from '../../diagrams/data/router.ts'
import { SCHEMA } from '../../diagrams/data/schema.ts'
import type { DiagramData, Lit } from '../../diagrams/types.ts'

export type FlowStep = {
  title: string
  text: string
  walk: string[][] // node sequences; each consecutive pair is an edge 'from-to'
  edges?: string[] // edges whose id is not 'from-to'
}

export type Flow = { key: string; title: string; summary: string; data: DiagramData; steps: FlowStep[] }

export const FLOWS: Flow[] = [
  {
    key: 'ingestion',
    title: 'Ingestion',
    summary:
      'Every document becomes two things: chunks with embeddings for similarity search, and checked facts for the graph. Each graph edge keeps the chunk it came from, so a graph answer can still cite text.',
    data: INGESTION,
    steps: [
      { title: 'Clean up', text: 'Documents are parsed and normalized, keeping where every sentence started.', walk: [['docs', 'parse']] },
      {
        title: 'Chunk and embed',
        text: 'Text is cut three ways (fixed size, sentence, topic shift) and each chunk is embedded for search.',
        walk: [['parse', 'strategy', 'fixed', 'embed', 'vdb'], ['strategy', 'sentence', 'embed'], ['strategy', 'semantic', 'embed']],
      },
      { title: 'Extract facts', text: 'A language model reads the chunks and writes facts as subject, relation, object.', walk: [['parse', 'extract']] },
      { title: 'Check facts', text: 'Both names must appear in the source text; anything made up is rejected and logged.', walk: [['extract', 'validate']] },
      {
        title: 'Build the graph',
        text: 'Names are merged with their aliases, and every relation keeps a link to its chunk.',
        walk: [['validate', 'resolve', 'gdb', 'vdb'], ['vdb', 'gdb']],
      },
    ],
  },
  {
    key: 'router',
    title: 'Router decision logic',
    summary:
      'The router reads the question and picks the cheapest route that can answer it. Weak evidence falls back to hybrid once, never more, and a shaky answer is still returned but flagged for a person.',
    data: ROUTER,
    steps: [
      { title: 'Simple lookup', text: 'No relational or comparative structure: straight to vector search.', walk: [['q', 'relational', 'vector', 'topk', 'answer']] },
      {
        title: 'Connected or unsure',
        text: 'Relational, comparative or unsure questions go to hybrid, graph and vector ranked together (decision D17).',
        walk: [['q', 'relational', 'fallback', 'hybrid', 'answer']],
      },
      { title: 'Weak evidence', text: 'A top score below the threshold falls back to hybrid, once.', walk: [['vector', 'topk', 'fallback', 'hybrid', 'answer']] },
      {
        title: 'Graph only',
        text: 'Traversal alone, used when the entities are in the graph, is one config line away.',
        walk: [['relational', 'entities', 'graph', 'path', 'answer']],
      },
      { title: 'Confidence check', text: 'A low confidence answer is returned and flagged for review.', walk: [['answer', 'confident', 'out'], ['confident', 'flag']] },
    ],
  },
  {
    key: 'schema',
    title: 'Graph schema',
    summary:
      'Entities, their aliases and the relations between them sit in the same Postgres database as the chunks. A relation cannot exist without the chunk it was read from.',
    data: SCHEMA,
    steps: [
      { title: 'Entities', text: 'One row per resolved person, place or work, with a type and an embedding.', walk: [['entities']] },
      { title: 'Aliases', text: 'Every name an entity is known by, each with a confidence.', walk: [['entities', 'aliases']] },
      { title: 'Relations', text: 'A fact between two entities, with the exact span of its evidence.', walk: [['entities', 'relations']], edges: ['subject', 'object'] },
      { title: 'Provenance', text: 'Every relation points at the chunk, and so the document, it was read from.', walk: [['relations', 'chunks', 'documents']] },
    ],
  },
  {
    key: 'eval',
    title: 'Evaluation loop',
    summary:
      'Every judged answer either passes or waits for a person. What the person finds decides whether the router, retrieval or extraction gets tuned next.',
    data: EVAL_LOOP,
    steps: [
      { title: 'Judge', text: 'Each answer is scored by a model from a different family than the one that wrote it.', walk: [['answered', 'judged']] },
      { title: 'Pass', text: 'Faithfulness, relevance and completeness all above the threshold.', walk: [['judged', 'passed']] },
      { title: 'Flag', text: 'Any score below it sends the answer to the review queue.', walk: [['judged', 'flagged', 'review']] },
      {
        title: 'Tune',
        text: 'The cause a person names (misroute, bad chunks, bad facts) decides what gets tuned.',
        walk: [['review', 'router'], ['review', 'retrieval'], ['review', 'extraction']],
      },
    ],
  },
]

/** The nodes and edges a step lights. */
export function stepLit(step: FlowStep): Lit {
  const nodes = new Set<string>()
  const edges = new Set<string>(step.edges ?? [])
  for (const seq of step.walk) {
    seq.forEach((id, i) => {
      nodes.add(id)
      if (i > 0) edges.add(`${seq[i - 1]}-${id}`)
    })
  }
  return { nodes, edges }
}
