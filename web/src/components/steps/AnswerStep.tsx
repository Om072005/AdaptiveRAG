import { useState } from 'react'
import { score } from '../../copy/format'
import { NOT_ENOUGH, type RecordedRun, explanationParts } from '../../data/replay'
import type { Replay } from '../../types'

export function AnswerStep({ run, replay }: { run: RecordedRun; replay: Replay }) {
  const [active, setActive] = useState<number | null>(null)
  const answer = run.response.answer
  const notEnough = answer.short.trim().toLowerCase().startsWith(NOT_ENOUGH)
  const known = new Set(answer.citations.map((c) => c.n))

  return (
    <div>
      <p className={`m-0 font-serif text-[28px] leading-9 md:text-[32px] md:leading-10 ${notEnough ? 'text-muted' : 'text-white'}`}>
        {notEnough ? 'Not enough context' : answer.short}
      </p>
      <p className="text-body mt-4 mb-0">
        {explanationParts(answer.text).map((part, i) =>
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
                className="inline-block min-w-5 cursor-pointer border-0 bg-transparent px-1 py-0.5 text-[13px] leading-4 text-cream-300 underline underline-offset-2 aria-pressed:text-white disabled:cursor-default disabled:no-underline"
              >
                {part}
              </button>
            </sup>
          ),
        )}
      </p>

      <h4 className="text-caption m-0 mt-8 mb-2 font-normal">Sources</h4>
      {answer.citations.length === 0 && <p className="text-small m-0 text-muted">No sources were cited.</p>}
      <ol className="m-0 list-none p-0">
        {answer.citations.map((c) => (
          <li
            key={c.n}
            className={`text-small border-l py-2 pl-4 ${active === c.n ? 'border-cream-100 text-white' : 'border-rule'}`}
          >
            <span className="text-muted">{c.n}</span> {c.title}
            <span className="text-caption block">{c.snippet}</span>
          </li>
        ))}
      </ol>

      {replay.gold_answer !== '' && (
        <dl className="m-0 mt-8 grid grid-cols-1 gap-x-8 border-t border-rule pt-6 sm:grid-cols-3">
          <div className="mb-4">
            <dt className="text-caption">Gold answer</dt>
            <dd className="m-0 text-[15px] leading-6">{replay.gold_answer}</dd>
          </div>
          <div className="mb-4">
            <dt className="text-caption">Exact match</dt>
            <dd className="m-0 text-[15px] leading-6">{score(run.metrics.em)}</dd>
          </div>
          <div className="mb-4">
            <dt className="text-caption">Token F1</dt>
            <dd className="m-0 text-[15px] leading-6">{score(run.metrics.f1)}</dd>
          </div>
        </dl>
      )}
    </div>
  )
}
