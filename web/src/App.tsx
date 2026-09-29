import { DataMissing } from './components/DataMissing'
import { FollowQuestion } from './components/FollowQuestion'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { FailureModes } from './components/results/FailureModes'
import { ResultsView } from './components/results/ResultsView'
import { RunIt } from './components/RunIt'
import { SampleBanner } from './components/SampleBanner'
import { Section } from './components/Section'
import { Team } from './components/Team'
import { Workflows } from './components/Workflows'
import { Architecture } from './diagrams/Architecture'
import { loadReplayIndex, loadResults, loadSite } from './data/load'
import { useLoaded } from './data/useLoaded'

const REPO_URL = 'https://github.com/Om072005/AdaptiveRAG'

export default function App() {
  const replays = useLoaded(loadReplayIndex)
  const results = useLoaded(loadResults)
  const site = useLoaded(loadSite)
  const sample = [replays, results, site].some((s) => s.status === 'ok' && s.sample)

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
          <Architecture />
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
          <Workflows />
        </Section>
        <Section
          id="results"
          title="What we measured."
          lede="Only pinned runs appear here, and every table names the run it came from. Where a result was worse than expected, it stays."
        >
          {results.status === 'loading' && <div className="h-px w-64 bg-rule" aria-label="Loading" />}
          {results.status === 'missing' && <DataMissing />}
          {results.status === 'error' && <DataMissing error={results.message} />}
          {results.status === 'ok' && <ResultsView results={results.data} />}
        </Section>
        <Section
          id="failures"
          title="What went wrong."
          lede="Real incidents found in a run or in review, with the run that showed them."
        >
          <FailureModes failures={results.status === 'ok' ? results.data.tables.failures : null} />
        </Section>
        <Section
          id="run"
          title="Run it yourself."
          lede="The whole system runs on one machine with Ollama for the models, a free Neon database and a free Google AI Studio key for the judge."
        >
          <RunIt />
        </Section>
        <Section id="team" title="Who built it.">
          {site.status === 'loading' && <div className="h-px w-64 bg-rule" aria-label="Loading" />}
          {site.status === 'ok' && <Team site={site.data} />}
          {site.status === 'missing' && <p className="text-small m-0 text-muted">The team list is published with the final page.</p>}
          {site.status === 'error' && <DataMissing error={site.message} />}
        </Section>
      </main>
      <Footer repoUrl={REPO_URL} />
    </>
  )
}
