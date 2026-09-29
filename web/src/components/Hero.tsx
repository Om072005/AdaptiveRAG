import { ButtonLink } from './Button'

export function Hero({ repoUrl }: { repoUrl: string }) {
  return (
    <section className="page-wrap pt-16 pb-20 md:pt-32 md:pb-40">
      <div className="page-grid">
        <div className="col-span-4 md:col-span-8">
          <h1 className="text-statement m-0">A research assistant that decides how to search before it answers.</h1>
          <p className="text-lede mt-6 mb-0">
            AdaptiveRAG reads each question, sends it to vector search, a walk through a knowledge graph, or both,
            answers with citations, and records what every step cost. Everything on this page comes from recorded
            runs.
          </p>
          <div className="mt-12 flex flex-wrap gap-4">
            <ButtonLink kind="primary" href="#follow">
              Follow a question
            </ButtonLink>
            <ButtonLink href={repoUrl}>View the code on GitHub</ButtonLink>
          </div>
        </div>
      </div>
    </section>
  )
}
