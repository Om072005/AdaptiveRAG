import type { ReactNode } from 'react'
import { CodeBlock } from './CodeBlock'
import { ChevronDownIcon, DatabaseIcon, LayersIcon, ShieldCheckIcon, TerminalIcon } from './Icons'

// The CLI of contract section 7, in the order a new machine needs it. The first five ask a question;
// the rest are extras behind a reveal.
const FIRST = 5
const STEPS: { text: string; code: string }[] = [
  {
    text: 'Clone and install. Postgres with pgvector comes along.',
    code: 'git clone https://github.com/Om072005/AdaptiveRAG.git\ncd AdaptiveRAG\nuv sync',
  },
  {
    text: 'Pull the models. The large model and the judge are optional.',
    code: 'ollama pull nomic-embed-text\nollama pull gpt-oss:20b\nollama pull qwen3.6:35b-a3b   # optional\nollama pull gemma4:31b        # optional, the judge',
  },
  {
    text: 'Load the corpus into a local database. About two minutes on a GPU, once.',
    code: 'uv run python -m adaptiverag demo setup',
  },
  { text: 'Check the database, models and GPU.', code: 'uv run python -m adaptiverag demo check' },
  {
    text: 'Ask a question and watch each step as it happens.',
    code: 'uv run python -m adaptiverag ask "Who died first, Bryce Courtenay or Juan Carlos Onetti?"',
  },
  { text: 'This page, with a live question box. Needs Node 20 or newer.', code: 'uv run python -m adaptiverag demo page' },
  { text: 'Three recorded questions, scored live.', code: 'uv run python -m adaptiverag demo eval' },
  { text: 'Lint, types and tests.', code: 'bash scripts/check.sh' },
]

const NEEDS: { icon: ReactNode; title: string; text: string }[] = [
  { icon: <TerminalIcon size={18} />, title: 'Python with uv', text: 'One command, database included.' },
  { icon: <LayersIcon size={18} />, title: 'Ollama', text: 'Runs the models locally.' },
  { icon: <DatabaseIcon size={18} />, title: 'No account', text: 'The database runs from the clone.' },
  { icon: <ShieldCheckIcon size={18} />, title: 'No API keys', text: 'Offline after the downloads.' },
]

function Steps({ steps, start }: { steps: typeof STEPS; start: number }) {
  return (
    <ol className="relative m-0 list-none p-0" start={start}>
      <span aria-hidden="true" className="absolute top-4 bottom-4 left-[15px] w-px bg-rule" />
      {steps.map((s, i) => (
        <li key={s.code} className="relative mb-8 grid grid-cols-[32px_minmax(0,1fr)] gap-4 last:mb-0">
          <span className="relative z-[1] inline-flex size-8 items-center justify-center rounded-full border border-rule bg-surface text-[13px] font-[650] text-ink">{start + i}</span>
          <div className="min-w-0 pt-1">
            <p className="text-body m-0 text-text">{s.text}</p>
            <CodeBlock code={s.code} />
          </div>
        </li>
      ))}
    </ol>
  )
}

export function RunIt() {
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] lg:gap-14">
      <div>
        <div className="card p-6 lg:sticky lg:top-32">
          <h3 className="text-title m-0">What you need</h3>
          <ul className="m-0 mt-5 list-none space-y-4 p-0">
            {NEEDS.map((n) => (
              <li key={n.title} className="flex gap-3">
                <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-[2px] bg-accent-soft text-accent-text">{n.icon}</span>
                <span>
                  <span className="block text-[14.5px] leading-6 font-[620] text-ink">{n.title}</span>
                  <span className="text-caption block">{n.text}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="min-w-0">
        <Steps steps={STEPS.slice(0, FIRST)} start={1} />
        <details className="group mt-8">
          <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 border-y border-ink px-1 py-2 text-ink [&::-webkit-details-marker]:hidden">
            <span className="text-label">{STEPS.length - FIRST} more: live page, mini eval, checks</span>
            <ChevronDownIcon size={18} className="shrink-0 transition-transform group-open:rotate-180" />
          </summary>
          <div className="mt-6">
            <Steps steps={STEPS.slice(FIRST)} start={FIRST + 1} />
          </div>
        </details>
      </div>
    </div>
  )
}
