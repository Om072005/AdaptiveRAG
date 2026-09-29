import type { ReactNode } from 'react'

/** A full width rule, the heading block (h2 on columns 1 to 8, lede on 1 to 6), then the content. */
export function Section({ id, title, lede, children }: { id: string; title: string; lede?: ReactNode; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="border-t border-rule">
      <div className="page-wrap pt-20 pb-20 md:pt-28 md:pb-32 lg:pt-40">
        <div className="page-grid">
          <div className="col-span-4 md:col-span-8">
            <h2 id={`${id}-h`} className="text-display m-0">
              {title}
            </h2>
          </div>
          {lede && (
            <div className="col-span-4 md:col-span-8 lg:col-span-6">
              <p className="text-lede mt-6 mb-0">{lede}</p>
            </div>
          )}
        </div>
        <div className="mt-12 md:mt-16">{children}</div>
      </div>
    </section>
  )
}
