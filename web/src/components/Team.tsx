import type { ReactNode } from 'react'
import type { SiteContent } from '../types'
import { BugIcon, GitHubIcon, MailIcon, ScaleIcon } from './Icons'

const initials = (name: string) => name.replace(/[^A-Za-z]/g, '').slice(0, 2).toUpperCase()

function Contact({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="card flex items-start gap-3 p-5">
      <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-sunken text-ink">{icon}</span>
      <div className="min-w-0">
        <p className="text-caption m-0 font-[600]">{label}</p>
        <div className="mt-0.5 text-[15px] leading-6 break-words">{children}</div>
      </div>
    </div>
  )
}

/** Members from site.json, then how to reach the team. */
export function Team({ site }: { site: SiteContent }) {
  return (
    <div>
      <ul className="m-0 grid list-none grid-cols-1 gap-5 p-0 sm:grid-cols-2 lg:grid-cols-4">
        {site.members.map((m) => (
          <li key={m.name} className="card card-hover flex flex-col p-6">
            <span aria-hidden="true" className="inline-flex size-12 items-center justify-center rounded-full bg-accent-soft text-[16px] font-[680] text-accent-text">
              {initials(m.name)}
            </span>
            <p className="text-title m-0 mt-4">{m.name}</p>
            <p className="text-small m-0 mt-1 text-muted">{m.role}</p>
            <a className="mt-auto inline-flex items-center gap-1.5 pt-4 text-[14px] font-[560] no-underline" href={m.github}>
              <GitHubIcon size={16} />
              GitHub profile
            </a>
          </li>
        ))}
      </ul>
      <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-3">
        <Contact icon={<MailIcon size={18} />} label="Questions or feedback">
          <a href={`mailto:${site.contact_email}`}>{site.contact_email}</a>
        </Contact>
        <Contact icon={<BugIcon size={18} />} label="Found a problem">
          <a href={`${site.repo_url}/issues`}>Open an issue</a>
        </Contact>
        <Contact icon={<ScaleIcon size={18} />} label="License">
          <span className="text-ink">{site.license}</span>
        </Contact>
      </div>
    </div>
  )
}
