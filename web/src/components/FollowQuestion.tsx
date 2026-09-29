import { useState } from 'react'
import { loadReplay } from '../data/load'
import { useLoaded } from '../data/useLoaded'
import type { ReplayIndex } from '../types'
import { DataMissing } from './DataMissing'
import { STAGES, ordered } from '../data/replay'
import { ReplayList } from './ReplayList'
import { ReplayPanel } from './ReplayPanel'
import { AnswerStep } from './steps/AnswerStep'
import { ClassifyStep } from './steps/ClassifyStep'
import { RouteStep } from './steps/RouteStep'
import { StageSummary } from './steps/StageSummary'

export function FollowQuestion({ index }: { index: ReplayIndex }) {
  const [current, setCurrent] = useState(ordered(index.items)[0]?.question_id ?? '')
  const [listOpen, setListOpen] = useState(false)
  const replay = useLoaded(loadReplay, current)
  const pick = (id: string) => {
    setCurrent(id)
    setListOpen(false)
  }

  return (
    <div className="page-grid items-start">
      <div className="col-span-4 min-w-0 md:col-span-8 lg:col-span-3 xl:col-span-4">
        <button
          type="button"
          className="mb-4 min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] text-white underline underline-offset-4 md:hidden"
          aria-expanded={listOpen}
          onClick={() => setListOpen(!listOpen)}
        >
          Choose a question
        </button>
        <div className={listOpen ? 'block' : 'hidden md:block'}>
          <ReplayList items={index.items} current={current} onPick={pick} />
        </div>
      </div>
      <div className="col-span-4 min-w-0 md:col-span-8 lg:col-span-9 xl:col-span-8">
        {replay.status === 'loading' && <div className="h-px w-64 bg-rule" aria-label="Loading" />}
        {replay.status === 'missing' && <DataMissing />}
        {replay.status === 'error' && <DataMissing error={replay.message} />}
        {replay.status === 'ok' && (
          <ReplayPanel
            key={current}
            replay={replay.data}
            renderStage={(stage, run, r) => {
              if (STAGES[stage] === 'Classify') return <ClassifyStep run={run} />
              if (STAGES[stage] === 'Route') return <RouteStep run={run} />
              if (STAGES[stage] === 'Answer') return <AnswerStep run={run} replay={r} />
              return <StageSummary stage={stage} run={run} />
            }}
            renderRoutes={(r) => <p className="text-small m-0">Recorded modes: {Object.keys(r.runs).join(', ')}</p>}
          />
        )}
      </div>
    </div>
  )
}
