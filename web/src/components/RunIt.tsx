import { CodeBlock } from './CodeBlock'

// The CLI of contract section 7, in the order a new machine needs it.
const STEPS: { text: string; code: string }[] = [
  { text: 'Clone the repository and install the Python side with uv.', code: 'git clone https://github.com/Om072005/AdaptiveRAG.git\ncd AdaptiveRAG\nuv sync' },
  {
    text: 'Pull the local models with Ollama: the embedder, the small model and the large one.',
    code: 'ollama pull nomic-embed-text\nollama pull gpt-oss:20b\nollama pull qwen3.6:35b-a3b',
  },
  {
    text: 'Copy the environment file and fill in your own Neon branch and your own Gemini key for the judge (both free tiers).',
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

export function RunIt() {
  return (
    <ol className="m-0 list-none p-0 lg:max-w-[68%]">
      {STEPS.map((s, i) => (
        <li key={s.code} className="mb-10 grid grid-cols-[40px_minmax(0,1fr)] md:grid-cols-[48px_minmax(0,1fr)]">
          <span className="font-serif text-[24px] leading-8 text-muted">{i + 1}</span>
          <div className="min-w-0">
            <p className="text-body m-0">{s.text}</p>
            <CodeBlock code={s.code} />
          </div>
        </li>
      ))}
    </ol>
  )
}
