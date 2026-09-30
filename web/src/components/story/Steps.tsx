import type { ReactNode } from 'react'
import { BrainTagIcon, QuoteIcon, RouteIcon, SearchIcon, ShieldCheckIcon } from '../Icons'

const STEPS: { icon: ReactNode; title: string; text: string }[] = [
  { icon: <BrainTagIcon size={20} />, title: 'Understand', text: 'A classifier labels the question: a simple lookup, a chain of facts, or a comparison.' },
  { icon: <RouteIcon size={20} />, title: 'Choose', text: 'The router picks the cheapest route that can answer it, within a per question budget.' },
  { icon: <SearchIcon size={20} />, title: 'Search', text: 'Vector search, the knowledge graph or both bring back the evidence, ranked.' },
  { icon: <QuoteIcon size={20} />, title: 'Answer', text: 'A small or large open model writes a short answer, citing a numbered source for every claim.' },
  { icon: <ShieldCheckIcon size={20} />, title: 'Check', text: 'A judge from a different model family scores it. Low scores wait for a person to review.' },
]

/** The pipeline in five plain steps, joined by a line on wide screens. */
export function Steps() {
  return (
    <ol className="relative m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 lg:grid-cols-5 lg:gap-5">
      <span aria-hidden="true" className="absolute top-[34px] right-[10%] left-[10%] hidden h-px bg-rule lg:block" />
      {STEPS.map((s, i) => (
        <li key={s.title} className="card card-hover relative p-5">
          <div className="flex items-center gap-3">
            <span className="inline-flex size-9 items-center justify-center rounded-[2px] bg-accent-soft text-accent-text">{s.icon}</span>
            <span className="text-caption font-[600]">Step {i + 1}</span>
          </div>
          <h3 className="text-title m-0 mt-4">{s.title}</h3>
          <p className="text-small m-0 mt-1.5 text-text">{s.text}</p>
        </li>
      ))}
    </ol>
  )
}
