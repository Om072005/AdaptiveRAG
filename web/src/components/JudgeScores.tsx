import { useState } from 'react'
import { money } from '../copy/format'
import { judgeLive } from '../data/live'
import type { Judgement } from '../types'
import { Button } from './Button'
import { ScoreBar } from './ScoreBar'

const METRICS = [
  ['faithfulness', 'Faithfulness'],
  ['relevance', 'Relevance'],
  ['completeness', 'Completeness'],
] as const

function Scores({ j }: { j: Judgement }) {
  return (
    <div>
      <dl className="m-0 grid grid-cols-1 gap-x-8 sm:grid-cols-3">
        {METRICS.map(([key, name]) => (
          <div key={key} className="mb-4">
            <dt className="text-caption">{name}</dt>
            <dd className="m-0 text-[15px] leading-6">
              <ScoreBar value={j[key]} label={name} />
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-small m-0 max-w-[68ch]">{j.rationale}</p>
      <p className="text-caption m-0 mt-2">
        Judge cost {money(j.cost_usd)}.
        {j.flagged && (j.queued ? ' Below the threshold, so it waits in the review queue.' : ' Below the threshold.')}
      </p>
    </div>
  )
}

/** The judge's recorded scores, or locally a button that asks the API to judge a live answer. */
export function JudgeScores({ judgement, liveTraceId }: { judgement: Judgement | null; liveTraceId?: string }) {
  const [asked, setAsked] = useState<Judgement | null>(null)
  const [state, setState] = useState<'idle' | 'busy' | string>('idle')
  const shown = judgement ?? asked

  const ask = async () => {
    if (!liveTraceId) return
    setState('busy')
    try {
      setAsked(await judgeLive(liveTraceId))
      setState('idle')
    } catch (e) {
      setState(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <section aria-label="Judge scores" className="mt-6 rounded-[2px] border border-rule p-5">
      <h4 className="text-caption m-0 mb-3 font-[600]">Judge, a different model family from the generator</h4>
      {shown && <Scores j={shown} />}
      {!shown && !liveTraceId && <p className="text-small m-0 text-muted">This answer was not judged.</p>}
      {!shown && liveTraceId && (
        <>
          <Button onClick={ask} disabled={state === 'busy'}>
            {state === 'busy' ? 'Judging' : 'Judge this answer'}
          </Button>
          {state !== 'idle' && state !== 'busy' && (
            <p role="alert" className="text-small m-0 mt-3 text-muted">
              {state}
            </p>
          )}
        </>
      )}
    </section>
  )
}
