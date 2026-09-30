import { headlineStats } from '../../data/headline'
import type { Results } from '../../types'
import { RunId } from '../RunId'

export function HeroStats({ results }: { results: Results }) {
  const h = headlineStats(results)
  if (!h) return null
  return (
    <div className="mt-16 md:mt-20">
      <dl className="card m-0 grid grid-cols-2 overflow-hidden p-0 lg:grid-cols-4">
        {h.stats.map((s, i) => (
          <div
            key={s.label}
            className={`p-5 md:p-7 ${i % 2 === 1 ? 'border-l border-rule' : ''} ${i >= 2 ? 'border-t border-rule lg:border-t-0' : ''} ${i === 2 ? 'lg:border-l' : ''}`}
          >
            <dt className="text-[13.5px] leading-5 font-[560] text-muted">{s.label}</dt>
            <dd className="m-0 mt-2">
              <span className="block text-[34px] leading-10 font-[680] tracking-[-0.03em] text-ink md:text-[42px] md:leading-[48px]">{s.value}</span>
              <span className="text-caption mt-1 block">{s.detail}</span>
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-caption m-0 mt-3">
        Held out test split, {h.n} questions, router run <RunId id={h.runId} />.
      </p>
    </div>
  )
}
