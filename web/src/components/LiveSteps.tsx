import { describeStep, type LiveStep } from '../data/liveSteps'

type Props = { steps: LiveStep[]; thinking: string; answer: string; busy: boolean }

function StepRow({ step, n }: { step: LiveStep; n: number }) {
  const { headline, details } = describeStep(step)
  return (
    <li className="grid grid-cols-[28px_96px_minmax(0,1fr)] gap-x-3 border-t border-rule py-2.5 first:border-t-0 max-sm:grid-cols-[28px_minmax(0,1fr)]">
      <span className="font-mono text-[12px] leading-6 text-muted tabular-nums">{String(n).padStart(2, '0')}</span>
      <span className="font-mono text-[12px] leading-6 tracking-[0.06em] text-ink uppercase">{step.step}</span>
      <div className="min-w-0 max-sm:col-start-2">
        <p className="m-0 text-[15.5px] leading-6 break-words text-ink">{headline}</p>
        {details.map((d) => (
          <p key={d} className="text-caption m-0 break-words">
            {d}
          </p>
        ))}
      </div>
    </li>
  )
}

function Streamed({ label, text, mono }: { label: string; text: string; mono?: boolean }) {
  return (
    <div className="border-t border-rule py-3">
      <p className="text-label m-0 mb-2">{label}</p>
      <p
        className={`m-0 max-h-56 overflow-y-auto break-words whitespace-pre-wrap ${mono ? 'font-mono text-[12.5px] leading-5 text-muted' : 'text-body text-text'}`}
      >
        {text}
      </p>
    </div>
  )
}

/** A live question as it runs: every step the moment it ends, the model's own reasoning and the
 * answer as they are written. Shown under the question box, kept after the answer arrives. */
export function LiveSteps({ steps, thinking, answer, busy }: Props) {
  const split = steps.findIndex((s) => s.step === 'model') + 1 || steps.length
  const before = steps.slice(0, split)
  const after = steps.slice(split)
  return (
    <section aria-label="Live steps" className="card mb-8 p-5 md:p-6">
      <p className="text-label m-0 mb-2">{busy ? 'Working, step by step' : 'How this answer was made'}</p>
      <ol className="m-0 list-none p-0" role="log">
        {before.map((s, i) => (
          <StepRow key={`${s.step}-${i}`} step={s} n={i + 1} />
        ))}
      </ol>
      {thinking && <Streamed label="The model's reasoning" text={thinking} mono />}
      {answer && <Streamed label="The answer as it is written" text={answer} />}
      <ol className="m-0 list-none p-0" role="log">
        {after.map((s, i) => (
          <StepRow key={`${s.step}-${split + i}`} step={s} n={split + i + 1} />
        ))}
      </ol>
      {busy && <p className="text-caption m-0 mt-2 animate-pulse">Waiting for the next step</p>}
    </section>
  )
}
