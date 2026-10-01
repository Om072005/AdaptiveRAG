import { type FormEvent, useEffect, useRef, useState } from 'react'
import { askLiveStream } from '../data/live'
import type { LiveDelta, LiveStep } from '../data/liveSteps'
import { liveReplay } from '../data/replay'
import type { Mode, Replay } from '../types'
import { Button } from './Button'
import { LiveSteps } from './LiveSteps'

type Props = { onAnswer: (replay: Replay) => void }

/** Local only: ask the running API a question and watch it work, step by step; the finished
 * answer opens in the replay panel. */
export function LiveAsk({ onAnswer }: Props) {
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<Mode>('auto')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [steps, setSteps] = useState<LiveStep[]>([])
  const [thinking, setThinking] = useState('')
  const [answer, setAnswer] = useState('')
  const running = useRef<AbortController | null>(null)
  useEffect(() => () => running.current?.abort(), []) // leaving the page stops the question

  const hear = (e: LiveStep | LiveDelta) => {
    if (e.type === 'step') setSteps((s) => [...s, e])
    else if (e.kind === 'thinking') setThinking((t) => t + e.text)
    else setAnswer((a) => a + e.text)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    setSteps([])
    setThinking('')
    setAnswer('')
    running.current?.abort()
    const controller = new AbortController()
    running.current = controller
    try {
      onAnswer(liveReplay(await askLiveStream(question.trim(), mode, hear, controller.signal), mode))
    } catch (err) {
      if (controller.signal.aborted) return
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
    <form onSubmit={submit} className="card mb-8 p-5 md:p-6">
      <label htmlFor="live-q" className="text-title block">
        Ask your own question
      </label>
      <p className="text-caption m-0 mt-1">Answered live by the API running on this machine. Each step shows up the moment it ends.</p>
      <textarea
        id="live-q"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        minLength={3}
        maxLength={300}
        rows={2}
        required
        className="mt-4 block w-full resize-y rounded-[2px] border border-rule bg-canvas p-3 text-[15px] leading-6 text-text"
      />
      <div className="mt-3 flex flex-wrap items-center gap-4">
        <label className="text-small flex items-center gap-2">
          Route
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}
            className="min-h-11 rounded-[2px] border border-rule bg-canvas px-2 text-[15px] text-text"
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
    {(busy || steps.length > 0) && <LiveSteps steps={steps} thinking={thinking} answer={answer} busy={busy} />}
    </>
  )
}
