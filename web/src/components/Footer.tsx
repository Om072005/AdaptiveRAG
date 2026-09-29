// the build year, fixed at build time
const YEAR = new Date().getFullYear()

export function Footer({ repoUrl }: { repoUrl: string }) {
  return (
    <footer className="border-t border-rule pt-12 pb-16">
      <div className="page-wrap page-grid gap-y-4">
        <span className="col-span-4 font-serif text-[22px] leading-7 text-white md:col-span-8 lg:col-span-3">
          AdaptiveRAG
        </span>
        <div className="col-span-4 text-[13px] leading-[22px] text-muted md:col-span-8 lg:col-span-9">
          <p className="m-0 mb-1.5">Questions and passages from HotpotQA, CC BY-SA 4.0.</p>
          <p className="m-0 mb-1.5">Every number on this page comes from runs listed in docs/results/pinned.toml.</p>
          <p className="m-0">
            <a href={repoUrl}>Repository</a> · {YEAR}
          </p>
        </div>
      </div>
    </footer>
  )
}
