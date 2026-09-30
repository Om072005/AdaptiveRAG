// The page as a journey: eight chapters, each answering one question a visitor has, in the order
// they have them. Section ids are the page anchors.

export type Chapter = {
  id: string
  short: string // the name in the nav, the route map and the recap
  question: string // what the reader wants to know when they arrive here
  takeaway: string // what they know when they leave it
  minutes: number // a rough reading time
}

export const CHAPTERS: Chapter[] = [
  {
    id: 'idea',
    short: 'The idea',
    question: 'Why not just use one search method?',
    takeaway: 'Questions differ, so AdaptiveRAG has three ways to find evidence (vector, graph, hybrid) and picks one per question.',
    minutes: 1,
  },
  {
    id: 'how',
    short: 'How it works',
    question: 'What happens to a question?',
    takeaway: 'Each question is classified, routed, searched, answered with numbered sources, then checked by a separate judge.',
    minutes: 2,
  },
  {
    id: 'follow',
    short: 'Watch it',
    question: 'What does that look like on a real question?',
    takeaway: 'You stepped through recorded questions, from the router’s choice to the cited answer and its cost, including ones that went wrong.',
    minutes: 3,
  },
  {
    id: 'results',
    short: 'The proof',
    question: 'Does it actually work better?',
    takeaway: 'On held out questions, letting the router choose beat every single method, and the charts show what that costs.',
    minutes: 3,
  },
  {
    id: 'failures',
    short: 'Lessons',
    question: 'What went wrong along the way?',
    takeaway: 'Real incidents, how each one was found, and what was fixed or is still open.',
    minutes: 2,
  },
  {
    id: 'workflows',
    short: 'Under the hood',
    question: 'How is each piece built?',
    takeaway: 'How documents are ingested, how the router decides, how the graph is stored and how answers are judged.',
    minutes: 2,
  },
  {
    id: 'run',
    short: 'Try it',
    question: 'Can I run it myself?',
    takeaway: 'Eight commands run the whole system on your own machine with free, open tools and no API keys.',
    minutes: 1,
  },
  {
    id: 'team',
    short: 'The team',
    question: 'Who made it?',
    takeaway: 'Four people built it in thirteen days; issues go to the repository.',
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
