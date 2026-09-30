import { type ReactNode, useEffect, useState } from 'react'
import { CHAPTERS, type Progress } from './chapters'
import { JourneyContext } from './context'

const RANK: Record<Progress, number> = { unseen: 0, started: 1, finished: 2 }

/** Watches the page: a chapter is started when its section is in view, finished when the reader
 * reaches its closing line. Progress only moves forward for this visit. */
export function JourneyProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState('')
  const [progress, setProgress] = useState<Record<string, Progress>>({})

  useEffect(() => {
    const mark = (id: string, p: Progress) =>
      setProgress((prev) => (RANK[prev[id] ?? 'unseen'] >= RANK[p] ? prev : { ...prev, [id]: p }))

    const inView = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue
          setCurrent(e.target.id)
          if (e.target.id !== 'recap') mark(e.target.id, 'started')
        }
      },
      { rootMargin: '-40% 0px -55% 0px' },
    )
    const reachedEnd = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const id = (e.target as HTMLElement).dataset.chapterEnd
          if (e.isIntersecting && id) mark(id, 'finished')
        }
      },
      { threshold: 0.6 },
    )
    const top = new IntersectionObserver((entries) => entries[0]?.isIntersecting && setCurrent(''), { rootMargin: '0px 0px -60% 0px' })

    for (const c of CHAPTERS) {
      const section = document.getElementById(c.id)
      if (section) inView.observe(section)
      const end = document.querySelector(`[data-chapter-end="${c.id}"]`)
      if (end) reachedEnd.observe(end)
    }
    const recap = document.getElementById('recap')
    if (recap) inView.observe(recap)
    const hero = document.getElementById('front')
    if (hero) top.observe(hero)
    return () => {
      inView.disconnect()
      reachedEnd.disconnect()
      top.disconnect()
    }
  }, [])

  return <JourneyContext.Provider value={{ current, progress }}>{children}</JourneyContext.Provider>
}
