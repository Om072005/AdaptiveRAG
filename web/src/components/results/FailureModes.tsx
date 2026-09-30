import type { ReactNode } from 'react'
import type { Results } from '../../types'
import { AlertIcon, CheckIcon, ChevronDownIcon, DotCircleIcon } from '../Icons'
import { RunId } from '../RunId'

type Failure = Results['tables']['failures'][number]

/** Text with `code` spans from the failure log shown in mono. */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split(/(`[^`]+`)/).map((part, i) =>
        part.startsWith('`') && part.endsWith('`') ? (
          <code key={i} className="rounded-[4px] bg-sunken px-1 py-0.5 font-mono text-[0.88em] text-ink">
            {part.slice(1, -1)}
          </code>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  )
}

const RUN_ID = /^\d{8}-\d{4}-[\w-]+$/

/** The run field: run ids as copyable chips, anything else (a review, a commit) as text. */
function Runs({ text }: { text: string | null }) {
  if (!text) return <span>review, not a run</span>
  const parts = text.split(/`?,\s*`?/).map((p) => p.replace(/`/g, '').trim())
  if (!parts.every((p) => RUN_ID.test(p))) return <Rich text={text} />
  return (
    <>
      {parts.map((id) => (
        <RunId key={id} id={id} />
      ))}
    </>
  )
}

function state(status: string): { word: string; tone: string; icon: ReactNode } {
  const s = status.toLowerCase()
  if (s.startsWith('closed') || s.startsWith('fixed')) return { word: s.startsWith('fixed') ? 'Fixed' : 'Closed', tone: 'bg-good-soft text-good', icon: <CheckIcon size={14} /> }
  if (s.startsWith('open')) return { word: 'Open', tone: 'bg-bad-soft text-bad', icon: <AlertIcon size={14} /> }
  return { word: 'Known limit', tone: 'bg-warn-soft text-warn', icon: <DotCircleIcon size={14} /> }
}

function FailureCard({ f }: { f: Failure }) {
  const s = state(f.status)
  return (
    <li className="card flex flex-col p-5 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <span className="text-caption font-[600]">Incident {f.n}</span>
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[12.5px] leading-5 font-[600] ${s.tone}`}>
          {s.icon}
          {s.word}
        </span>
      </div>
      <p className="m-0 mt-3 text-[15.5px] leading-6 font-[560] text-ink">
        <Rich text={f.symptom} />
      </p>
      <details className="group mt-4 border-t border-rule pt-3">
        <summary className="flex min-h-9 cursor-pointer list-none items-center justify-between text-[13.5px] font-[560] text-accent-text [&::-webkit-details-marker]:hidden">
          Cause, fix and status
          <ChevronDownIcon size={16} className="transition-transform group-open:rotate-180" />
        </summary>
        <dl className="m-0 mt-2 text-[14px] leading-[22px]">
          {[
            ['Root cause', f.root_cause],
            ['Fix', f.fix],
            ['Status', f.status],
          ].map(([k, v]) => (
            <div key={k} className="mt-3">
              <dt className="text-caption font-[600]">{k}</dt>
              <dd className="m-0 mt-0.5">
                <Rich text={v} />
              </dd>
            </div>
          ))}
        </dl>
      </details>
      <p className="text-caption m-0 mt-auto flex flex-wrap items-center gap-x-2 gap-y-1 pt-4">
        Seen in <Runs text={f.run_id} />
      </p>
    </li>
  )
}

/** The failure log as cards, then the honest scope statement. */
export function FailureModes({ failures }: { failures: Results['tables']['failures'] | null }) {
  return (
    <div>
      {failures && failures.length > 0 ? (
        <ul className="m-0 grid list-none grid-cols-1 gap-5 p-0 md:grid-cols-2 lg:grid-cols-3" aria-label="Failure log">
          {failures.map((f) => (
            <FailureCard key={f.n} f={f} />
          ))}
        </ul>
      ) : (
        <p className="text-small m-0 text-muted">The failure log is published with the final results.</p>
      )}
      <div className="card mt-10 grid grid-cols-1 gap-8 p-6 md:p-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div>
          <p className="text-eyebrow m-0">Honest scope</p>
          <h3 className="text-title m-0 mt-2">What is ours, and what is borrowed.</h3>
        </div>
        <div className="text-small flex flex-col gap-4 text-text">
          <p className="m-0">
            Every number on this page comes from a run listed in the project's pinned results, and each figure names
            that run. A result that came out worse than expected stays on the page.
          </p>
          <p className="m-0">
            Where a part uses a library default instead of our own code, we say so: vector search is served by
            pgvector's HNSW index (our own HNSW is measured against it above), and embeddings come from an open
            model, nomic-embed-text, served by Ollama on one of our machines. Retrieval, routing, graph traversal,
            merging and the classifier are our own code.
          </p>
          <p className="m-0">
            Answers come from open models run through Ollama: gpt-oss 20B as the small model and Qwen 3.6 35B-A3B as
            the large one. Their cost is the public list price of the same weights, not what we paid. Every answer is
            scored by Gemma 4 31B (open weights, run on a rented GPU server), a different model family from both, and
            because a judge model is an imperfect proxy, a sample of its scores is checked by hand and the agreement
            is reported with the results. Latency comes from two machines: model calls first made on a rented server
            with two RTX 5090 cards keep that time when a later run reuses them from the cache, and new calls and
            database round trips are timed on one of our PCs.
          </p>
        </div>
      </div>
    </div>
  )
}
