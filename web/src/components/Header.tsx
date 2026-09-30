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

function Anchors({ current, onPick, stacked = false }: { current: string; onPick?: () => void; stacked?: boolean }) {
  return (
    <ul className={`m-0 flex list-none p-0 ${stacked ? 'flex-col' : 'items-stretch justify-center'}`}>
      {SECTIONS.map(({ id, label }, i) => (
        <li key={id} className={stacked ? 'border-b border-rule' : i > 0 ? 'border-l border-rule' : ''}>
          <a
            href={`#${id}`}
            onClick={onPick}
            aria-current={current === id ? 'true' : undefined}
            className={`block font-mono text-[12px] leading-5 tracking-[0.08em] text-ink uppercase no-underline transition-colors hover:bg-ink hover:text-canvas aria-[current=true]:bg-ink aria-[current=true]:text-canvas ${stacked ? 'px-1 py-3.5' : 'px-5 py-2.5'}`}
          >
            {label}
          </a>
        </li>
      ))}
    </ul>
  )
}

/** A newspaper masthead: the issue line, the name in the middle, then the section nav between rules. */
export function Header({ repoUrl }: { repoUrl: string }) {
  const current = useCurrentSection()
  const [open, setOpen] = useState(false)
  return (
    <header className="sticky top-0 z-40 border-b border-ink bg-(--header-bg) backdrop-blur-sm">
      <div className="page-wrap flex h-16 items-center justify-between gap-3 md:grid md:grid-cols-[1fr_auto_1fr] md:gap-4">
        <p className="m-0 hidden font-sans text-[17px] leading-6 text-ink md:block">Vol. 1 · Open source · HotpotQA</p>
        <div className="col-start-1 justify-self-start md:col-start-2 md:justify-self-center">
          <Wordmark />
        </div>
        <div className="col-start-3 flex items-center justify-self-end gap-2">
          <ThemeToggle />
          <a
            href={repoUrl}
            className="hidden h-10 items-center gap-2 border border-ink px-3.5 font-mono text-[12px] tracking-[0.08em] text-ink uppercase no-underline transition-colors hover:bg-ink hover:text-canvas sm:inline-flex"
          >
            <GitHubIcon size={16} />
            GitHub
          </a>
          <button
            type="button"
            className="inline-flex size-10 cursor-pointer items-center justify-center border border-ink bg-transparent text-ink min-[1000px]:hidden"
            aria-expanded={open}
            aria-controls="menu"
            aria-label="Menu"
            onClick={() => setOpen(!open)}
          >
            {open ? <CloseIcon size={18} /> : <MenuIcon size={18} />}
          </button>
        </div>
      </div>
      <nav aria-label="Sections" className="hidden border-t border-rule min-[1000px]:block">
        <div className="page-wrap">
          <Anchors current={current} />
        </div>
      </nav>
      {open && (
        <nav id="menu" aria-label="Sections" className="page-wrap border-t border-rule pb-4 min-[1000px]:hidden">
          <Anchors current={current} onPick={() => setOpen(false)} stacked />
          <a href={repoUrl} className="mt-2 flex items-center gap-2 px-1 py-3 font-mono text-[12px] tracking-[0.08em] text-ink uppercase no-underline sm:hidden">
            <GitHubIcon size={16} />
            GitHub
          </a>
        </nav>
      )}
    </header>
  )
}
