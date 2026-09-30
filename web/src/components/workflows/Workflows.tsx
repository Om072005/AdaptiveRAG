import { type KeyboardEvent, type ReactNode, useEffect, useRef, useState } from 'react'
import { Diagram } from '../../diagrams/Diagram'
import { Button } from '../Button'
import { DatabaseIcon, LayersIcon, LoopIcon, PauseIcon, PlayIcon, RouteIcon } from '../Icons'
import { type Flow, FLOWS, stepLit } from './flows'

const ICON: Record<string, ReactNode> = {
  ingestion: <LayersIcon size={18} />,
  router: <RouteIcon size={18} />,
  schema: <DatabaseIcon size={18} />,
  eval: <LoopIcon size={18} />,
}
const STEP_MS = 2600
const COLS: Record<number, string> = { 4: 'lg:grid-cols-4', 5: 'lg:grid-cols-5' }

/** Steps through a flow on a timer while playing; stops on the last step. */
function useWalkthrough(count: number) {
  const [step, setStep] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  useEffect(() => {
    if (!playing) return
    const t = window.setTimeout(() => {
      if (step !== null && step >= count - 1) setPlaying(false)
      else setStep(step === null ? 0 : step + 1)
    }, step === null ? 0 : STEP_MS)
    return () => window.clearTimeout(t)
  }, [playing, step, count])
  const play = () => {
    if (playing) return setPlaying(false)
    if (step !== null && step >= count - 1) setStep(null)
    setPlaying(true)
  }
  const pick = (i: number) => {
    setPlaying(false)
    setStep(step === i ? null : i)
  }
  return { step, playing, play, pick }
}

export function Workflows() {
  const [key, setKey] = useState(FLOWS[0].key)
  const flow = FLOWS.find((f) => f.key === key) ?? FLOWS[0]
  const tabs = useRef<(HTMLButtonElement | null)[]>([])

  const onTabKey = (e: KeyboardEvent, i: number) => {
    const last = FLOWS.length - 1
    const target: Record<string, number> = { ArrowRight: i === last ? 0 : i + 1, ArrowLeft: i === 0 ? last : i - 1, Home: 0, End: last }
    const next = target[e.key]
    if (next === undefined) return
    e.preventDefault()
    setKey(FLOWS[next].key)
    tabs.current[next]?.focus()
  }

  return (
    <div>
      <div role="tablist" aria-label="Workflows" className="flex gap-2 overflow-x-auto pb-1">
        {FLOWS.map((f, i) => (
          <button
            key={f.key}
            ref={(el) => {
              tabs.current[i] = el
            }}
            type="button"
            role="tab"
            id={`wf-tab-${f.key}`}
            aria-selected={f.key === key}
            aria-controls="wf-panel"
            tabIndex={f.key === key ? 0 : -1}
            onClick={() => setKey(f.key)}
            onKeyDown={(e) => onTabKey(e, i)}
            className="inline-flex min-h-11 shrink-0 cursor-pointer items-center gap-2 rounded-[2px] border border-rule bg-surface px-4 text-[14.5px] leading-6 font-[560] whitespace-nowrap text-muted transition-colors hover:text-ink aria-selected:border-transparent aria-selected:bg-ink aria-selected:text-canvas"
          >
            {ICON[f.key]}
            {f.title}
          </button>
        ))}
      </div>

      <div id="wf-panel" role="tabpanel" tabIndex={0} aria-labelledby={`wf-tab-${key}`} className="mt-8 rounded-[2px]">
        {/* keyed, so a new tab starts its walkthrough from the beginning */}
        <FlowPanel key={flow.key} flow={flow} />
      </div>
    </div>
  )
}

function FlowPanel({ flow }: { flow: Flow }) {
  const { step, playing, play, pick } = useWalkthrough(flow.steps.length)
  const lit = step === null ? null : stepLit(flow.steps[step])
  return (
    <div className="fade-in">
      <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <div className="max-w-[68ch]">
          <h3 className="text-title m-0">{flow.title}</h3>
          <p className="text-small m-0 mt-2">{flow.summary}</p>
        </div>
        <Button kind="primary" onClick={play} className="shrink-0">
          {playing ? <PauseIcon size={16} /> : <PlayIcon size={16} />}
          {playing ? 'Pause walkthrough' : 'Play walkthrough'}
        </Button>
      </div>

      <ol className={`m-0 mt-6 grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2 ${COLS[flow.steps.length] ?? 'lg:grid-cols-4'}`} aria-label={`${flow.title} steps`}>
        {flow.steps.map((s, i) => (
          <li key={s.title}>
            <button
              type="button"
              onClick={() => pick(i)}
              aria-pressed={step === i}
              className="group relative h-full w-full cursor-pointer overflow-hidden rounded-[2px] border border-rule bg-surface p-4 text-left transition-all duration-200 hover:border-faint aria-pressed:border-accent aria-pressed:bg-accent-soft"
            >
              <span className="flex items-center gap-2.5">
                <span className="inline-flex size-6 items-center justify-center rounded-full bg-sunken text-[12px] font-[650] text-muted group-aria-pressed:bg-accent group-aria-pressed:text-accent-ink">
                  {i + 1}
                </span>
                <span className="text-[14.5px] leading-5 font-[620] text-ink">{s.title}</span>
              </span>
              <span className="mt-2 block text-[13.5px] leading-5 text-text">{s.text}</span>
              {playing && step === i && (
                <span aria-hidden="true" className="absolute bottom-0 left-0 h-0.5 w-full origin-left animate-[grow_2600ms_linear] bg-accent" />
              )}
            </button>
          </li>
        ))}
      </ol>

      <div className="mt-6">
        <Diagram
          data={flow.data}
          lit={lit}
          caption={step === null ? 'Pick a step or play the walkthrough. Select any box for detail.' : `Step ${step + 1}: ${flow.steps[step].title}`}
        />
      </div>
    </div>
  )
}
