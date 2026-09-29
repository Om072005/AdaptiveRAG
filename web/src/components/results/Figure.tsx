import type { ReactNode } from 'react'
import { RunId } from '../RunId'

/** A result with its caption: title, split and the run ids it came from. */
export function Figure({ title, split, runIds, children, note }: {
  title: string
  split?: string
  runIds: string[]
  children: ReactNode
  note?: ReactNode
}) {
  return (
    <figure className="m-0 mb-16 md:mb-24">
      <figcaption className="flex flex-wrap justify-between gap-x-6 gap-y-2 border-b border-rule pb-4">
        <span className="text-title">{title}</span>
        <span className="text-caption flex flex-wrap items-center gap-x-3">
          {split && <span>{split} split</span>}
          {runIds.map((id) => (
            <RunId key={id} id={id} />
          ))}
        </span>
      </figcaption>
      {/* focusable so a keyboard can scroll a wide table on a phone */}
      <div className="mt-4 overflow-x-auto" tabIndex={0} role="region" aria-label={title}>
        {children}
      </div>
      {note && <p className="text-caption m-0 mt-4 max-w-[68ch]">{note}</p>}
    </figure>
  )
}
