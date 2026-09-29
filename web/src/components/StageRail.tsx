import { STAGES } from '../data/replay'

export function StageRail({ current, onPick }: { current: number; onPick: (i: number) => void }) {
  return (
    <ol aria-label="Stages" className="m-0 mt-6 flex list-none gap-2 overflow-x-auto p-0">
      {STAGES.map((name, i) => (
        <li key={name}>
          <button
            type="button"
            onClick={() => onPick(i)}
            aria-current={i === current ? 'step' : undefined}
            className={`cursor-pointer rounded-[6px] border border-rule bg-transparent px-3.5 py-2 text-[15px] leading-6 whitespace-nowrap aria-[current=step]:border-cream-100 aria-[current=step]:text-white ${i < current ? 'text-text' : 'text-muted'}`}
          >
            {i + 1} {name}
          </button>
        </li>
      ))}
    </ol>
  )
}
