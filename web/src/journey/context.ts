import { createContext, useContext } from 'react'
import type { Progress } from './chapters'

export type JourneyState = {
  current: string // the chapter in view, '' above the first one
  progress: Record<string, Progress>
}

export const JourneyContext = createContext<JourneyState>({ current: '', progress: {} })

/** Where the reader is and which chapters they have started or finished. */
export const useJourney = () => useContext(JourneyContext)
