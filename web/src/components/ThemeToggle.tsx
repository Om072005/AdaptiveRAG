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
      className="inline-flex size-10 cursor-pointer items-center justify-center border border-ink bg-transparent text-ink transition-colors duration-150 hover:bg-ink hover:text-canvas"
    >
      {theme === 'dark' ? <SunIcon size={17} /> : <MoonIcon size={17} />}
    </button>
  )
}
