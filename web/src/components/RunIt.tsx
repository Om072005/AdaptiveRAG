import type { ReactNode } from 'react'
import { CodeBlock } from './CodeBlock'
import { DatabaseIcon, LayersIcon, ShieldCheckIcon, TerminalIcon } from './Icons'

// The CLI of contract section 7, in the order a new machine needs it.
const STEPS: { text: string; code: string }[] = [
  {
    text: 'Clone the repository and install the Python side with uv. It brings its own Postgres with pgvector.',
    code: 'git clone https://github.com/Om072005/AdaptiveRAG.git\ncd AdaptiveRAG\nuv sync',
  },
  {
    text: 'Pull the two models every question needs. The large model and the judge are optional: with the large one, multi hop and comparison questions use it as the recorded runs did.',
    code: 'ollama pull nomic-embed-text\nollama pull gpt-oss:20b\nollama pull qwen3.6:35b-a3b   # optional\nollama pull gemma4:31b        # optional, the judge',
  },
  {
    text: 'Create the database on your disk and load the corpus: 2,957 documents with their graph, embedded by your own Ollama. About two minutes on a GPU, once.',
    code: 'uv run python -m adaptiverag demo setup',
  },
  { text: 'Check the database, the models and the GPU, and warm the small model.', code: 'uv run python -m adaptiverag demo check' },
  {
    text: 'Ask a question. Every step prints the moment it ends, then the model reasons and answers in front of you.',
    code: 'uv run python -m adaptiverag ask "Who died first, Bryce Courtenay or Juan Carlos Onetti?"',
  },
  { text: 'Open this page with a live question box that shows the same steps as they happen.', code: 'uv run python -m adaptiverag demo page' },
  { text: 'Run three recorded questions live and see your scores next to the recorded ones.', code: 'uv run python -m adaptiverag demo eval' },
  { text: 'Run the checks: lint, types, unit tests and the page.', code: 'bash scripts/check.sh' },
]

const NEEDS: { icon: ReactNode; title: string; text: string }[] = [
  { icon: <TerminalIcon size={18} />, title: 'Python with uv', text: 'Installs the whole Python side, the database included, in one command.' },
  { icon: <LayersIcon size={18} />, title: 'Ollama', text: 'Runs the embedder and the answer models on your machine.' },
  { icon: <DatabaseIcon size={18} />, title: 'No account', text: 'Postgres with pgvector runs from a folder in the clone. Node 20 or newer for this page.' },
  { icon: <ShieldCheckIcon size={18} />, title: 'No API keys', text: 'After the downloads it works offline. Nothing is sent out.' },
]

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
