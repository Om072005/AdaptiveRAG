import { DataMissing } from './components/DataMissing'
import { FollowQuestion } from './components/FollowQuestion'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { SampleBanner } from './components/SampleBanner'
import { Section } from './components/Section'
import { loadReplayIndex, loadResults } from './data/load'
import { useLoaded } from './data/useLoaded'

const REPO_URL = 'https://github.com/Om072005/AdaptiveRAG'

export default function App() {
  const replays = useLoaded(loadReplayIndex)
  const results = useLoaded(loadResults)
  const sample = [replays, results].some((s) => s.status === 'ok' && s.sample)

  return (
    <>
      {sample && <SampleBanner />}
      <Header repoUrl={REPO_URL} />
      <main id="top">
        <Hero repoUrl={REPO_URL} />
        <Section
          id="how"
          title="One question, three ways to find the answer."
          lede="A classifier reads the question, a budgeter picks a route, and every answer is judged and logged."
        >
          {null}
        </Section>
        <Section
          id="follow"
          title="Follow a question through the system."
          lede="Each of these is a real recorded run. Step through what the router decided, what it found, which model answered, and what it cost. Some of them went wrong, and they are here on purpose."
        >
          {replays.status === 'loading' && <div className="h-px w-64 bg-rule" aria-label="Loading" />}
          {replays.status === 'missing' && <DataMissing />}
          {replays.status === 'error' && <DataMissing error={replays.message} />}
          {replays.status === 'ok' && <FollowQuestion index={replays.data} />}
        </Section>
        <Section
          id="workflows"
          title="How the pieces are built."
          lede="Ingestion, the router's full decision logic, the graph schema and the evaluation loop, drawn from the same data as the code."
        >
          {null}
        </Section>
        <Section
          id="results"
          title="What we measured."
          lede="Only pinned runs appear here, and every table names the run it came from. Where a result was worse than expected, it stays."
        >
          {results.status !== 'ok' && results.status !== 'loading' && <DataMissing />}
        </Section>
        <Section
          id="run"
          title="Run it yourself."
          lede="The whole system runs on a laptop with free accounts for Neon, Groq and Google AI Studio."
        >
          {null}
        </Section>
        <Section id="team" title="Who built it.">
          {null}
        </Section>
      </main>
      <Footer repoUrl={REPO_URL} />
    </>
  )
}
