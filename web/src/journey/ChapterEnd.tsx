import { ArrowRightIcon } from '../components/Icons'
import { CHAPTERS, chapterNo, nextChapter } from './chapters'

/** The close of a chapter: one ruled bar that leads to the next chapter. What each chapter told the
 * reader is gathered once, in the recap at the end. */
export function ChapterEnd({ id }: { id: string }) {
  if (!CHAPTERS.some((c) => c.id === id)) return null
  const next = nextChapter(id)
  return (
    <div data-chapter-end={id} className="mt-14 md:mt-16">
      <a
        href={next ? `#${next.chapter.id}` : '#recap'}
        className="group flex items-center justify-between gap-4 border-y border-ink px-1 py-4 text-ink no-underline transition-colors hover:bg-ink hover:text-canvas md:px-4"
      >
        <span className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <span className="text-label group-hover:text-canvas">{next ? `Next · ${chapterNo(next.index)}` : 'The end'}</span>
          <span className="font-headline text-[24px] leading-none md:text-[28px]">{next ? next.chapter.short : 'Your recap'}</span>
        </span>
        <ArrowRightIcon size={22} className="shrink-0 transition-transform group-hover:translate-x-1" />
      </a>
    </div>
  )
}
