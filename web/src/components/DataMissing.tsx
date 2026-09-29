export function DataMissing({ error }: { error?: string }) {
  return (
    <p className="text-small text-muted">
      {error ? `This data could not be loaded (${error}).` : 'These results are published after the final evaluation run.'}
    </p>
  )
}
