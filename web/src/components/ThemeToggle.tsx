import { useTheme } from '../theme/useTheme'
import { MoonIcon, SunIcon } from './Icons'

export function ThemeToggle() {
  const [theme, toggle] = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      className="inline-flex size-10 cursor-pointer items-center justify-center rounded-full border border-rule bg-surface text-text transition-colors duration-150 hover:border-faint hover:text-ink"
    >
      {theme === 'dark' ? <SunIcon size={18} /> : <MoonIcon size={18} />}
    </button>
  )
}
