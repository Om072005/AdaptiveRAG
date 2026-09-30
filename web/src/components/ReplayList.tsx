import { LABEL } from '../copy/reasons'
import { GROUPS, OUTCOME, type ReplayItem } from '../data/replay'

const TONE: Record<ReplayItem['outcome'], string> = {
  correct: 'bg-good-soft text-good',
  partial: 'bg-warn-soft text-warn',
  wrong: 'bg-bad-soft text-bad',
  misrouted: 'bg-bad-soft text-bad',
}

export function ReplayList({ items, current, onPick }: { items: ReplayItem[]; current: string; onPick: (id: string) => void }) {
  return (
    <div>
      {GROUPS.map((g) => {
        const group = items.filter(g.pick)
        if (!group.length) return null
        return (
          <div key={g.title} className="mb-6 last:mb-0">
            <h3 className="m-0 mb-2 px-1 text-[12.5px] leading-5 font-[650] tracking-[0.06em] text-muted uppercase">{g.title}</h3>
            <ul className="m-0 list-none space-y-1.5 p-0">
              {group.map((item) => (
                <li key={item.question_id}>
                  <button
                    type="button"
                    onClick={() => onPick(item.question_id)}
                    aria-current={item.question_id === current ? 'true' : undefined}
                    className="block w-full cursor-pointer rounded-[2px] border border-transparent bg-transparent px-3.5 py-3 text-left text-[14.5px] leading-[22px] text-text transition-colors hover:border-rule hover:bg-surface aria-[current=true]:border-accent aria-[current=true]:bg-surface aria-[current=true]:text-ink aria-[current=true]:shadow-sm"
                  >
                    {item.question}
                    <span className="mt-1.5 flex items-center gap-2">
                      {g.title === 'Went wrong' && <span className="text-caption">{LABEL[item.type] ?? item.type}</span>}
                      <span className={`rounded-[2px] px-2 py-px text-[12px] leading-5 font-[600] ${TONE[item.outcome]}`}>{OUTCOME[item.outcome]}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
