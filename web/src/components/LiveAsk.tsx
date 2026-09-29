import { type FormEvent, useState } from 'react'
import { askLive } from '../data/live'
import { liveReplay } from '../data/replay'
import type { Mode, Replay } from '../types'
import { Button } from './Button'

type Props = { onAnswer: (replay: Replay) => void }

/** Local only: ask the running API a question; the answer opens in the replay panel. */
export function LiveAsk({ onAnswer }: Props) {
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<Mode>('auto')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      onAnswer(liveReplay(await askLive(question.trim(), mode), mode))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="mb-10 max-w-[68ch]">
      <label htmlFor="live-q" className="text-title block">
        Ask your own question
      </label>
      <p className="text-caption m-0 mt-1">Answered live by the API running on this machine.</p>
      <textarea
        id="live-q"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        minLength={3}
        maxLength={300}
        rows={2}
        required
        className="mt-4 block w-full resize-y rounded-[6px] border border-rule bg-black p-3 text-[15px] leading-6 text-text"
      />
      <div className="mt-3 flex flex-wrap items-center gap-4">
        <label className="text-small flex items-center gap-2">
          Route
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}
            className="min-h-11 rounded-[6px] border border-rule bg-black px-2 text-[15px] text-text"
          >
            <option value="auto">Let the router choose</option>
            <option value="vector">Vector</option>
            <option value="graph">Graph</option>
            <option value="hybrid">Hybrid</option>
          </select>
        </label>
        <Button type="submit" kind="primary" disabled={busy || question.trim().length < 3}>
          {busy ? 'Answering' : 'Ask'}
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-small m-0 mt-3 text-muted">
          {error}
        </p>
      )}
    </form>
  )
}
