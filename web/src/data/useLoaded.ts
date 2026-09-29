import { useEffect, useState } from 'react'
import type { Loaded } from './load'

export type LoadState<T> = Loaded<T> | { status: 'loading' }

/** Runs a module level loader for an argument and returns its state; loading until it answers. */
export function useLoaded<T>(load: (arg: string) => Promise<Loaded<T>>, arg = ''): LoadState<T> {
  const [result, setResult] = useState<{ arg: string; state: Loaded<T> } | null>(null)
  useEffect(() => {
    let live = true
    load(arg).then((state) => {
      if (live) setResult({ arg, state })
    })
    return () => {
      live = false
    }
  }, [load, arg])
  return result?.arg === arg ? result.state : { status: 'loading' }
}
