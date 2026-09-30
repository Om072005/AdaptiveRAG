import { type RecordedRun, STAGES } from '../../data/replay'
import type { Replay } from '../../types'
import { AnswerStep } from './AnswerStep'
import { ClassifyStep } from './ClassifyStep'
import { CostStep } from './CostStep'
import { ModelStep } from './ModelStep'
import { RetrieveStep } from './RetrieveStep'
import { RouteStep } from './RouteStep'

// what each stage does, in one plain sentence above its detail
const INTRO: Record<(typeof STAGES)[number], string> = {
  Classify: 'First, a small classifier decides what kind of question this is.',
  Route: 'The router uses that label to choose where to look for the answer.',
  Retrieve: 'The chosen route brings back the evidence, strongest first.',
  Model: 'A selector picks the small or the large model to write the answer.',
  Answer: 'The answer, with every claim pointing at a numbered source, then how it scored.',
  Cost: 'Where the time went, and what the question cost at list prices.',
}

/** One stage of the recorded run, in the order of the stage rail. */
export function StageView({ stage, run, replay }: { stage: number; run: RecordedRun; replay: Replay }) {
  return (
    <div>
      <p className="m-0 mb-5 flex items-center gap-2 text-[14.5px] leading-6 text-text">
        <span className="rounded-full bg-accent-soft px-2 py-px text-[12px] font-[650] text-accent-text">{STAGES[stage]}</span>
        {INTRO[STAGES[stage]]}
      </p>
      <Stage stage={stage} run={run} replay={replay} />
    </div>
  )
}

function Stage({ stage, run, replay }: { stage: number; run: RecordedRun; replay: Replay }) {
  switch (STAGES[stage]) {
    case 'Classify':
      return <ClassifyStep run={run} />
    case 'Route':
      return <RouteStep run={run} />
    case 'Retrieve':
      return <RetrieveStep run={run} />
    case 'Model':
      return <ModelStep run={run} />
    case 'Answer':
      return <AnswerStep run={run} replay={replay} />
    case 'Cost':
      return <CostStep run={run} />
  }
}
