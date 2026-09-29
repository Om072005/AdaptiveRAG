import { GROUPS, OUTCOME, type ReplayItem } from '../data/replay'

export function ReplayList({ items, current, onPick }: { items: ReplayItem[]; current: string; onPick: (id: string) => void }) {
  return (
    <div>
      {GROUPS.map((g) => {
        const group = items.filter(g.pick)
        if (!group.length) return null
        return (
          <div key={g.title} className="mb-8">
            <h3 className="m-0 mb-2 font-sans text-[15px] leading-6 font-medium text-muted">{g.title}</h3>
            <ul className="m-0 list-none p-0">
              {group.map((item) => (
                <li key={item.question_id}>
                  <button
                    type="button"
                    onClick={() => onPick(item.question_id)}
                    aria-current={item.question_id === current ? 'true' : undefined}
                    className="block w-full cursor-pointer rounded-[6px] border border-transparent bg-transparent px-4 py-3 text-left text-[15px] leading-6 text-text hover:border-rule aria-[current=true]:border-cream-300 aria-[current=true]:text-white"
                  >
                    {item.question}
                    <span className="text-caption mt-0.5 block">{OUTCOME[item.outcome]}</span>
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
