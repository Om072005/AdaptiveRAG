import type { QueryResponse } from '../types'
import { litPath, ROUTER } from './data/router'
import { Diagram } from './Diagram'

/** The router flowchart; given a recorded route decision, the path it took is highlighted and flows. */
export function RouterFlow({ route = null, flagged = null, framed = true }: {
  route?: QueryResponse['route'] | null
  flagged?: boolean | null // lights the last branch, answer returned or flagged for review
  framed?: boolean
}) {
  const lit = route ? litPath(route, flagged) : null
  return (
    <Diagram
      data={ROUTER}
      lit={lit}
      framed={framed}
      legend={false}
      caption={lit ? 'The path this question took is highlighted. Select a box for what it checks.' : undefined}
    />
  )
}
