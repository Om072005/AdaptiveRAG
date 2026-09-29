import { EVAL_LOOP } from './data/evalLoop'
import { Diagram } from './Diagram'

/** The README evaluation feedback loop; select a box for what it does and where it lives. */
export function EvalLoop() {
  return <Diagram data={EVAL_LOOP} />
}
