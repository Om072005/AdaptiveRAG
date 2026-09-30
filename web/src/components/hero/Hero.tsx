import type { LoadState } from '../../data/useLoaded'
import type { Results } from '../../types'
import { ButtonLink } from '../Button'
import { ArrowRightIcon, GitHubIcon } from '../Icons'
import { HeroDemo } from './HeroDemo'
import { HeroStats } from './HeroStats'

export function Hero({ repoUrl, results }: { repoUrl: string; results: LoadState<Results> }) {
  return (
    <section className="hero-glow relative overflow-hidden">
      <div className="page-wrap pt-14 pb-16 md:pt-24 md:pb-24">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-16">
          <div className="min-w-0">
            <p className="m-0 inline-flex flex-wrap items-center gap-2 rounded-full border border-rule bg-surface py-1 pr-3.5 pl-1 text-[13px] leading-5 font-[500] text-text shadow-sm">
              <span className="rounded-full bg-accent px-2 py-0.5 text-[12px] font-[600] text-accent-ink">v1.0</span>
              Open source, measured on HotpotQA
            </p>
            <h1 className="text-statement m-0 mt-6">
              Every question gets the search <span className="text-accent-text">it needs.</span>
            </h1>
            <p className="text-lede mt-6 mb-0">
              AdaptiveRAG reads a question, decides how to look for the answer (by meaning, by following links
              between facts, or both), then answers with sources you can check. Everything on this page comes from
              recorded runs.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <ButtonLink kind="primary" href="#follow">
                See it answer a question
                <ArrowRightIcon size={17} />
              </ButtonLink>
              <ButtonLink href={repoUrl}>
                <GitHubIcon size={17} />
                View the code on GitHub
              </ButtonLink>
            </div>
          </div>
          <div className="min-w-0">
            <HeroDemo />
          </div>
        </div>
        {results.status === 'ok' && <HeroStats results={results.data} />}
      </div>
    </section>
  )
}
