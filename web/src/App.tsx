import { DataMissing } from './components/DataMissing'
import { FollowQuestion } from './components/FollowQuestion'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/hero/Hero'
import { ResultsView } from './components/results/ResultsView'
import { RunIt } from './components/RunIt'
import { SampleBanner } from './components/SampleBanner'
import { Section } from './components/Section'
import { RouteCards } from './components/story/RouteCards'
import { Steps } from './components/story/Steps'
import { Team } from './components/Team'
import { Workflows } from './components/workflows/Workflows'
import { Architecture } from './diagrams/Architecture'
import { JourneyMap } from './journey/JourneyMap'
import { JourneyProvider } from './journey/JourneyProvider'
import { JourneyRecap } from './journey/JourneyRecap'
import { loadReplayIndex, loadResults, loadSite } from './data/load'
import { useLoaded } from './data/useLoaded'

const REPO_URL = 'https://github.com/Om072005/AdaptiveRAG'

const Loading = () => <div className="h-64 animate-pulse border border-rule" aria-label="Loading" />

export default function App() {
  const replays = useLoaded(loadReplayIndex)
  const results = useLoaded(loadResults)
  const site = useLoaded(loadSite)
  const sample = [replays, results, site].some((s) => s.status === 'ok' && s.sample)

  return (
    <JourneyProvider>
      {sample && <SampleBanner />}
      <Header repoUrl={REPO_URL} />
      <main id="top">
        <Hero repoUrl={REPO_URL} results={results} />
        <JourneyMap />
        <Section
          id="idea"
          title="No single search method fits every question."
          lede="Some questions are a quick lookup, others join or compare facts. So there are three ways to search."
        >
          <RouteCards />
        </Section>
        <Section
          id="how"
          title="From question to cited answer in five steps."
          lede="Select any box in the diagram for detail."
        >
          <Steps />
          <div className="mt-8">
            <Architecture />
          </div>
        </Section>
        <Section
          id="follow"
          title="Watch it answer real questions."
          lede="Recorded runs, step by step. Some went wrong, on purpose."
        >
          {replays.status === 'loading' && <Loading />}
          {replays.status === 'missing' && <DataMissing />}
          {replays.status === 'error' && <DataMissing error={replays.message} />}
          {replays.status === 'ok' && <FollowQuestion index={replays.data} />}
        </Section>
        <Section
          id="results"
          title="Measured, not claimed."
          lede="Every chart names the run it came from. Hover for detail."
        >
          {results.status === 'loading' && <Loading />}
          {results.status === 'missing' && <DataMissing />}
          {results.status === 'error' && <DataMissing error={results.message} />}
          {results.status === 'ok' && <ResultsView results={results.data} />}
        </Section>
        <Section
          id="workflows"
          title="How the pieces are built."
          lede="Four workflows, drawn from the same data as the code."
        >
          <Workflows />
        </Section>
        <Section
          id="run"
          title="Everything runs on your own machine."
          lede="Open models, a bundled database, no API keys."
        >
          <RunIt />
        </Section>
        <Section id="team" title="The team.">
          {site.status === 'loading' && <Loading />}
          {site.status === 'ok' && <Team site={site.data} />}
          {site.status === 'missing' && <p className="text-small m-0 text-muted">The team list is published with the final page.</p>}
          {site.status === 'error' && <DataMissing error={site.message} />}
        </Section>
        <JourneyRecap repoUrl={REPO_URL} />
      </main>
      <Footer repoUrl={REPO_URL} />
    </JourneyProvider>
  )
}
