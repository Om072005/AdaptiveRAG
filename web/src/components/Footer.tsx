import { ButtonLink } from './Button'
import { ArrowRightIcon, GitHubIcon } from './Icons'
import { Wordmark } from './Logo'

// the build year, fixed at build time
const YEAR = new Date().getFullYear()

/** A closing call to action in an ink block, then the colophon. */
export function Footer({ repoUrl }: { repoUrl: string }) {
  return (
    <footer>
      <div className="page-wrap pb-12">
        <div className="ink-block flex flex-col items-start gap-8 p-8 md:p-12 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="m-0 font-mono text-[12px] tracking-[0.08em] uppercase opacity-70">Last word</p>
            <h2 className="m-0 mt-3 font-headline text-[48px] leading-[0.9] md:text-[80px]">See how it handles your questions.</h2>
            <p className="m-0 mt-4 max-w-[46ch] font-sans text-[20px] leading-[26px] opacity-85">
              Clone it, pull the open models and ask anything. Everything runs on your machine.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-3">
            <a
              href="#run"
              className="inline-flex min-h-11 items-center gap-2 border border-canvas bg-canvas px-5 font-mono text-[12.5px] tracking-[0.08em] text-ink uppercase no-underline hover:bg-accent hover:text-ink"
            >
              Run it yourself
              <ArrowRightIcon size={15} />
            </a>
            <ButtonLink href={repoUrl} className="border-canvas text-canvas hover:text-canvas">
              <GitHubIcon size={15} />
              Star on GitHub
            </ButtonLink>
          </div>
        </div>
      </div>
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
              <a href={repoUrl}>Repository</a> · {YEAR}
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
