import type { ReactNode } from 'react'
import { CodeBlock } from './CodeBlock'
import { DatabaseIcon, LayersIcon, ShieldCheckIcon, TerminalIcon } from './Icons'

// The CLI of contract section 7, in the order a new machine needs it.
const STEPS: { text: string; code: string }[] = [
  { text: 'Clone the repository and install the Python side with uv.', code: 'git clone https://github.com/Om072005/AdaptiveRAG.git\ncd AdaptiveRAG\nuv sync' },
  {
    text: 'Pull the local models with Ollama: the embedder, the small model, the large one and the judge.',
    code: 'ollama pull nomic-embed-text\nollama pull gpt-oss:20b\nollama pull qwen3.6:35b-a3b\nollama pull gemma4:31b',
  },
  {
    text: 'Copy the environment file and fill in your own Neon branch (free tier). Every model runs locally, so no API key is needed.',
    code: 'cp .env.example .env',
  },
  { text: 'Create the tables on your database.', code: 'uv run python -m adaptiverag.stores.migrate' },
  { text: 'Ingest the small corpus of 30 questions.', code: 'uv run python -m adaptiverag.ingest run --corpus mini' },
  { text: 'Ask a question from the command line.', code: 'uv run python -m adaptiverag ask "Who was born first, Yanka Dyagileva or Alexander Bashlachev?"' },
  { text: 'Run the checks: lint, types, unit tests and the page.', code: 'bash scripts/check.sh' },
  {
    text: 'Start the local API and this page with a live question box.',
    code: 'uv run python -m adaptiverag serve\ncd web && VITE_LIVE_API_URL=http://localhost:8000 npm run dev',
  },
]

const NEEDS: { icon: ReactNode; title: string; text: string }[] = [
  { icon: <TerminalIcon size={18} />, title: 'Python with uv', text: 'Installs the whole Python side in one command.' },
  { icon: <LayersIcon size={18} />, title: 'Ollama', text: 'Runs the embedder, both answer models and the judge locally.' },
  { icon: <DatabaseIcon size={18} />, title: 'A free Neon database', text: 'Postgres with pgvector holds chunks, graph and traces.' },
  { icon: <ShieldCheckIcon size={18} />, title: 'No API keys', text: 'Every model runs on your machine. Nothing is sent out.' },
]

export function RunIt() {
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] lg:gap-14">
      <div>
        <div className="card p-6 lg:sticky lg:top-24">
          <h3 className="text-title m-0">What you need</h3>
          <ul className="m-0 mt-5 list-none space-y-4 p-0">
            {NEEDS.map((n) => (
              <li key={n.title} className="flex gap-3">
                <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-accent-soft text-accent-text">{n.icon}</span>
                <span>
                  <span className="block text-[14.5px] leading-6 font-[620] text-ink">{n.title}</span>
                  <span className="text-caption block">{n.text}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <ol className="relative m-0 list-none p-0">
        <span aria-hidden="true" className="absolute top-4 bottom-4 left-[15px] w-px bg-rule" />
        {STEPS.map((s, i) => (
          <li key={s.code} className="relative mb-8 grid grid-cols-[32px_minmax(0,1fr)] gap-4 last:mb-0">
            <span className="relative z-[1] inline-flex size-8 items-center justify-center rounded-full border border-rule bg-surface text-[13px] font-[650] text-ink">{i + 1}</span>
            <div className="min-w-0 pt-1">
              <p className="text-body m-0 text-text">{s.text}</p>
              <CodeBlock code={s.code} />
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
