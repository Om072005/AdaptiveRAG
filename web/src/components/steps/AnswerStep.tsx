import { useState } from 'react'
import { score } from '../../copy/format'
import { LIVE_ID, NOT_ENOUGH, type RecordedRun, explanationParts } from '../../data/replay'
import type { Replay } from '../../types'
import { JudgeScores } from '../JudgeScores'

export function AnswerStep({ run, replay }: { run: RecordedRun; replay: Replay }) {
  const [active, setActive] = useState<number | null>(null)
  const answer = run.response.answer
  const notEnough = answer.short.trim().toLowerCase().startsWith(NOT_ENOUGH)
  const known = new Set(answer.citations.map((c) => c.n))

  return (
    <div>
      <p className={`m-0 text-[28px] leading-9 font-[680] tracking-[-0.02em] md:text-[32px] md:leading-10 ${notEnough ? 'text-muted' : 'text-ink'}`}>
        {notEnough ? 'Not enough context' : answer.short}
      </p>
      <p className="text-body mt-4 mb-0">
        {explanationParts(answer.text, answer.short).map((part, i) =>
          typeof part === 'string' ? (
            <span key={i}>{part}</span>
          ) : (
            <sup key={i}>
              <button
                type="button"
                disabled={!known.has(part)}
                aria-pressed={active === part}
                aria-label={`Source ${part}`}
                onClick={() => setActive(active === part ? null : part)}
                className="mx-0.5 inline-flex min-w-5 cursor-pointer items-center justify-center rounded-[6px] border-0 bg-accent-soft px-1.5 py-0.5 text-[12px] leading-4 font-[650] text-accent-text aria-pressed:bg-accent aria-pressed:text-accent-ink disabled:cursor-default disabled:bg-sunken disabled:text-muted"
              >
                {part}
              </button>
            </sup>
          ),
        )}
      </p>

      <h4 className="text-caption m-0 mt-8 mb-2 font-[600]">Sources</h4>
      {answer.citations.length === 0 && <p className="text-small m-0 text-muted">No sources were cited.</p>}
      <ol className="m-0 list-none space-y-2 p-0">
        {answer.citations.map((c) => (
          <li
            key={c.n}
            className={`text-small rounded-[10px] border py-2.5 pr-3 pl-3.5 transition-colors ${active === c.n ? 'border-accent bg-accent-soft text-ink' : 'border-rule bg-surface'}`}
          >
            <span className="mr-1.5 inline-flex size-5 items-center justify-center rounded-[5px] bg-sunken text-[12px] font-[650] text-accent-text">{c.n}</span>
            <span className="font-[560] text-ink">{c.title}</span>
            <span className="text-caption block">{c.snippet}</span>
          </li>
        ))}
      </ol>

      {replay.gold_answer !== '' && (
        <dl className="m-0 mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-[12px] border border-rule bg-sunken p-3.5">
            <dt className="text-caption">Gold answer</dt>
            <dd className="m-0 mt-0.5 text-[15px] leading-6 font-[600] text-ink">{replay.gold_answer}</dd>
          </div>
          <div className="rounded-[12px] border border-rule bg-sunken p-3.5">
            <dt className="text-caption">Exact match</dt>
            <dd className="m-0 mt-0.5 text-[15px] leading-6 font-[600] text-ink">{score(run.metrics.em)}</dd>
          </div>
          <div className="rounded-[12px] border border-rule bg-sunken p-3.5">
            <dt className="text-caption">Token F1</dt>
            <dd className="m-0 mt-0.5 text-[15px] leading-6 font-[600] text-ink">{score(run.metrics.f1)}</dd>
          </div>
        </dl>
      )}
      <JudgeScores
        judgement={run.judgement}
        liveTraceId={replay.question_id === LIVE_ID ? run.response.trace_id : undefined}
      />
    </div>
  )
}
