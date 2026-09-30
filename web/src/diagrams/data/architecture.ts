// The README "System architecture". Status words are what exists today; the lead updates them at
// each gate (Built and measured, Built, Not built).
import type { DiagramData } from '../types.ts'
import { box, edge } from './shapes.ts'

export const ARCHITECTURE: DiagramData = {
  id: 'architecture',
  title: 'System architecture',
  desc: 'A query is classified and budgeted, then answered from vector search, graph traversal or a hybrid of both over one Postgres store. A model selector picks a small or large model to write the cited answer, a judge from another model family scores it, and low scores wait in a queue whose findings tune the classifier.',
  nodes: [
    { id: 'u', lines: ['User query'], kind: 'step', detail: 'A question from the page or the command line.', module: 'adaptiverag/server.py', status: 'Built' },
    { id: 'qc', lines: ['Query classifier'], kind: 'step', detail: 'Labels the question single hop, multi hop or comparison, with a confidence of its own. Logistic regression on the query embedding and cue features, picked over rules and a model classifier on the dev split.', module: 'adaptiverag/router/classify.py', status: 'Built and measured' },
    { id: 'cb', lines: ['Cost and complexity', 'budgeter'], kind: 'step', detail: 'The decision table picks the route; near the budget it keeps to vector, and one query makes at most four model calls.', module: 'adaptiverag/router/policy.py', status: 'Built' },
    { id: 'vs', lines: ['Vector', 'search'], kind: 'step', detail: 'Nearest chunks by cosine similarity through a pgvector HNSW index, the library default.', module: 'adaptiverag/stores/vector.py', status: 'Built and measured' },
    { id: 'hy', lines: ['Hybrid', 'merge and', 're-rank'], kind: 'step', detail: 'Vector and graph hits fused by reciprocal rank, then a diversity pass drops near duplicates.', module: 'adaptiverag/router/hybrid.py', status: 'Built' },
    { id: 'gr', lines: ['Graph', 'traversal'], kind: 'step', detail: 'Breadth first search from the entities named in the question, two hops at most, every edge citing its chunk.', module: 'adaptiverag/stores/graph.py', status: 'Built' },
    { id: 'vdb', lines: ['Vector DB:', 'chunks and', 'embeddings'], kind: 'store', detail: 'Documents, chunks and their embeddings in Postgres on Neon.', module: 'adaptiverag/stores/vector.py', status: 'Built' },
    { id: 'gdb', lines: ['Graph DB:', 'entities and', 'relations'], kind: 'store', detail: 'Entities, aliases and relations in the same Postgres; the graph for the gold questions is being built.', module: 'adaptiverag/stores/graph.py', status: 'Not built' },
    { id: 'log', lines: ['Trace store:', 'cost, latency,', 'evaluation'], kind: 'store', detail: 'One trace row per query with both confidences, tokens, list price cost and latency, plus every model call.', module: 'adaptiverag/telemetry/trace.py', status: 'Built' },
    { id: 'ms', lines: ['Model selector:', 'small or large'], kind: 'step', detail: 'Sends questions the classifier labels multi hop or comparison, and very long contexts, to the large model, and the rest to the small one. On the dev split that kept most of the large model\'s gain at 60% of its cost (decision D20).', module: 'adaptiverag/generate/select.py', status: 'Built' },
    { id: 'llm', lines: ['Answer synthesis', 'with citations'], kind: 'step', detail: 'A short answer and one or two sentences, every claim pointing at a numbered source.', module: 'adaptiverag/generate/answer.py', status: 'Built' },
    { id: 'ev', lines: ['Model as judge:', 'faithfulness,', 'relevance'], kind: 'step', detail: 'Scores faithfulness, relevance and completeness with a model from a different family than the generator.', module: 'adaptiverag/eval/judge.py', status: 'Built' },
    { id: 'lq', lines: ['Low confidence', 'queue'], kind: 'step', detail: 'Answers with a low judge score or low answer confidence, waiting for a person to label the cause.', module: 'adaptiverag/eval/review.py', status: 'Built' },
  ],
  edges: [
    edge('u', 'qc'),
    edge('qc', 'cb'),
    edge('cb', 'vs'),
    edge('cb', 'hy'),
    edge('cb', 'gr'),
    edge('vs', 'vdb'),
    edge('hy', 'vdb'),
    edge('hy', 'gdb'),
    edge('gr', 'gdb'),
    edge('vs', 'ms'),
    edge('hy', 'ms'),
    edge('gr', 'ms'),
    edge('ms', 'llm'),
    edge('llm', 'ev'),
    edge('ev', 'log'),
    edge('ev', 'lq'),
    edge('lq', 'qc', 'tune thresholds', 'dotted'),
    edge('llm', 'u'),
  ],
  wide: {
    width: 904,
    height: 704,
    nodes: {
      u: box(328, 40, 144, 48),
      qc: box(232, 136, 160, 48),
      cb: box(448, 136, 176, 64),
      vs: box(144, 272, 128, 64),
      hy: box(328, 272, 128, 80),
      gr: box(512, 272, 128, 64),
      vdb: box(168, 416, 176, 96),
      gdb: box(488, 416, 176, 96),
      log: box(784, 416, 176, 96),
      ms: box(328, 544, 176, 64),
      llm: box(328, 640, 176, 64),
      ev: box(568, 640, 176, 80),
      lq: box(784, 640, 160, 64),
    },
    bends: {
      'cb-vs': [
        [448, 200],
        [144, 200],
      ],
      'cb-hy': [
        [448, 200],
        [328, 200],
      ],
      'cb-gr': [
        [448, 200],
        [512, 200],
      ],
      'vs-vdb': [[144, 336]],
      'gr-gdb': [[512, 336]],
      'hy-vdb': [
        [328, 336],
        [224, 336],
      ],
      'hy-gdb': [
        [328, 336],
        [432, 336],
      ],
      'vs-ms': [
        [48, 272],
        [48, 544],
      ],
      'gr-ms': [
        [608, 272],
        [608, 544],
      ],
      'ev-log': [
        [568, 568],
        [784, 568],
      ],
      'u-qc': [
        [328, 80],
        [232, 80],
      ],
      'lq-qc': [
        [896, 640],
        [896, 8],
        [112, 8],
        [112, 136],
      ],
      'llm-u': [
        [16, 640],
        [16, 40],
      ],
    },
    labels: { 'lq-qc': [512, 8] },
    groups: [
      { label: 'Routing layer', box: { x: 136, y: 88, w: 416, h: 88 } },
      { label: 'Retrieval backends', box: { x: 64, y: 216, w: 528, h: 104 } },
      { label: 'Storage layer', box: { x: 64, y: 344, w: 824, h: 128 } },
      { label: 'Generation', box: { x: 224, y: 488, w: 208, h: 192 } },
      { label: 'Evaluation loop', box: { x: 464, y: 576, w: 416, h: 112 } },
    ],
  },
  tall: {
    width: 384,
    height: 992,
    nodes: {
      u: box(192, 32, 144, 48),
      qc: box(192, 120, 176, 48),
      cb: box(192, 216, 208, 64),
      vs: box(80, 344, 96, 64),
      hy: box(192, 344, 96, 80),
      gr: box(304, 344, 96, 64),
      vdb: box(112, 480, 144, 96),
      gdb: box(272, 480, 144, 96),
      ms: box(192, 600, 176, 64),
      llm: box(192, 696, 176, 64),
      ev: box(192, 800, 176, 80),
      log: box(112, 928, 144, 96),
      lq: box(272, 920, 144, 64),
    },
    bends: {
      'cb-vs': [
        [192, 280],
        [80, 280],
      ],
      'cb-gr': [
        [192, 280],
        [304, 280],
      ],
      'vs-vdb': [[80, 408]],
      'gr-gdb': [[304, 408]],
      'hy-vdb': [
        [192, 408],
        [152, 408],
      ],
      'hy-gdb': [
        [192, 408],
        [232, 408],
      ],
      'vs-ms': [
        [24, 344],
        [24, 600],
      ],
      'gr-ms': [
        [360, 344],
        [360, 600],
      ],
      'ev-log': [
        [192, 864],
        [112, 864],
      ],
      'ev-lq': [
        [192, 864],
        [272, 864],
      ],
      'lq-qc': [
        [376, 920],
        [376, 120],
      ],
      'llm-u': [
        [8, 696],
        [8, 32],
      ],
    },
    // no room on the narrow layout; Show as text still carries it
    labels: { 'lq-qc': null },
  },
}
