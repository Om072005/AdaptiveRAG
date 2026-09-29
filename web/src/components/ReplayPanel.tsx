import { type KeyboardEvent, type ReactNode, useState } from 'react'
import { day } from '../copy/format'
import { type RecordedRun, STAGES, mainRun } from '../data/replay'
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
    <article aria-labelledby="qtitle" onKeyDown={onKey} className="min-w-0 rounded-[10px] border border-rule p-6 md:p-10">
      <h3
        id="qtitle"
        className="m-0 max-w-[32ch] font-serif text-[24px] leading-8 font-normal text-white md:text-[28px] md:leading-9"
      >
        {replay.question}
      </h3>
      {main && (
        <p className="text-caption m-0 mt-3">
          Recorded run <RunId id={main.run.run_id} /> on {day(replay.recorded_at)}
        </p>
      )}
      <Tabs tabs={TABS} current={tab} onPick={setTab} />
      {tab === 'Step by step' && main && (
        <>
          <StageRail current={stage} onPick={go} />
          <div className="mt-10" aria-live="polite">
            {renderStage(stage, main.run, replay)}
          </div>
          <div className="mt-10 flex justify-between border-t border-rule pt-6">
            <Button onClick={() => go(stage - 1)} disabled={stage === 0}>
              Previous step
            </Button>
            <Button onClick={() => go(stage + 1)} disabled={stage === STAGES.length - 1}>
              Next step
            </Button>
          </div>
        </>
      )}
      {tab === 'Every route' && <div className="mt-10">{renderRoutes(replay)}</div>}
    </article>
  )
}
