// Static page data from /data (contract 6b). Samples are used only when VITE_ALLOW_SAMPLE=1,
// which is set locally and on previews; the production build strips them.
import type { Replay, ReplayIndex, Results, SiteContent } from '../types'

export const ALLOW_SAMPLE = import.meta.env.VITE_ALLOW_SAMPLE === '1'

export type Loaded<T> =
  | { status: 'ok'; data: T; sample: boolean }
  | { status: 'missing' }
  | { status: 'error'; message: string }

async function fetchJson(path: string): Promise<unknown | null> {
  const res = await fetch(path)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`)
  // a dev server answers unknown paths with index.html, which is not data
  if (!(res.headers.get('content-type') ?? '').includes('json')) return null
  return res.json()
}

export async function loadData<T>(name: string, isValid: (d: unknown) => boolean): Promise<Loaded<T>> {
  try {
    let data = await fetchJson(`/data/${name}.json`)
    if (data === null && ALLOW_SAMPLE) data = await fetchJson(`/data/${name}.sample.json`)
    if (data === null) return { status: 'missing' }
    if (!isValid(data)) return { status: 'error', message: `/data/${name} does not match the contract` }
    const sample = (data as { sample?: unknown }).sample === true
    if (sample && !ALLOW_SAMPLE) return { status: 'missing' }
    return { status: 'ok', data: data as T, sample }
  } catch (e) {
    return { status: 'error', message: e instanceof Error ? e.message : String(e) }
  }
}

const isObject = (d: unknown): d is Record<string, unknown> => typeof d === 'object' && d !== null
const has = (d: unknown, keys: string[]) => isObject(d) && keys.every((k) => k in d)

export const loadResults = (): Promise<Loaded<Results>> =>
  loadData<Results>('results', (d) => has(d, ['sample', 'generated_at', 'git_sha', 'runs', 'tables']))

export const loadReplayIndex = (): Promise<Loaded<ReplayIndex>> =>
  loadData<ReplayIndex>('replays/index', (d) => has(d, ['sample', 'items']) && Array.isArray((d as ReplayIndex).items))

export const loadReplay = (questionId: string) =>
  loadData<Replay>(`replays/${questionId}`, (d) => has(d, ['sample', 'question_id', 'question', 'runs']))

export const loadSite = (): Promise<Loaded<SiteContent>> =>
  loadData<SiteContent>('site', (d) => has(d, ['repo_url', 'contact_email', 'license', 'members']))
