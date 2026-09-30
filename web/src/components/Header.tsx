import { useEffect, useState } from 'react'
import { CloseIcon, GitHubIcon, MenuIcon } from './Icons'
import { Wordmark } from './Logo'
import { ThemeToggle } from './ThemeToggle'

const SECTIONS = [
  { id: 'how', label: 'How it works' },
  { id: 'follow', label: 'Demo' },
  { id: 'results', label: 'Results' },
  { id: 'workflows', label: 'Under the hood' },
  { id: 'run', label: 'Run it' },
  { id: 'team', label: 'Team' },
]

/** The section in view, so its anchor can show as current. */
function useCurrentSection(): string {
  const [current, setCurrent] = useState('')
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length) setCurrent(visible[0].target.id)
      },
      { rootMargin: '-40% 0px -55% 0px' },
    )
    for (const { id } of SECTIONS) {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    }
    return () => observer.disconnect()
  }, [])
  return current
}

/** Whether the page has scrolled past the top, to give the bar its hairline. */
function useScrolled(): boolean {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return scrolled
}

function Anchors({ current, onPick, stacked = false }: { current: string; onPick?: () => void; stacked?: boolean }) {
  return (
    <ul className={`m-0 flex list-none p-0 ${stacked ? 'flex-col gap-1' : 'items-center gap-1'}`}>
      {SECTIONS.map(({ id, label }) => (
        <li key={id}>
          <a
            href={`#${id}`}
            onClick={onPick}
            aria-current={current === id ? 'true' : undefined}
            className={`block rounded-full px-3 py-1.5 text-[14.5px] leading-6 font-[500] text-muted no-underline transition-colors hover:bg-sunken hover:text-ink aria-[current=true]:bg-accent-soft aria-[current=true]:text-accent-text ${stacked ? 'py-3 text-[16px]' : ''}`}
          >
            {label}
          </a>
        </li>
      ))}
    </ul>
  )
}

export function Header({ repoUrl }: { repoUrl: string }) {
  const current = useCurrentSection()
  const scrolled = useScrolled()
  const [open, setOpen] = useState(false)
  return (
    <header
      className={`sticky top-0 z-40 border-b bg-(--header-bg) backdrop-blur-md backdrop-saturate-150 transition-colors ${scrolled || open ? 'border-rule' : 'border-transparent'}`}
    >
      <div className="page-wrap flex h-16 items-center justify-between gap-6">
        <Wordmark />
        <nav aria-label="Sections" className="hidden min-[1000px]:block">
          <Anchors current={current} />
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <a
            href={repoUrl}
            className="hidden h-10 items-center gap-2 rounded-full border border-rule bg-surface px-4 text-[14.5px] font-[500] text-ink no-underline transition-colors hover:border-faint hover:text-ink sm:inline-flex"
          >
            <GitHubIcon size={17} />
            GitHub
          </a>
          <button
            type="button"
            className="inline-flex size-10 cursor-pointer items-center justify-center rounded-full border border-rule bg-surface text-ink min-[1000px]:hidden"
            aria-expanded={open}
            aria-controls="menu"
            aria-label="Menu"
            onClick={() => setOpen(!open)}
          >
            {open ? <CloseIcon size={18} /> : <MenuIcon size={18} />}
          </button>
        </div>
      </div>
      {open && (
        <nav id="menu" aria-label="Sections" className="page-wrap pb-4 min-[1000px]:hidden">
          <Anchors current={current} onPick={() => setOpen(false)} stacked />
          <a href={repoUrl} className="mt-2 flex items-center gap-2 px-3 py-3 text-[16px] font-[500] text-ink no-underline sm:hidden">
            <GitHubIcon size={17} />
            GitHub
          </a>
        </nav>
      )}
    </header>
  )
}
