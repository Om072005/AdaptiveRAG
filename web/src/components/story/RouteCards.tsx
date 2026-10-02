import type { ReactNode } from 'react'
import { BG } from '../../copy/routes'
import type { Route } from '../../types'
import { MergeIcon, NetworkIcon, RouteIcon, SearchIcon } from '../Icons'

const CARDS: { route: Route; icon: ReactNode; name: string; what: string; example: string }[] = [
  {
    route: 'vector',
    icon: <SearchIcon size={22} />,
    name: 'Vector search',
    what: 'Finds passages closest in meaning. Fast and cheap.',
    example: 'When was Dwell magazine launched?',
  },
  {
    route: 'graph',
    icon: <NetworkIcon size={22} />,
    name: 'Knowledge graph',
    what: 'Follows links between people, places and works. Chains facts together.',
    example: 'Nathan Bridger was a character played by which actor and amateur boxer?',
  },
  {
    route: 'hybrid',
    icon: <MergeIcon size={22} />,
    name: 'Hybrid',
    what: 'Runs both and re-ranks. Most thorough.',
    example: 'Who was born first, Yanka Dyagileva or Alexander Bashlachev?',
  },
]

/** The three ways to search, in plain words, then the router that chooses between them. */
export function RouteCards() {
  return (
    <div>
      <ul className="m-0 grid list-none grid-cols-1 gap-5 p-0 md:grid-cols-3">
        {CARDS.map((c) => (
          <li key={c.route} className="card card-hover flex flex-col p-6">
            <div className="flex items-center justify-between">
              <span className="inline-flex size-11 items-center justify-center rounded-[2px] border border-rule bg-sunken text-ink">{c.icon}</span>
              <span aria-hidden="true" className={`h-1.5 w-10 rounded-full ${BG[c.route]}`} />
            </div>
            <h3 className="text-title m-0 mt-5">{c.name}</h3>
            <p className="text-small m-0 mt-2">{c.what}</p>
            <p className="m-0 mt-auto pt-5">
              <span className="block rounded-[2px] bg-sunken px-3.5 py-2.5 text-[13.5px] leading-5 text-text">
                <span className="text-caption block">For example</span>
                {c.example}
              </span>
            </p>
          </li>
        ))}
      </ul>
      <div className="card mt-5 flex flex-col gap-5 border-accent/30 bg-accent-soft p-6 md:flex-row md:items-center md:p-8">
        <span className="inline-flex size-12 shrink-0 items-center justify-center rounded-[2px] bg-accent text-accent-ink">
          <RouteIcon size={24} />
        </span>
        <div>
          <h3 className="text-title m-0">The router picks one for every question.</h3>
          <p className="text-small m-0 mt-1.5 max-w-[72ch]">
            Lookups go to vector search, questions that join or compare facts go to hybrid, and the big model is
            used only where it is needed.
          </p>
        </div>
      </div>
    </div>
  )
}
