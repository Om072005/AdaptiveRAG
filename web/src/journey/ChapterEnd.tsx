import { ArrowRightIcon } from '../components/Icons'
import { CHAPTERS, chapterNo, nextChapter } from './chapters'

/** The close of a chapter: what the reader now knows, and the door to the next question. */
export function ChapterEnd({ id }: { id: string }) {
  const chapter = CHAPTERS.find((c) => c.id === id)
  if (!chapter) return null
  const next = nextChapter(id)
  const href = next ? `#${next.chapter.id}` : '#recap'
  return (
    <div data-chapter-end={id} className="mt-16 grid grid-cols-1 border-y border-ink md:mt-20 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="py-5 md:py-6 md:pr-8">
        <p className="text-label m-0">What you now know</p>
        <p className="m-0 mt-2 max-w-[54ch] font-sans text-[21px] leading-[27px] text-ink md:text-[23px] md:leading-[29px]">{chapter.takeaway}</p>
      </div>
      <a
        href={href}
        className="group flex items-center justify-between gap-4 border-t border-rule py-5 text-ink no-underline transition-colors hover:bg-ink hover:text-canvas md:border-t-0 md:border-l md:py-6 md:pl-8 md:pr-4"
      >
        <span>
          <span className="text-label block group-hover:text-canvas">
            {next ? `Next · chapter ${chapterNo(next.index)}` : 'The end · your recap'}
          </span>
          <span className="mt-1.5 block font-headline text-[26px] leading-none md:text-[30px]">{next ? next.chapter.short : 'What you went through'}</span>
          <span className="mt-1.5 block font-sans text-[17px] leading-[22px] italic opacity-80">
            {next ? next.chapter.question : 'Every chapter, what it told you, and what you skipped.'}
          </span>
        </span>
        <ArrowRightIcon size={22} className="shrink-0 transition-transform group-hover:translate-x-1" />
      </a>
    </div>
  )
}
