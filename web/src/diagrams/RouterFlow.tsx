import type { QueryResponse } from '../types'
import { litPath, ROUTER } from './data/router'
import { Diagram } from './Diagram'

/** The router flowchart; given a recorded route decision, the path it took is drawn in white. */
export function RouterFlow({ route = null, flagged = null }: {
  route?: QueryResponse['route'] | null
  flagged?: boolean | null // lights the last branch, answer returned or flagged for review
}) {
  const lit = route ? litPath(route, flagged) : null
  return (
    <Diagram
      data={ROUTER}
      lit={lit}
      caption={lit ? 'The path this question took is drawn in white. Select a box for what it checks.' : undefined}
    />
  )
}
