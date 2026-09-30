import { useEffect, useState } from 'react'
import { DASH, FILL, ROUTE_NAME, STROKE } from '../../copy/routes'
import { PauseIcon, PlayIcon } from '../Icons'
import type { Route } from '../../types'

// Three recorded router runs from the replay set (test split): what was asked, how the classifier
// read it, the route and model the router chose, and the answer it gave.
const EXAMPLES: { question: string; type: string; route: Route; model: string; answer: string; sources: string[] }[] = [
  {
    question: 'When was Dwell magazine launched?',
    type: 'Single hop',
    route: 'vector',
    model: 'Small model',
    answer: 'September 2000',
    sources: ['Dwell (magazine)'],
  },
  {
    question: 'Nathan Bridger was a character played by which actor and amateur boxer?',
    type: 'Multi hop',
    route: 'hybrid',
    model: 'Large model',
    answer: 'Roy Scheider',
    sources: ['Nathan Bridger', 'Roy Scheider'],
  },
  {
    question: 'Who was born first, Yanka Dyagileva or Alexander Bashlachev?',
    type: 'Comparison',
    route: 'hybrid',
    model: 'Large model',
    answer: 'Alexander Bashlachev',
    sources: ['Alexander Bashlachev', 'Yanka Dyagileva'],
  },
]

const LANES: { route: Route; y: number; label: string }[] = [
  { route: 'vector', y: 28, label: 'by meaning' },
  { route: 'graph', y: 84, label: 'by connections' },
  { route: 'hybrid', y: 140, label: 'both, merged' },
]
const CYCLE_MS = 4200

/** The router at a glance: a question comes in, one of three lanes lights up, a cited answer comes out. */
export function HeroDemo() {
  const [i, setI] = useState(0)
  // stopped by the reader's button, or at the start when they asked for reduced motion
  const [stopped, setStopped] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false)
  const [hover, setHover] = useState(false)
  const [focus, setFocus] = useState(false)
  const running = !stopped && !hover && !focus
  useEffect(() => {
    if (!running) return
    // a timeout per example, so picking one by hand restarts the clock
    const t = window.setTimeout(() => setI((v) => (v + 1) % EXAMPLES.length), CYCLE_MS)
    return () => window.clearTimeout(t)
  }, [running, i])
  const ex = EXAMPLES[i]

  return (
    <div
      className="card relative overflow-hidden p-0 shadow-lg"
      onPointerEnter={(e) => e.pointerType === 'mouse' && setHover(true)}
      onPointerLeave={() => setHover(false)}
      onFocus={() => setFocus(true)}
      onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setFocus(false)}
    >
      <div className="flex items-center justify-between border-b border-ink bg-sunken px-5 py-2.5">
        <span className="text-label text-ink">Live from the archive</span>
        <span className="text-label">Recorded runs</span>
      </div>

      <div className="p-5 sm:p-6">
        <p className="text-label m-0">Question</p>
        <p key={`q${i}`} className="fade-in m-0 mt-1 min-h-[52px] font-sans text-[22px] leading-[26px] text-ink">
          {ex.question}
        </p>
        <p className="text-label m-0 mt-3 flex flex-wrap items-center gap-2">
          Read as
          <span key={`t${i}`} className="fade-in bg-accent px-2 py-0.5 text-accent-ink">
            {ex.type}
          </span>
        </p>

        <svg viewBox="0 0 400 168" className="mt-5 block h-auto w-full" role="img" aria-label={`The router sent it to ${ROUTE_NAME[ex.route]} search`}>
          {LANES.map((l) => {
            const on = l.route === ex.route
            const d = `M 44 84 C 110 84, 110 ${l.y}, 176 ${l.y} L 290 ${l.y}`
            return (
              <g key={l.route}>
                <path d={d} fill="none" strokeWidth={on ? 2.5 : 1.5} strokeDasharray={on ? undefined : DASH[l.route]} className={`transition-all duration-300 ${on ? STROKE[l.route] : 'stroke-faint'}`} />
                {on && <path d={d} fill="none" strokeWidth="2.5" strokeLinecap="round" className="flow-dash stroke-surface" />}
                <circle cx="290" cy={l.y} r={on ? 7 : 5} className={`transition-all duration-300 ${on ? FILL[l.route] : 'fill-faint'}`} />
                {on && <circle cx="290" cy={l.y} r="7" className={`pulse-dot ${FILL[l.route]}`} />}
                <text x="306" y={l.y - 3} className={`font-display text-[17px] font-[760] uppercase [font-stretch:62.5%] ${on ? 'fill-ink' : 'fill-muted'}`}>
                  {ROUTE_NAME[l.route]}
                </text>
                <text x="306" y={l.y + 13} className="fill-muted font-sans text-[14px] italic">
                  {l.label}
                </text>
              </g>
            )
          })}
          <circle cx="30" cy="84" r="18" className="fill-ink" />
          <g fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="stroke-canvas">
            <path d="M21 84h5" />
            <path d="M26 84c3 0 4-6 8-6h3M26 84h11M26 84c3 0 4 6 8 6h3" />
          </g>
          <circle cx="21" cy="84" r="2.2" className="fill-canvas" />
        </svg>

        <div key={`a${i}`} className="fade-in mt-5 border-t border-ink pt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-label m-0">Answer</p>
            <span className="text-label">{ex.model}</span>
          </div>
          <p className="m-0 mt-2 font-headline text-[40px] leading-[0.95] text-ink">
            {ex.answer}
          </p>
          <p className="m-0 mt-2 flex flex-wrap gap-1.5">
            {ex.sources.map((s, n) => (
              <span key={s} className="border border-rule px-2 py-0.5 font-mono text-[11px] leading-5 tracking-[0.04em] text-muted uppercase">
                <span className="text-accent-text">{n + 1}</span> {s}
              </span>
            ))}
          </p>
        </div>

        <div className="mt-5 flex items-center justify-center gap-2" role="group" aria-label="Examples">
          <button
            type="button"
            onClick={() => setStopped(!stopped)}
            aria-label={stopped ? 'Play the examples' : 'Pause the examples'}
            className="mr-1 inline-flex size-7 cursor-pointer items-center justify-center border border-ink bg-transparent text-ink hover:bg-ink hover:text-canvas"
          >
            {stopped ? <PlayIcon size={13} /> : <PauseIcon size={13} />}
          </button>
          {EXAMPLES.map((e, n) => (
            <button
              key={e.question}
              type="button"
              aria-label={`Example ${n + 1}: ${e.question}`}
              aria-pressed={n === i}
              onClick={() => setI(n)}
              className="flex size-6 cursor-pointer items-center justify-center border-0 bg-transparent p-0"
            >
              <span className={`block h-1.5 rounded-full transition-all duration-300 ${n === i ? 'w-6 bg-ink' : 'w-1.5 bg-faint'}`} />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
