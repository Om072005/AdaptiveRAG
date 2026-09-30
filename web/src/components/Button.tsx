import type { ComponentProps } from 'react'

const BASE =
  'inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 border px-5 font-mono text-[12.5px] leading-none font-[500] tracking-[0.08em] uppercase no-underline transition-all duration-150 ease-page'
const KIND = {
  primary: 'border-ink bg-ink text-canvas hover:shadow-md hover:text-canvas',
  secondary: 'border-ink bg-transparent text-ink hover:shadow-md hover:text-ink',
  // on an ink block: paper colored outline and type
  inverse: 'border-canvas bg-transparent text-canvas hover:bg-canvas hover:text-ink',
  ghost: 'border-transparent bg-transparent text-ink underline decoration-accent underline-offset-4 hover:text-accent-text',
}

type Kind = keyof typeof KIND

export function Button({ kind = 'secondary', className = '', ...rest }: ComponentProps<'button'> & { kind?: Kind }) {
  return (
    <button
      type="button"
      className={`${BASE} ${KIND[kind]} disabled:cursor-default disabled:opacity-40 disabled:hover:shadow-none ${className}`}
      {...rest}
    />
  )
}

export function ButtonLink({ kind = 'secondary', className = '', ...rest }: ComponentProps<'a'> & { kind?: Kind }) {
  return <a className={`${BASE} ${KIND[kind]} ${className}`} {...rest} />
}
