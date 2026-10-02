import { ButtonLink } from '../components/Button'
import { ArrowRightIcon, CheckIcon, GitHubIcon } from '../components/Icons'
import { CHAPTERS, chapterNo, type Progress, summarize } from './chapters'
import { useJourney } from './context'

const STAMP: Record<Progress, { word: string; tone: string }> = {
  finished: { word: 'Read', tone: 'bg-canvas text-ink' },
  started: { word: 'Skimmed', tone: 'bg-accent text-accent-ink' },
  unseen: { word: 'Skipped', tone: 'border border-canvas/60 text-canvas' },
}

/** The end of the journey: every chapter, what it told the reader, and what they skipped, from what
 * they actually scrolled through on this visit. */
export function JourneyRecap({ repoUrl }: { repoUrl: string }) {
  const { progress } = useJourney()
  const count = summarize(progress)
  const seen = count.finished + count.started
  return (
    <section id="recap" aria-labelledby="recap-h" className="page-wrap pb-12">
      <div className="ink-block p-6 md:p-12">
        <div className="flex flex-wrap items-baseline justify-between gap-4 border-b border-canvas/30 pb-3">
          <p className="m-0 font-mono text-[12px] tracking-[0.08em] uppercase opacity-80">Your recap</p>
          <p className="m-0 font-mono text-[12px] tracking-[0.08em] uppercase opacity-80" aria-live="polite">
            {count.finished} read · {count.started} skimmed · {count.unseen} skipped
          </p>
        </div>
        <h2 id="recap-h" className="m-0 mt-6 font-headline text-[48px] leading-[0.9] [overflow-wrap:anywhere] md:text-[84px]">
          What you just went through.
        </h2>
        <p className="m-0 mt-4 max-w-[60ch] font-sans text-[21px] leading-[27px] opacity-90">
          The whole story in {CHAPTERS.length} lines{seen === CHAPTERS.length ? '.' : ', skipped parts marked.'}
        </p>

        <ol className="m-0 mt-8 list-none border-t border-canvas/30 p-0">
          {CHAPTERS.map((c, i) => {
            const p = progress[c.id] ?? 'unseen'
            const stamp = STAMP[p]
            return (
              <li key={c.id} className="grid grid-cols-[40px_minmax(0,1fr)] gap-x-4 gap-y-2 border-b border-canvas/30 py-4 md:grid-cols-[48px_minmax(0,220px)_minmax(0,1fr)_auto] md:items-baseline">
                <span className="font-mono text-[13px] opacity-70">{chapterNo(i)}</span>
                <span className="font-headline text-[24px] leading-none md:text-[28px]">{c.short}</span>
                <span className="col-start-2 font-sans text-[18px] leading-[24px] opacity-90 md:col-start-auto">
                  {c.takeaway}
                  {p === 'unseen' && (
                    <>
                      {' '}
                      <a href={`#${c.id}`} className="text-canvas decoration-accent">
                        Read it
                      </a>
                    </>
                  )}
                </span>
                <span className={`col-start-2 inline-flex items-center gap-1 justify-self-start px-2 py-0.5 font-mono text-[11px] tracking-[0.08em] uppercase md:col-start-auto md:justify-self-end ${stamp.tone}`}>
                  {p === 'finished' && <CheckIcon size={12} />}
                  {stamp.word}
                </span>
              </li>
            )
          })}
        </ol>

        <div className="mt-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <p className="m-0 max-w-[40ch] font-headline text-[30px] leading-[0.95] md:text-[40px]">Now see how it handles your questions.</p>
          <div className="flex flex-wrap gap-3">
            <a
              href="#run"
              className="inline-flex min-h-11 items-center gap-2 border border-canvas bg-canvas px-5 font-mono text-[12.5px] tracking-[0.08em] text-ink uppercase no-underline hover:bg-accent hover:text-ink"
            >
              Run it yourself
              <ArrowRightIcon size={15} />
            </a>
            <ButtonLink kind="inverse" href={repoUrl}>
              <GitHubIcon size={15} />
              Star on GitHub
            </ButtonLink>
          </div>
        </div>
      </div>
    </section>
  )
}
