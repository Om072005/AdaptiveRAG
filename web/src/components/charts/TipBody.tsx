/** Tooltip body: a title line and label, value rows. */
export function TipBody({ title, rows }: { title: string; rows: [string, string][] }) {
  return (
    <>
      <span className="block font-[620] text-ink">{title}</span>
      {rows.map(([k, v]) => (
        <span key={k} className="flex justify-between gap-4">
          <span className="text-muted">{k}</span>
          <span className="tabular-nums">{v}</span>
        </span>
      ))}
    </>
  )
}
