import { ButtonLink } from './Button'
import { ArrowRightIcon, GitHubIcon } from './Icons'
import { Wordmark } from './Logo'

// the build year, fixed at build time
const YEAR = new Date().getFullYear()

/** A closing call to action, then the credits. */
export function Footer({ repoUrl }: { repoUrl: string }) {
  return (
    <footer>
      <div className="page-wrap pb-16">
        <div className="hero-glow card flex flex-col items-start gap-6 overflow-hidden p-8 md:flex-row md:items-center md:justify-between md:p-12">
          <div className="max-w-[48ch]">
            <h2 className="m-0 text-[28px] leading-9 font-[680] tracking-[-0.03em] text-ink md:text-[34px] md:leading-10">
              See how it handles your questions.
            </h2>
            <p className="text-small m-0 mt-2">Clone it, pull the open models and ask anything. Everything runs on your machine.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <ButtonLink kind="primary" href="#run">
              Run it yourself
              <ArrowRightIcon size={17} />
            </ButtonLink>
            <ButtonLink href={repoUrl}>
              <GitHubIcon size={17} />
              Star on GitHub
            </ButtonLink>
          </div>
        </div>
      </div>
      <div className="border-t border-rule">
        <div className="page-wrap flex flex-col gap-6 py-10 md:flex-row md:items-start md:justify-between">
          <div>
            <Wordmark />
            <p className="text-caption m-0 mt-3 max-w-[40ch]">Adaptive retrieval for question answering. Built by a team of four in thirteen days.</p>
          </div>
          <div className="text-caption flex flex-col gap-1.5 md:text-right">
            <p className="m-0">Questions and passages from HotpotQA, CC BY-SA 4.0.</p>
            <p className="m-0">Every number on this page comes from runs listed in docs/results/pinned.toml.</p>
            <p className="m-0">
              <a href={repoUrl}>Repository</a> · {YEAR}
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
