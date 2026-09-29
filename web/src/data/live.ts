// The local API (contract 6). Only used when VITE_LIVE_API_URL is set, which is never the case in
// the production build: the public page reads recorded runs only.
import type { Judgement, Mode, QueryResponse } from '../types'

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
