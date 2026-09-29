import { useState } from 'react'
import { liveEnabled } from '../data/live'
import { loadReplay } from '../data/load'
import { ordered } from '../data/replay'
import { useLoaded } from '../data/useLoaded'
import type { Replay, ReplayIndex } from '../types'
import { DataMissing } from './DataMissing'
import { EveryRoute } from './EveryRoute'
import { LiveAsk } from './LiveAsk'
import { ReplayList } from './ReplayList'
import { ReplayPanel } from './ReplayPanel'
import { StageView } from './steps/StageView'

export function FollowQuestion({ index }: { index: ReplayIndex }) {
  const [current, setCurrent] = useState(ordered(index.items)[0]?.question_id ?? '')
  const [listOpen, setListOpen] = useState(false)
  const [live, setLive] = useState<Replay | null>(null)
  const recorded = useLoaded(loadReplay, current)
  const replay = live ? ({ status: 'ok', data: live, sample: false } as const) : recorded
  const pick = (id: string) => {
    setCurrent(id)
    setLive(null)
    setListOpen(false)
  }

  return (
    <>
      {liveEnabled && <LiveAsk onAnswer={setLive} />}
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
            <ReplayList items={index.items} current={live ? '' : current} onPick={pick} />
          </div>
        </div>
        <div className="col-span-4 min-w-0 md:col-span-8 lg:col-span-9 xl:col-span-8">
          {replay.status === 'loading' && <div className="h-px w-64 bg-rule" aria-label="Loading" />}
          {replay.status === 'missing' && <DataMissing />}
          {replay.status === 'error' && <DataMissing error={replay.message} />}
          {replay.status === 'ok' && (
            <ReplayPanel
              key={live ? `live-${live.recorded_at}` : current}
              replay={replay.data}
              renderStage={(stage, run, r) => <StageView stage={stage} run={run} replay={r} />}
              renderRoutes={(r) => <EveryRoute replay={r} />}
            />
          )}
        </div>
      </div>
    </>
  )
}
