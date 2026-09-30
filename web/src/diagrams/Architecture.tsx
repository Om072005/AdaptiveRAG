import { ARCHITECTURE } from './data/architecture'
import { Diagram } from './Diagram'

/** The README architecture: select a box for what it does, where it lives and whether it is built. */
export function Architecture() {
  return <Diagram data={ARCHITECTURE} caption="Select a box to read what it does, where it lives in the code and whether it is built." />
}
