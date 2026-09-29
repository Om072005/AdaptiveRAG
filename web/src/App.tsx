import { DataMissing } from './components/DataMissing'
import { SampleBanner } from './components/SampleBanner'
import { loadReplayIndex, loadResults } from './data/load'
import { useLoaded } from './data/useLoaded'

const REPO_URL = 'https://github.com/Om072005/AdaptiveRAG'
const OUTCOME = { correct: 'Correct', partial: 'Partial', wrong: 'Wrong', misrouted: 'Misrouted' }

export default function App() {
  const replays = useLoaded(loadReplayIndex)
  const results = useLoaded(loadResults)
  const sample = [replays, results].some((s) => s.status === 'ok' && s.sample)

  return (
    <>
      {sample && <SampleBanner />}
      <header className="page-wrap flex items-center justify-between py-6">
        <span className="font-serif text-[22px] leading-7 text-white">AdaptiveRAG</span>
        <a className="text-small" href={REPO_URL}>
          GitHub
        </a>
      </header>
      <main>
        <section className="border-t border-rule">
          <div className="page-wrap page-grid pt-20 pb-32 md:pt-32 md:pb-40">
            <div className="col-span-4 md:col-span-8">
              <h1 className="text-statement m-0">A research assistant that decides how to search before it answers.</h1>
              <p className="text-lede mt-6">
                AdaptiveRAG routes each question to vector search, graph traversal or both, answers with citations,
                and records the cost and latency of every decision.
              </p>
              <p className="text-small mt-6 text-muted">
                The page is being built. Everything it will show comes from recorded runs.
              </p>
            </div>
          </div>
        </section>
        <section id="follow" className="border-t border-rule">
          <div className="page-wrap pt-20 pb-32 md:pt-28 lg:pt-40">
            <h2 className="text-display m-0">Follow a question</h2>
            <div className="mt-16">
              {replays.status === 'loading' && <div className="h-px w-64 bg-rule" aria-label="Loading" />}
              {replays.status === 'missing' && <DataMissing />}
              {replays.status === 'error' && <DataMissing error={replays.message} />}
              {replays.status === 'ok' && (
                <ul className="m-0 list-none p-0">
                  {replays.data.items.map((item) => (
                    <li key={item.question_id} className="text-small border-b border-rule py-3">
                      {item.question} <span className="text-muted">{OUTCOME[item.outcome]}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      </main>
    </>
  )
}
