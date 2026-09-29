const REPO_URL = 'https://github.com/Om072005/AdaptiveRAG'

export default function App() {
  return (
    <>
      <header className="page-wrap flex items-center justify-between py-6">
        <span className="font-serif text-[22px] leading-7 text-white">AdaptiveRAG</span>
        <a className="text-small" href={REPO_URL}>
          GitHub
        </a>
      </header>
      <main className="border-t border-rule">
        <div className="page-wrap page-grid pt-20 pb-32 md:pt-32 md:pb-40">
          <div className="col-span-4 md:col-span-8">
            <h1 className="text-statement m-0">
              A research assistant that decides how to search before it answers.
            </h1>
            <p className="text-lede mt-6">
              AdaptiveRAG routes each question to vector search, graph traversal or both,
              answers with citations, and records the cost and latency of every decision.
            </p>
            <p className="text-small mt-6 text-muted">
              The page is being built. Everything it will show comes from recorded runs.
            </p>
          </div>
        </div>
      </main>
    </>
  )
}
