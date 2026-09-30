import { STAGES } from '../data/replay'

/** The six stages as a stepper: done, current and still to come. */
export function StageRail({ current, onPick }: { current: number; onPick: (i: number) => void }) {
  return (
    <div className="mt-6">
      <ol aria-label="Stages" className="m-0 flex list-none gap-1.5 overflow-x-auto p-0 pb-1">
        {STAGES.map((name, i) => (
          <li key={name}>
            <button
              type="button"
              onClick={() => onPick(i)}
              aria-current={i === current ? 'step' : undefined}
              className={`inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-[14px] leading-6 font-[560] whitespace-nowrap transition-colors aria-[current=step]:border-accent aria-[current=step]:bg-accent aria-[current=step]:text-accent-ink ${i < current ? 'border-rule bg-accent-soft text-accent-text' : 'border-rule bg-surface text-muted hover:text-ink'}`}
            >
              <span className="text-[12.5px] font-[700] tabular-nums">{i + 1}</span> {name}
            </button>
          </li>
        ))}
      </ol>
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-sunken" aria-hidden="true">
        <div className="h-full rounded-full bg-accent transition-[width] duration-300 ease-page" style={{ width: `${((current + 1) / STAGES.length) * 100}%` }} />
      </div>
    </div>
  )
}
