import type { SiteContent } from '../types'

/** Members from site.json, then how to reach the team. */
export function Team({ site }: { site: SiteContent }) {
  return (
    <div>
      <ul className="m-0 grid list-none grid-cols-1 gap-8 p-0 sm:grid-cols-2 lg:grid-cols-4">
        {site.members.map((m) => (
          <li key={m.name}>
            <p className="text-title m-0 mb-1">{m.name}</p>
            <p className="text-small m-0 text-muted">{m.role}</p>
            <a className="text-small mt-2 inline-block" href={m.github}>
              GitHub profile
            </a>
          </li>
        ))}
      </ul>
      <div className="page-grid mt-16 gap-y-6 md:mt-24">
        <div className="col-span-4">
          <p className="text-caption m-0">Questions or feedback</p>
          <a className="text-[15px]" href={`mailto:${site.contact_email}`}>
            {site.contact_email}
          </a>
        </div>
        <div className="col-span-4">
          <p className="text-caption m-0">Found a problem</p>
          <a className="text-[15px]" href={`${site.repo_url}/issues`}>
            Open an issue
          </a>
        </div>
        <div className="col-span-4">
          <p className="text-caption m-0">License</p>
          <p className="m-0 text-[15px]">{site.license}</p>
        </div>
      </div>
    </div>
  )
}
