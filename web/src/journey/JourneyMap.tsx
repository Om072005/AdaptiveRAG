import { ButtonLink } from '../components/Button'
import { ArrowRightIcon, CheckIcon } from '../components/Icons'
import { CHAPTERS, chapterNo, type Progress, TOTAL_MINUTES } from './chapters'
import { useJourney } from './context'

const STOP: Record<Progress, string> = {
  unseen: 'border-ink bg-canvas text-ink',
  started: 'border-ink bg-accent text-accent-ink',
  finished: 'border-ink bg-ink text-canvas',
}

/** The route through the page before the reader sets off: every chapter as a stop on one line and how
 * long it takes. Stops fill in as the reader goes. */
export function JourneyMap() {
  const { progress, current } = useJourney()
  return (
    <section id="route" aria-labelledby="route-h" className="page-wrap pb-16 md:pb-20">
      <div className="border-y-[3px] border-double border-ink py-6 md:py-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-eyebrow m-0">In this issue</p>
            <h2 id="route-h" className="m-0 mt-2 font-headline text-[40px] leading-[0.92] text-ink md:text-[56px]">
              Your route through this page
            </h2>
            <p className="m-0 mt-3 max-w-[56ch] font-sans text-[20px] leading-[26px] text-text">
              {CHAPTERS.length} short chapters, about {TOTAL_MINUTES} minutes. Jump to any stop.
            </p>
          </div>
          <ButtonLink kind="primary" href={`#${CHAPTERS[0].id}`} className="shrink-0 self-start md:self-end">
            Start the journey
            <ArrowRightIcon size={15} />
          </ButtonLink>
        </div>

        <ol className="relative m-0 mt-8 grid list-none grid-cols-1 gap-0 p-0 md:mt-10 md:grid-cols-4 lg:grid-cols-7">
          {/* the line the stops sit on: down the left on a phone, across on a wide screen */}
          <span aria-hidden="true" className="absolute top-4 bottom-4 left-[15px] w-px bg-ink md:hidden" />
          <span aria-hidden="true" className="absolute top-[15px] right-0 left-0 hidden h-px bg-ink lg:block" />
          {CHAPTERS.map((c, i) => {
            const p = progress[c.id] ?? 'unseen'
            const here = current === c.id
            return (
              <li key={c.id} className="relative">
                <a
                  href={`#${c.id}`}
                  aria-current={here ? 'location' : undefined}
                  className="group grid grid-cols-[32px_minmax(0,1fr)] gap-3 py-3 text-ink no-underline md:block md:py-0 md:pr-4 md:pb-6"
                >
                  <span
                    className={`relative z-[1] inline-flex size-8 items-center justify-center border font-mono text-[12px] transition-colors group-hover:bg-ink group-hover:text-canvas ${STOP[p]} ${here ? 'outline-2 outline-offset-2 outline-accent' : ''}`}
                  >
                    {p === 'finished' ? <CheckIcon size={14} /> : chapterNo(i)}
                  </span>
                  <span className="block md:mt-3">
                    <span className="block font-headline text-[22px] leading-none group-hover:text-accent-text">{c.short}</span>
                    <span className="text-label mt-1.5 block">
                      {c.minutes} min{p === 'finished' ? ' · read' : p === 'started' ? ' · started' : ''}
                    </span>
                  </span>
                </a>
              </li>
            )
          })}
        </ol>
      </div>
    </section>
  )
}
