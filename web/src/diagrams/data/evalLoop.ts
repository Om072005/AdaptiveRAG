// The README "Evaluation feedback loop" states, each mapped to where it lives in the system.
import type { DiagramData } from '../types.ts'
import { box, edge } from './shapes.ts'

export const EVAL_LOOP: DiagramData = {
  id: 'evalloop',
  title: 'Evaluation feedback loop',
  desc: 'Every answer is judged by a model from a different family. It passes when every score clears the threshold, otherwise it is flagged for manual review, where a person names the cause: a misroute, bad chunks or bad triples, each leading to its own tuning.',
  nodes: [
    { id: 'answered', lines: ['Answered'], kind: 'step', detail: 'A trace row: route, both confidences, tokens, cost and latency.', module: 'adaptiverag/telemetry/trace.py' },
    { id: 'judged', lines: ['Judged'], kind: 'step', detail: 'Faithfulness, relevance and completeness from a judge model of a different family than the generator.', module: 'adaptiverag/eval/judge.py' },
    { id: 'passed', lines: ['Passed'], kind: 'step', detail: 'Every score at or above judge.flag_below.' },
    { id: 'flagged', lines: ['Flagged'], kind: 'step', detail: 'Any score below judge.flag_below opens a row in the review queue.', module: 'adaptiverag/eval/review.py' },
    { id: 'review', lines: ['Manual review'], kind: 'step', detail: 'A person reads the answer and its sources and labels the cause.', module: 'python -m adaptiverag.eval.review' },
    { id: 'router', lines: ['Router tuning'], kind: 'step', detail: 'Labelled misroutes retrain the classifier and move the router thresholds, measured on dev.', module: 'adaptiverag/router/train.py' },
    { id: 'retrieval', lines: ['Retrieval tuning'], kind: 'step', detail: 'Bad chunks point at the chunking strategy and the vector thresholds.', module: 'adaptiverag/eval/tune.py' },
    { id: 'extraction', lines: ['Extraction tuning'], kind: 'step', detail: 'Bad triples point at the extraction prompt, validation and entity resolution.', module: 'adaptiverag/ingest/extract.py' },
  ],
  edges: [
    edge('answered', 'judged', 'async judge'),
    edge('judged', 'passed', 'all above threshold'),
    edge('judged', 'flagged', 'any below threshold'),
    edge('flagged', 'review'),
    edge('review', 'router', 'misroute'),
    edge('review', 'retrieval', 'bad chunks'),
    edge('review', 'extraction', 'bad triples'),
  ],
  wide: {
    width: 1024,
    height: 392,
    nodes: {
      answered: box(72, 208, 128, 48),
      judged: box(296, 208, 128, 48),
      passed: box(488, 96, 128, 48),
      flagged: box(488, 296, 128, 48),
      review: box(656, 296, 160, 48),
      router: box(952, 200, 144, 48),
      retrieval: box(952, 296, 144, 48),
      extraction: box(952, 360, 144, 48),
    },
    bends: {
      'review-router': [
        [776, 296],
        [776, 200],
      ],
      'review-extraction': [
        [776, 296],
        [776, 360],
      ],
    },
    labels: {
      'judged-passed': [392, 152],
      'judged-flagged': [392, 252],
      'review-router': [828, 200],
      'review-retrieval': [828, 296],
      'review-extraction': [828, 360],
    },
  },
  tall: {
    width: 352,
    height: 704,
    nodes: {
      answered: box(176, 32, 144, 48),
      judged: box(176, 136, 144, 48),
      passed: box(88, 248, 128, 48),
      flagged: box(264, 248, 128, 48),
      review: box(176, 360, 160, 48),
      router: box(176, 472, 192, 48),
      retrieval: box(176, 568, 192, 48),
      extraction: box(176, 664, 192, 48),
    },
    bends: {
      'review-retrieval': [
        [32, 360],
        [32, 568],
      ],
      'review-extraction': [
        [320, 360],
        [320, 664],
      ],
    },
    labels: {
      'answered-judged': [176, 84],
      'judged-passed': [88, 200],
      'judged-flagged': [264, 200],
      'review-router': [176, 424],
      'review-retrieval': [80, 520],
      'review-extraction': [272, 616],
    },
  },
}
