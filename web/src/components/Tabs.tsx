export function Tabs<T extends string>({ tabs, current, onPick }: { tabs: readonly T[]; current: T; onPick: (t: T) => void }) {
  return (
    <div role="tablist" className="mt-8 flex gap-6 border-b border-rule">
      {tabs.map((t) => (
        <button
          key={t}
          type="button"
          role="tab"
          aria-selected={t === current}
          onClick={() => onPick(t)}
          className="-mb-px cursor-pointer border-0 border-b border-transparent bg-transparent px-0 pb-3 text-[15px] leading-6 font-medium text-muted aria-selected:border-cream-100 aria-selected:text-white"
        >
          {t}
        </button>
      ))}
    </div>
  )
}
