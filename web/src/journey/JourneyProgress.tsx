import { CHAPTERS, chapterNo } from './chapters'
import { useJourney } from './context'

const SEGMENT = { unseen: 'bg-transparent', started: 'bg-accent', finished: 'bg-ink' } as const

/** Where the reader is: the chapter in view by name, and one segment per chapter along the bottom of
 * the masthead, filled as chapters are started and finished. */
export function JourneyWhere() {
  const { current } = useJourney()
  const i = CHAPTERS.findIndex((c) => c.id === current)
  if (current === 'recap') {
    return (
      <p className="m-0 font-sans text-[17px] leading-6 text-ink">
        <span className="text-label mr-2 text-ink">The end</span>
        Your recap
      </p>
    )
  }
  if (i < 0) return <p className="m-0 font-sans text-[17px] leading-6 text-ink">Vol. 1 · Open source · HotpotQA</p>
  return (
    <p className="m-0 font-sans text-[17px] leading-6 text-ink" aria-live="polite">
      <span className="text-label mr-2 text-ink">
        Chapter {chapterNo(i)} / {chapterNo(CHAPTERS.length - 1)}
      </span>
      {CHAPTERS[i].short}
    </p>
  )
}

export function JourneyBar() {
  const { current, progress } = useJourney()
  return (
    <ol aria-label="Journey progress" className="m-0 grid list-none gap-px p-0" style={{ gridTemplateColumns: `repeat(${CHAPTERS.length}, minmax(0, 1fr))` }}>
      {CHAPTERS.map((c) => {
        const p = progress[c.id] ?? 'unseen'
        return (
          <li key={c.id} className="h-1 bg-rule">
            <span className={`block h-full transition-colors duration-300 ${current === c.id ? 'bg-accent' : SEGMENT[p]}`} />
            <span className="sr-only">
              {c.short}: {p === 'finished' ? 'read' : p === 'started' ? 'started' : 'not yet'}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
