import type { Results } from '../../types'
import { DataTable } from './DataTable'

/** The failure log as the README table, then the honest scope statement. */
export function FailureModes({ failures }: { failures: Results['tables']['failures'] | null }) {
  return (
    <div>
      {failures && failures.length > 0 ? (
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Failure log">
          <DataTable
            rows={failures}
            columns={[
              { label: '#', value: (r) => r.n, numeric: true },
              { label: 'Symptom', value: (r) => r.symptom, wrap: true },
              { label: 'Root cause', value: (r) => r.root_cause, wrap: true },
              { label: 'Fix', value: (r) => r.fix, wrap: true },
              { label: 'Status', value: (r) => r.status, wrap: true },
              { label: 'Run', value: (r) => (r.run_id ? <span className="font-mono text-[13px]">{r.run_id}</span> : 'None') },
            ]}
          />
        </div>
      ) : (
        <p className="text-small m-0 text-muted">The failure log is published with the final results.</p>
      )}
      <h3 className="text-title m-0 mt-16">Honest scope</h3>
      <div className="text-body mt-4">
        <p className="m-0">
          Every number on this page comes from a run listed in the project's pinned results, and each figure names
          that run. A result that came out worse than expected stays on the page.
        </p>
        <p className="m-0 mt-6">
          Where a part uses a library default instead of our own code, we say so: vector search is served by
          pgvector's HNSW index (our own HNSW is measured against it above), and embeddings come from an open
          model, nomic-embed-text, served by Ollama on one of our machines. Retrieval, routing, graph traversal,
          merging and the classifier are our own code.
        </p>
        <p className="m-0 mt-6">
          Answers come from open models run through Ollama: gpt-oss 20B as the small model and Qwen 3.6 35B-A3B as
          the large one. Their cost is the public list price of the same weights, not what we paid. Every answer is
          scored by Gemma 4 31B on Google's Gemini API, a different model family from both, and because a judge
          model is an imperfect proxy, a sample of its scores is checked by hand and the agreement is reported with
          the results. Latency comes from two machines: model calls first made on a rented server with two RTX
          5090 cards keep that time when a later run reuses them from the cache, and new calls and database round
          trips are timed on one of our PCs.
        </p>
      </div>
    </div>
  )
}
