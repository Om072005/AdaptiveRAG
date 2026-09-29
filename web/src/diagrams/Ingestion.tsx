import { INGESTION } from './data/ingestion'
import { Diagram } from './Diagram'

/** The README ingestion pipeline; select a box for what it does and where it lives. */
export function Ingestion() {
  return <Diagram data={INGESTION} />
}
