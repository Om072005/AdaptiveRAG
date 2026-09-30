import type { ReactNode, SVGProps } from 'react'

// Line icons in the Lucide style: 24 unit box, 1.75 stroke, round caps, drawn in currentColor.
function Icon({ children, size = 20, ...rest }: SVGProps<SVGSVGElement> & { size?: number; children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  )
}

type P = SVGProps<SVGSVGElement> & { size?: number }

export const SunIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </Icon>
)
export const MoonIcon = (p: P) => (
  <Icon {...p}>
    <path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11z" />
  </Icon>
)
export const GitHubIcon = (p: P) => (
  <Icon {...p}>
    <path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21" />
  </Icon>
)
export const MenuIcon = (p: P) => (
  <Icon {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Icon>
)
export const CloseIcon = (p: P) => (
  <Icon {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Icon>
)
export const ArrowRightIcon = (p: P) => (
  <Icon {...p}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Icon>
)
export const PlayIcon = (p: P) => (
  <Icon {...p}>
    <path d="M7 5v14l11-7z" />
  </Icon>
)
export const PauseIcon = (p: P) => (
  <Icon {...p}>
    <path d="M8 5v14M16 5v14" />
  </Icon>
)
export const CopyIcon = (p: P) => (
  <Icon {...p}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M5 15V6a2 2 0 0 1 2-2h8" />
  </Icon>
)
export const CheckIcon = (p: P) => (
  <Icon {...p}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Icon>
)
export const AlertIcon = (p: P) => (
  <Icon {...p}>
    <path d="M12 3l9.5 17h-19z" />
    <path d="M12 10v4M12 17.5v.01" />
  </Icon>
)
export const DotCircleIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <circle cx="12" cy="12" r="2.5" />
  </Icon>
)
export const TableIcon = (p: P) => (
  <Icon {...p}>
    <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
    <path d="M3.5 9.5h17M3.5 14.5h17M9.5 9.5v10" />
  </Icon>
)
export const ChartIcon = (p: P) => (
  <Icon {...p}>
    <path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6" />
  </Icon>
)
export const SearchIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M20 20l-4.2-4.2" />
  </Icon>
)
export const NetworkIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="5.5" cy="6" r="2.5" />
    <circle cx="18.5" cy="6" r="2.5" />
    <circle cx="12" cy="18" r="2.5" />
    <path d="M8 6h8M7 8l3.7 7.8M17 8l-3.7 7.8" />
  </Icon>
)
export const MergeIcon = (p: P) => (
  <Icon {...p}>
    <path d="M6 3v4c0 3.5 6 4.5 6 8.5V21M18 3v4c0 3.5-6 4.5-6 8.5" />
    <path d="M8.5 18.5L12 21l3.5-2.5" />
  </Icon>
)
export const RouteIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="5" cy="12" r="2.5" />
    <path d="M7.5 12h3c3 0 3-6 6-6H20M10.5 12H20M10.5 12c3 0 3 6 6 6H20" />
  </Icon>
)
export const BrainTagIcon = (p: P) => (
  <Icon {...p}>
    <path d="M3.5 12.5V5a1.5 1.5 0 0 1 1.5-1.5h7.5l8 8a1.5 1.5 0 0 1 0 2.1l-6.4 6.4a1.5 1.5 0 0 1-2.1 0z" />
    <circle cx="8" cy="8" r="1.5" />
  </Icon>
)
export const QuoteIcon = (p: P) => (
  <Icon {...p}>
    <path d="M4 5h16v11H9l-5 4z" />
    <path d="M8.5 9.5h7M8.5 12.5h4" />
  </Icon>
)
export const ShieldCheckIcon = (p: P) => (
  <Icon {...p}>
    <path d="M12 3l7.5 3v5.5c0 4.5-3.2 8-7.5 9.5-4.3-1.5-7.5-5-7.5-9.5V6z" />
    <path d="M8.5 12l2.5 2.5 4.5-5" />
  </Icon>
)
export const LayersIcon = (p: P) => (
  <Icon {...p}>
    <path d="M12 3.5l9 4.5-9 4.5-9-4.5z" />
    <path d="M3 12.5l9 4.5 9-4.5M3 16.5l9 4.5 9-4.5" />
  </Icon>
)
export const DatabaseIcon = (p: P) => (
  <Icon {...p}>
    <ellipse cx="12" cy="5.5" rx="7.5" ry="2.5" />
    <path d="M4.5 5.5v13c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-13M4.5 12c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5" />
  </Icon>
)
export const LoopIcon = (p: P) => (
  <Icon {...p}>
    <path d="M20 11a8 8 0 0 0-14.3-4.9L4 8M4 4v4h4M4 13a8 8 0 0 0 14.3 4.9L20 16M20 20v-4h-4" />
  </Icon>
)
export const TerminalIcon = (p: P) => (
  <Icon {...p}>
    <rect x="3" y="4.5" width="18" height="15" rx="2.5" />
    <path d="M7 10l3 2.5L7 15M12.5 15H17" />
  </Icon>
)
export const MailIcon = (p: P) => (
  <Icon {...p}>
    <rect x="3" y="5" width="18" height="14" rx="2.5" />
    <path d="M3.5 7l8.5 6 8.5-6" />
  </Icon>
)
export const BugIcon = (p: P) => (
  <Icon {...p}>
    <rect x="7" y="7.5" width="10" height="12.5" rx="5" />
    <path d="M12 11v9M7 13H3.5M20.5 13H17M7.5 17.5l-3 2M16.5 17.5l3 2M7.5 9.5l-3-2M16.5 9.5l3-2M9 7.5a3 3 0 0 1 6 0" />
  </Icon>
)
export const ScaleIcon = (p: P) => (
  <Icon {...p}>
    <path d="M12 4v16M7 20h10M5 7h14M5 7l-2.5 6a2.5 2.5 0 0 0 5 0zM19 7l-2.5 6a2.5 2.5 0 0 0 5 0z" />
  </Icon>
)
export const ChevronDownIcon = (p: P) => (
  <Icon {...p}>
    <path d="M6 9l6 6 6-6" />
  </Icon>
)
