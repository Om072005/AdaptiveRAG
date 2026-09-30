/** The mark: one point that forks into three routes, printed in ink. */
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true" className="shrink-0">
      <rect width="32" height="32" className="fill-ink" />
      <g fill="none" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" className="stroke-canvas">
        <path d="M8 16h5" />
        <path d="M13 16c3 0 4-6 8-6h3" />
        <path d="M13 16h11" />
        <path d="M13 16c3 0 4 6 8 6h3" />
      </g>
      <circle cx="8" cy="16" r="2.6" className="fill-accent" />
    </svg>
  )
}

/** The masthead name, in the headline face. */
export function Wordmark({ href = '#top', big = false }: { href?: string; big?: boolean }) {
  return (
    <a href={href} className="inline-flex items-center gap-2.5 text-ink no-underline hover:text-ink">
      <LogoMark size={big ? 30 : 24} />
      <span className={`font-headline leading-none tracking-[0.01em] ${big ? 'text-[34px]' : 'text-[22px] sm:text-[26px]'}`}>AdaptiveRAG</span>
    </a>
  )
}
