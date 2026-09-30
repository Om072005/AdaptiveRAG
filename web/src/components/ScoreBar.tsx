/** A number in 0..1 as a bar on a track, with the number beside it. */
export function ScoreBar({ value, label }: { value: number; label: string }) {
  const v = Math.max(0, Math.min(1, value))
  return (
    <span className="inline-flex items-center gap-3">
      <span className="w-9 font-[600] text-ink tabular-nums">{value.toFixed(2)}</span>
      <svg viewBox="0 0 140 8" width="140" height="8" role="img" aria-label={`${label} ${value.toFixed(2)} of 1`}>
        <rect x="0" y="0" width="140" height="8" rx="4" className="fill-sunken" />
        <rect x="0" y="0" width={Math.max(8, 140 * v)} height="8" rx="4" className="fill-accent" />
      </svg>
    </span>
  )
}
