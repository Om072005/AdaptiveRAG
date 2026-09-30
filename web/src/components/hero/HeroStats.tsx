import { headlineStats } from '../../data/headline'
import type { Results } from '../../types'
import { RunId } from '../RunId'

/** The headline numbers as newspaper columns between rules. */
export function HeroStats({ results }: { results: Results }) {
  const h = headlineStats(results)
  if (!h) return null
  return (
    <div className="mt-10">
      <dl className="m-0 grid grid-cols-2 border-y border-ink lg:grid-cols-4">
        {h.stats.map((s, i) => (
          <div
            key={s.label}
            className={`px-4 py-5 md:px-6 md:py-6 ${i % 2 === 1 ? 'border-l border-rule' : ''} ${i >= 2 ? 'border-t border-rule lg:border-t-0' : ''} ${i === 2 ? 'lg:border-l' : ''}`}
          >
            <dt className="text-label">{s.label}</dt>
            <dd className="m-0 mt-2">
              <span className="block font-headline text-[40px] leading-[0.9] text-ink sm:text-[48px] md:text-[64px]">{s.value}</span>
              <span className="text-caption mt-2 block">{s.detail}</span>
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
