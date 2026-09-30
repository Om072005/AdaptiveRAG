import type { ReactNode } from 'react'

/** A page section: eyebrow, heading and lede, then the content. Alternate sections sit on the sunken tone. */
export function Section({ id, eyebrow, title, lede, tone = 'plain', children }: {
  id: string
  eyebrow?: string
  title: string
  lede?: ReactNode
  tone?: 'plain' | 'sunken'
  children: ReactNode
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-h`}
      className={tone === 'sunken' ? 'border-y border-rule bg-sunken' : ''}
    >
      <div className="page-wrap py-20 md:py-28">
        <div className="max-w-[760px]">
          {eyebrow && <p className="text-eyebrow m-0 mb-3">{eyebrow}</p>}
          <h2 id={`${id}-h`} className="text-display m-0">
            {title}
          </h2>
          {lede && <p className="text-lede mt-5 mb-0">{lede}</p>}
        </div>
        <div className="mt-12 md:mt-14">{children}</div>
      </div>
    </section>
  )
}
