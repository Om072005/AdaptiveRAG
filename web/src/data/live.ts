// The local API (contract 6). Only used when VITE_LIVE_API_URL is set, which is never the case in
// the production build: the public page reads recorded runs only.
import type { Judgement, Mode, QueryResponse } from '../types'
import { type LiveDelta, type LiveEvent, type LiveStep, splitLines } from './liveSteps'

export const LIVE_API_URL = import.meta.env.VITE_LIVE_API_URL || ''
export const liveEnabled = LIVE_API_URL !== ''

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  if (!liveEnabled) throw new ApiError(0, 'live questions are off on this build')
  const res = await fetch(`${LIVE_API_URL}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data?.error?.message ?? `HTTP ${res.status}`)
  return data as T
}

export const askLive = (question: string, mode: Mode) => post<QueryResponse>('/api/query', { question, mode })

export const judgeLive = (traceId: string) => post<Judgement>('/api/judge', { trace_id: traceId })

/** Ask and follow the answer as it is made: onEvent hears every step and every streamed piece of
 * the model's reasoning and answer; resolves with the same body /api/query returns. An API
 * without the stream route (404) is asked the plain way. */
export async function askLiveStream(
  question: string,
  mode: Mode,
  onEvent: (e: LiveStep | LiveDelta) => void,
  signal?: AbortSignal,
): Promise<QueryResponse> {
  if (!liveEnabled) throw new ApiError(0, 'live questions are off on this build')
  const res = await fetch(`${LIVE_API_URL}/api/query/stream`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question, mode }),
    signal,
  })
  if (res.status === 404) return askLive(question, mode)
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => null)
    throw new ApiError(res.status, data?.error?.message ?? `HTTP ${res.status}`)
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      const split = splitLines(buffer + value)
      buffer = split.rest
      for (const line of split.lines) {
        const event = parseEvent(line)
        if (event.type === 'done') return event.response as QueryResponse
        if (event.type === 'error') throw new ApiError(503, event.message)
        onEvent(event)
      }
    }
  } finally {
    reader.cancel().catch(() => undefined) // closes the request, so the API stops the question too
  }
  throw new ApiError(0, 'the answer stream ended early; see the API terminal')
}

function parseEvent(line: string): LiveEvent {
  try {
    return JSON.parse(line) as LiveEvent
  } catch {
    throw new ApiError(0, 'the API sent a line this page cannot read; see the API terminal')
  }
}
