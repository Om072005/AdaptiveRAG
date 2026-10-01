import { DataMissing } from './components/DataMissing'
import { FollowQuestion } from './components/FollowQuestion'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/hero/Hero'
import { FailureModes } from './components/results/FailureModes'
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
          lede="Some questions are a quick lookup. Others need two facts joined together, or two things compared. AdaptiveRAG has three ways to find evidence and picks the right one each time."
        >
          <RouteCards />
        </Section>
        <Section
          id="how"
          title="From question to cited answer in five steps."
          lede="Each step is its own small, measured piece. Select any box in the diagram below to see what it does and where it lives in the code."
        >
          <Steps />
          <div className="mt-8">
            <Architecture />
          </div>
        </Section>
        <Section
          id="follow"
          title="Watch it answer real questions."
          lede="Each of these is a recorded run. Step through what the router decided, what it found, which model answered and what it cost. Some went wrong, and they are here on purpose."
        >
          {replays.status === 'loading' && <Loading />}
          {replays.status === 'missing' && <DataMissing />}
          {replays.status === 'error' && <DataMissing error={replays.message} />}
          {replays.status === 'ok' && <FollowQuestion index={replays.data} />}
        </Section>
        <Section
          id="results"
          title="Measured, not claimed."
          lede="Every chart comes from a pinned run and names it. Hover for detail, or switch any chart to its table. Where a result was worse than expected, it stays."
        >
          {results.status === 'loading' && <Loading />}
          {results.status === 'missing' && <DataMissing />}
          {results.status === 'error' && <DataMissing error={results.message} />}
          {results.status === 'ok' && <ResultsView results={results.data} />}
        </Section>
        <Section
          id="failures"
          title="What went wrong, and what we did about it."
          lede="Real incidents found in a run or in review, with the run that showed them."
        >
          <FailureModes failures={results.status === 'ok' ? results.data.tables.failures : null} />
        </Section>
        <Section
          id="workflows"
          title="How the pieces are built."
          lede="Four workflows, drawn from the same data as the code. Pick a step, or play the walkthrough to see each part light up in order."
        >
          <Workflows />
        </Section>
        <Section
          id="run"
          title="Everything runs on your own machine."
          lede="Open models through Ollama and a Postgres that ships with the code. No account, no API keys, and offline once the models are downloaded."
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
