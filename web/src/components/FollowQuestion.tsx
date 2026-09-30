import { useState } from 'react'
import { liveEnabled } from '../data/live'
import { loadReplay } from '../data/load'
import { ordered } from '../data/replay'
import { useLoaded } from '../data/useLoaded'
import type { Replay, ReplayIndex } from '../types'
import { DataMissing } from './DataMissing'
import { EveryRoute } from './EveryRoute'
import { ChevronDownIcon } from './Icons'
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
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)] lg:gap-8">
        <div className="min-w-0 lg:sticky lg:top-32">
          <button
            type="button"
            className="mb-3 inline-flex min-h-11 w-full cursor-pointer items-center justify-between rounded-[2px] border border-rule bg-surface px-4 text-[15px] font-[560] text-ink shadow-sm lg:hidden"
            aria-expanded={listOpen}
            onClick={() => setListOpen(!listOpen)}
          >
            Choose a question
            <ChevronDownIcon size={18} className={`transition-transform ${listOpen ? 'rotate-180' : ''}`} />
          </button>
          <div className={`${listOpen ? 'block' : 'hidden lg:block'} rounded-[2px] border border-rule bg-sunken p-2 lg:max-h-[calc(100vh-160px)] lg:overflow-y-auto`}>
            <ReplayList items={index.items} current={live ? '' : current} onPick={pick} />
          </div>
        </div>
        <div className="min-w-0">
          {replay.status === 'loading' && <div className="card h-96 animate-pulse" aria-label="Loading" />}
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
