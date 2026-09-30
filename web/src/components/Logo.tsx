/** The mark: one point that forks into three routes, on the brand square. */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true" className="shrink-0">
      <rect width="32" height="32" rx="8" className="fill-accent" />
      <g fill="none" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" className="stroke-accent-ink">
        <path d="M8 16h5" />
        <path d="M13 16c3 0 4-6 8-6h3" />
        <path d="M13 16h11" />
        <path d="M13 16c3 0 4 6 8 6h3" />
      </g>
      <circle cx="8" cy="16" r="2.6" className="fill-accent-ink" />
    </svg>
  )
}

export function Wordmark({ href = '#top' }: { href?: string }) {
  return (
    <a href={href} className="inline-flex items-center gap-2.5 text-[18px] leading-7 font-[650] tracking-[-0.02em] text-ink no-underline hover:text-ink">
      <LogoMark />
      AdaptiveRAG
    </a>
  )
}
