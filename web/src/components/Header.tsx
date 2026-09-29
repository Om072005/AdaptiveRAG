import { useEffect, useState } from 'react'

const SECTIONS = [
  { id: 'how', label: 'How it works' },
  { id: 'follow', label: 'Follow a question' },
  { id: 'workflows', label: 'Workflows' },
  { id: 'results', label: 'Results' },
  { id: 'run', label: 'Run it' },
  { id: 'team', label: 'Team' },
]

/** The section in view, so its anchor can show in white. */
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

function Anchors({ current, onPick }: { current: string; onPick?: () => void }) {
  return (
    <ul className="m-0 flex list-none flex-col gap-4 p-0 min-[900px]:flex-row min-[900px]:gap-5 min-[1100px]:gap-7">
      {SECTIONS.map(({ id, label }) => (
        <li key={id}>
          <a
            href={`#${id}`}
            onClick={onPick}
            aria-current={current === id ? 'true' : undefined}
            className="text-[15px] leading-6 text-muted no-underline hover:text-white aria-[current=true]:text-white"
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
  const [open, setOpen] = useState(false)
  return (
    <header className="page-wrap py-6">
      <div className="flex items-center justify-between gap-8">
        <a href="#top" className="font-serif text-[22px] leading-7 text-white no-underline">
          AdaptiveRAG
        </a>
        <nav aria-label="Sections" className="hidden min-[900px]:block">
          <Anchors current={current} />
        </nav>
        <div className="flex items-center gap-6">
          <button
            type="button"
            className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] text-white underline underline-offset-4 min-[900px]:hidden"
            aria-expanded={open}
            aria-controls="menu"
            onClick={() => setOpen(!open)}
          >
            Menu
          </button>
          <a className="text-[15px]" href={repoUrl}>
            GitHub
          </a>
        </div>
      </div>
      {open && (
        <nav id="menu" aria-label="Sections" className="mt-6 min-[900px]:hidden">
          <Anchors current={current} onPick={() => setOpen(false)} />
        </nav>
      )}
    </header>
  )
}
