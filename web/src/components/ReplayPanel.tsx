import { type KeyboardEvent, type ReactNode, useState } from 'react'
import { day } from '../copy/format'
import { LIVE_ID, type RecordedRun, STAGES, mainRun } from '../data/replay'
import type { Replay } from '../types'
import { Button } from './Button'
import { RunId } from './RunId'
import { StageRail } from './StageRail'
import { Tabs } from './Tabs'

const TABS = ['Step by step', 'Every route'] as const
type Props = {
  replay: Replay
  renderStage: (stage: number, run: RecordedRun, replay: Replay) => ReactNode
  renderRoutes: (replay: Replay) => ReactNode
}

export function ReplayPanel({ replay, renderStage, renderRoutes }: Props) {
  const [tab, setTab] = useState<(typeof TABS)[number]>('Step by step')
  const [stage, setStage] = useState(0)
  const main = mainRun(replay)
  const go = (i: number) => setStage(Math.max(0, Math.min(STAGES.length - 1, i)))
  const onKey = (e: KeyboardEvent) => {
    if (tab !== 'Step by step') return
    if (e.key === 'ArrowRight') go(stage + 1)
    if (e.key === 'ArrowLeft') go(stage - 1)
  }

  return (
    <article aria-labelledby="qtitle" onKeyDown={onKey} className="card min-w-0 overflow-hidden p-0 shadow-md">
      <div className="flex items-center justify-between gap-4 border-b border-rule bg-sunken px-5 py-3 md:px-8">
        <div className="flex items-center gap-1.5" aria-hidden="true">
          <span className="size-2.5 rounded-full bg-faint" />
          <span className="size-2.5 rounded-full bg-faint" />
          <span className="size-2.5 rounded-full bg-faint" />
        </div>
        <span className="text-caption">Use the arrow keys to move between steps</span>
      </div>
      <div className="p-5 md:p-8">
      <p className="text-caption m-0 mb-1.5 font-[600]">Question</p>
      <h3 id="qtitle" className="m-0 max-w-[40ch] text-[21px] leading-7 font-[650] tracking-[-0.015em] text-ink md:text-[25px] md:leading-8">
        {replay.question}
      </h3>
      {main && replay.question_id === LIVE_ID && (
        <p className="text-caption m-0 mt-3">
          Live answer, trace <RunId id={main.run.run_id} />
        </p>
      )}
      {main && replay.question_id !== LIVE_ID && (
        <p className="text-caption m-0 mt-3">
          Recorded run <RunId id={main.run.run_id} /> on {day(replay.recorded_at)}
        </p>
      )}
      {replay.question_id !== LIVE_ID && <Tabs tabs={TABS} current={tab} onPick={setTab} />}
      {tab === 'Step by step' && main && (
        <>
          <StageRail current={stage} onPick={go} />
          <div key={stage} className="fade-in mt-8" aria-live="polite">
            {renderStage(stage, main.run, replay)}
          </div>
          <div className="mt-8 flex justify-between gap-3 border-t border-rule pt-5">
            <Button onClick={() => go(stage - 1)} disabled={stage === 0}>
              Previous step
            </Button>
            <Button kind="primary" onClick={() => go(stage + 1)} disabled={stage === STAGES.length - 1}>
              Next step
            </Button>
          </div>
        </>
      )}
      {tab === 'Every route' && <div className="fade-in mt-8">{renderRoutes(replay)}</div>}
      </div>
    </article>
  )
}
