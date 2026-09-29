import type { Results } from '../../types'
import { DataTable } from './DataTable'

/** The failure log as the README table, then the honest scope statement. */
export function FailureModes({ failures }: { failures: Results['tables']['failures'] | null }) {
  return (
    <div>
      {failures && failures.length > 0 ? (
        <div className="overflow-x-auto">
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
          pgvector's HNSW index (our own HNSW is measured against it above), and embeddings come from the
          provider's embedding model. Retrieval, routing, graph traversal, merging and the classifier are our own
          code.
        </p>
      </div>
    </div>
  )
}
