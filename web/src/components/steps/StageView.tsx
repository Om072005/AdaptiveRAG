import { type RecordedRun, STAGES } from '../../data/replay'
import type { Replay } from '../../types'
import { AnswerStep } from './AnswerStep'
import { ClassifyStep } from './ClassifyStep'
import { CostStep } from './CostStep'
import { ModelStep } from './ModelStep'
import { RetrieveStep } from './RetrieveStep'
import { RouteStep } from './RouteStep'

/** One stage of the recorded run, in the order of the stage rail. */
export function StageView({ stage, run, replay }: { stage: number; run: RecordedRun; replay: Replay }) {
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
