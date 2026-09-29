import { ARCHITECTURE } from './data/architecture'
import { Diagram } from './Diagram'

/** The README architecture: select a box for what it does, where it lives and whether it is built. */
export function Architecture() {
  return <Diagram data={ARCHITECTURE} detailSide />
}
