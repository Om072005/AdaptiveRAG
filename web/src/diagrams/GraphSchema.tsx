import { SCHEMA } from './data/schema'
import { Diagram } from './Diagram'

/** The README graph schema as the tables it became; select a box for what it does and where it lives. */
export function GraphSchema() {
  return <Diagram data={SCHEMA} />
}
