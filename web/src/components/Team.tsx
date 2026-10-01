import type { SiteContent } from '../types'
import { ButtonLink } from './Button'
import { BugIcon, GitHubIcon } from './Icons'

/** The team from site.json, each with a GitHub button, then where to report a problem. */
export function Team({ site }: { site: SiteContent }) {
  return (
    <div>
      <ul className="m-0 grid list-none grid-cols-1 border-y border-ink p-0 sm:grid-cols-2 lg:grid-cols-4">
        {site.members.map((m, i) => (
          <li
            key={m.name}
            className={`flex flex-col px-0 py-6 sm:px-6 ${i > 0 ? 'border-t border-rule sm:border-t-0' : ''} ${i % 2 === 1 ? 'sm:border-l sm:border-rule' : ''} ${i >= 2 ? 'sm:border-t sm:border-rule lg:border-t-0' : ''} ${i === 2 ? 'lg:border-l' : ''} ${i === 0 ? 'sm:pl-0' : ''}`}
          >
            <p className="text-label m-0">Member {i + 1}</p>
            <p className="text-title m-0 mt-2 mb-5 break-words">{m.name}</p>
            <ButtonLink href={m.github} className="mt-auto self-start">
              <GitHubIcon size={15} />
              GitHub profile
            </ButtonLink>
          </li>
        ))}
      </ul>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
        <p className="m-0 flex items-center gap-3 font-sans text-[21px] leading-7 text-ink">
          <BugIcon size={20} />
          Found a problem?
        </p>
        <ButtonLink kind="primary" href={`${site.repo_url}/issues`}>
          Open an issue
        </ButtonLink>
      </div>
    </div>
  )
}
