import { Wordmark } from './Logo'

// the build year, fixed at build time
const YEAR = new Date().getFullYear()

/** The colophon: the name, where the data comes from, the repository. */
export function Footer({ repoUrl }: { repoUrl: string }) {
  return (
    <footer>
      <div className="border-t-[3px] border-double border-ink">
        <div className="page-wrap flex flex-col gap-6 py-8 md:flex-row md:items-start md:justify-between">
          <div>
            <Wordmark />
            <p className="text-caption m-0 mt-3 max-w-[40ch]">Adaptive retrieval for question answering. Built by a team of four in thirteen days.</p>
          </div>
          <div className="text-caption flex flex-col gap-1.5 md:text-right">
            <p className="m-0">Questions and passages from HotpotQA, CC BY-SA 4.0.</p>
            <p className="m-0">Every number on this page comes from runs listed in docs/results/pinned.toml.</p>
            <p className="m-0">
              <a href={`${repoUrl}/blob/main/docs/lessons.md`}>What went wrong, and what we did about it</a>
            </p>
            <p className="m-0">
              <a href={repoUrl}>Repository</a> · {YEAR}
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
