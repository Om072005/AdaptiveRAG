import type { ReactNode } from 'react'

/** A page section set like a newspaper spread: a heavy rule with the section number and name, the
 * headline, and the lede in its own ruled column. */
export function Section({ id, no, eyebrow, title, lede, tone = 'plain', children }: {
  id: string
  no?: number
  eyebrow?: string
  title: string
  lede?: ReactNode
  tone?: 'plain' | 'sunken'
  children: ReactNode
}) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} data-tone={tone}>
      <div className="page-wrap pt-10 pb-20 md:pt-12 md:pb-28">
        <div className="flex items-baseline justify-between gap-4 border-t-[3px] border-double border-ink pt-2.5">
          <p className="text-eyebrow m-0">{eyebrow}</p>
          {no !== undefined && <p className="text-eyebrow m-0">No. {String(no).padStart(2, '0')}</p>}
        </div>
        <div className="mt-6 grid grid-cols-1 gap-6 md:mt-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] lg:gap-0">
          <h2 id={`${id}-h`} className="text-display m-0 max-w-none lg:pr-10">
            {title}
          </h2>
          {lede && (
            <p className="m-0 max-w-[44ch] self-end font-sans text-[21px] leading-[27px] text-text md:text-[23px] md:leading-[29px] lg:border-l lg:border-rule lg:pl-8">
              {lede}
            </p>
          )}
        </div>
        <div className="mt-12 md:mt-16">{children}</div>
      </div>
    </section>
  )
}
