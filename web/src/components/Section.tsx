import type { ReactNode } from 'react'
import { ChapterEnd } from '../journey/ChapterEnd'
import { CHAPTERS, chapterNo } from '../journey/chapters'

/** A chapter of the page, set like a newspaper spread: a heavy rule with its number and reading time,
 * the question it answers, the headline, the lede in its own ruled column, the content, and a close
 * with what the reader now knows and the way to the next chapter. */
export function Section({ id, title, lede, children }: { id: string; title: string; lede?: ReactNode; children: ReactNode }) {
  const i = CHAPTERS.findIndex((c) => c.id === id)
  const chapter = CHAPTERS[i]
  return (
    <section id={id} aria-labelledby={`${id}-h`}>
      <div className="page-wrap pt-10 pb-20 md:pt-12 md:pb-24">
        <div className="flex items-baseline justify-between gap-4 border-t-[3px] border-double border-ink pt-2.5">
          <p className="text-eyebrow m-0">{chapter ? `Chapter ${chapterNo(i)} · ${chapter.short}` : title}</p>
          {chapter && <p className="text-eyebrow m-0">About {chapter.minutes} min</p>}
        </div>
        {chapter && <p className="m-0 mt-6 font-sans text-[22px] leading-7 text-accent-text italic md:mt-8 md:text-[26px] md:leading-8">{chapter.question}</p>}
        <div className="mt-2 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] lg:gap-0">
          <h2 id={`${id}-h`} className="text-display m-0 max-w-none lg:pr-10">
            {title}
          </h2>
          {lede && (
            <p className="m-0 max-w-[44ch] self-end font-sans text-[21px] leading-[27px] text-text md:text-[23px] md:leading-[29px] lg:border-l lg:border-rule lg:pl-8">
              {lede}
            </p>
          )}
        </div>
        <div className="mt-12 md:mt-16">{children}</div>
        {chapter && <ChapterEnd id={id} />}
      </div>
    </section>
  )
}
