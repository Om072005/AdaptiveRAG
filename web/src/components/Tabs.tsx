export function Tabs<T extends string>({ tabs, current, onPick }: { tabs: readonly T[]; current: T; onPick: (t: T) => void }) {
  return (
    <div role="tablist" className="mt-6 inline-flex gap-1 rounded-[2px] border border-rule bg-sunken p-1">
      {tabs.map((t) => (
        <button
          key={t}
          type="button"
          role="tab"
          aria-selected={t === current}
          onClick={() => onPick(t)}
          className="min-h-9 cursor-pointer rounded-[2px] border-0 bg-transparent px-4 text-[14px] leading-6 font-[560] text-muted transition-colors hover:text-ink aria-selected:bg-surface aria-selected:text-ink aria-selected:shadow-sm"
        >
          {t}
        </button>
      ))}
    </div>
  )
}
