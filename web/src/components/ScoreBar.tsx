/** A number in 0..1 as a thin bar on a hairline track, with the number beside it. */
export function ScoreBar({ value, label }: { value: number; label: string }) {
  return (
    <span className="inline-flex items-center gap-3">
      <span className="tabular-nums">{value.toFixed(2)}</span>
      <svg viewBox="0 0 160 4" width="160" height="4" role="img" aria-label={`${label} ${value.toFixed(2)} of 1`}>
        <line x1="0" y1="2" x2="160" y2="2" className="stroke-rule" strokeWidth="1" />
        <line x1="0" y1="2" x2={160 * Math.max(0, Math.min(1, value))} y2="2" className="stroke-cream-300" strokeWidth="3" />
      </svg>
    </span>
  )
}
