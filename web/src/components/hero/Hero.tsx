import type { LoadState } from '../../data/useLoaded'
import { TOTAL_MINUTES } from '../../journey/chapters'
import type { Results } from '../../types'
import { ButtonLink } from '../Button'
import { ArrowRightIcon } from '../Icons'
import { HeroDemo } from './HeroDemo'
import { HeroStats } from './HeroStats'

/** The front page: three ruled columns (the story, the headline, the demo), then the name in an ink
 * block and the headline numbers. */
export function Hero({ repoUrl, results }: { repoUrl: string; results: LoadState<Results> }) {
  return (
    <section id="front" aria-label="Front page">
      <div className="page-wrap pt-8 pb-16 md:pt-10 md:pb-20">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,3fr)_minmax(0,5fr)_minmax(0,4fr)] lg:gap-0">
          <div className="order-2 min-w-0 lg:order-1 lg:border-r lg:border-rule lg:pr-8">
            <p className="text-label m-0 mb-3">The story</p>
            <p className="drop-cap m-0 font-sans text-[20px] leading-[26px] text-text">
              AdaptiveRAG reads a question and decides how to look for the answer: by meaning, by following links
              between facts, or both. Then it answers with sources you can check, and records what every step cost.
              Everything on this page comes from recorded runs.
            </p>
            <div className="mt-8 flex flex-col gap-3">
              <ButtonLink kind="primary" href="#route">
                Take the tour
                <ArrowRightIcon size={15} />
              </ButtonLink>
              <ButtonLink href="#follow">
                Skip to the demo
              </ButtonLink>
              <a href={repoUrl} className="self-start font-sans text-[18px]">
                or read the code on GitHub
              </a>
            </div>
          </div>

          <div className="order-1 flex min-w-0 flex-col items-center justify-center text-center lg:order-2 lg:border-r lg:border-rule lg:px-8">
            <p className="text-label m-0">Adaptive retrieval · question answering · v1.0</p>
            <h1 className="text-statement m-0 mt-4">
              Every question gets the search it needs.
            </h1>
            <p className="m-0 mt-5 max-w-[30ch] font-sans text-[24px] leading-[28px] text-text italic md:text-[27px] md:leading-[31px]">
              Vector search, a knowledge graph, or both, chosen one question at a time.
            </p>
            <p className="m-0 mt-5 font-sans text-[16px] leading-6 text-muted">
              <span className="font-headline text-ink">Tip!</span> The card replays three real questions. The tour takes about {TOTAL_MINUTES} minutes.
            </p>
          </div>

          <div className="order-3 min-w-0 lg:pl-8">
            <HeroDemo />
          </div>
        </div>

        <div className="ink-block mt-12 overflow-hidden px-[2cqw] pt-[3.5cqw] pb-[1.5cqw] [container-type:inline-size] md:mt-16" aria-hidden="true">
          <p className="m-0 text-center font-headline text-[16.9cqw] leading-[0.8] tracking-[-0.025em] whitespace-nowrap">
            AdaptiveRAG
          </p>
        </div>

        {results.status === 'ok' && <HeroStats results={results.data} />}
      </div>
    </section>
  )
}
