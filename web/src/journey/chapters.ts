// The page as a journey: eight short chapters in the order a visitor wants them. Section ids are the
// page anchors.

export type Chapter = {
  id: string
  short: string // the name in the nav, the route map and the recap
  takeaway: string // what they know when they leave it
  minutes: number // a rough reading time
}

export const CHAPTERS: Chapter[] = [
  {
    id: 'idea',
    short: 'The idea',
    takeaway: 'Three ways to search (vector, graph, hybrid), and a router that picks one per question.',
    minutes: 1,
  },
  {
    id: 'how',
    short: 'How it works',
    takeaway: 'Classify, route, search, answer with sources, then a separate judge checks it.',
    minutes: 1,
  },
  {
    id: 'follow',
    short: 'Watch it',
    takeaway: 'Recorded questions step by step, failures included.',
    minutes: 2,
  },
  {
    id: 'results',
    short: 'The proof',
    takeaway: 'Letting the router choose beat every single method, at a measured cost.',
    minutes: 2,
  },
  {
    id: 'failures',
    short: 'Lessons',
    takeaway: 'Real incidents: how each was found and what was fixed.',
    minutes: 1,
  },
  {
    id: 'workflows',
    short: 'Under the hood',
    takeaway: 'Ingestion, routing, graph storage and judging, step by step.',
    minutes: 2,
  },
  {
    id: 'run',
    short: 'Try it',
    takeaway: 'A few commands run it all on your machine, no API keys.',
    minutes: 1,
  },
  {
    id: 'team',
    short: 'The team',
    takeaway: 'Four people, thirteen days.',
    minutes: 1,
  },
]

export type Progress = 'unseen' | 'started' | 'finished'

export const TOTAL_MINUTES = CHAPTERS.reduce((sum, c) => sum + c.minutes, 0)

export const chapterNo = (i: number) => String(i + 1).padStart(2, '0')

/** The chapter after this one, or null at the end. */
export function nextChapter(id: string): { chapter: Chapter; index: number } | null {
  const i = CHAPTERS.findIndex((c) => c.id === id)
  return i >= 0 && i < CHAPTERS.length - 1 ? { chapter: CHAPTERS[i + 1], index: i + 1 } : null
}

/** How much of the journey the reader has covered, for the recap. */
export function summarize(progress: Record<string, Progress>): { finished: number; started: number; unseen: number } {
  const out = { finished: 0, started: 0, unseen: 0 }
  for (const c of CHAPTERS) out[progress[c.id] ?? 'unseen']++
  return out
}
