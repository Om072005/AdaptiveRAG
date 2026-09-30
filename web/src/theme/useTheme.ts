import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const KEY = 'theme'
const media = () => window.matchMedia?.('(prefers-color-scheme: dark)')

/** The theme in effect: the one the reader picked, else the system setting. */
function current(): Theme {
  const picked = document.documentElement.dataset.theme
  if (picked === 'light' || picked === 'dark') return picked
  return media()?.matches ? 'dark' : 'light'
}

/** The page theme and a toggle. The choice is remembered on this device when storage allows it. */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(current)

  useEffect(() => {
    const m = media()
    if (!m) return
    const follow = () => setTheme(current())
    m.addEventListener('change', follow)
    return () => m.removeEventListener('change', follow)
  }, [])

  const toggle = useCallback(() => {
    const next: Theme = current() === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem(KEY, next)
    } catch {
      // private windows and blocked storage: the choice lasts until the page closes
    }
    setTheme(next)
  }, [])

  return [theme, toggle]
}
