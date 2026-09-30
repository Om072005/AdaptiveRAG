import type { ComponentProps } from 'react'

const BASE =
  'inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-[10px] border px-5 font-sans text-[15px] leading-none font-[560] no-underline transition-all duration-150 ease-page'
const KIND = {
  primary: 'border-transparent bg-accent text-accent-ink shadow-sm hover:brightness-110 hover:text-accent-ink',
  secondary: 'border-rule bg-surface text-ink shadow-sm hover:border-faint hover:bg-sunken hover:text-ink',
  ghost: 'border-transparent bg-transparent text-text hover:bg-sunken hover:text-ink',
}

type Kind = keyof typeof KIND

export function Button({ kind = 'secondary', className = '', ...rest }: ComponentProps<'button'> & { kind?: Kind }) {
  return (
    <button
      type="button"
      className={`${BASE} ${KIND[kind]} disabled:cursor-default disabled:opacity-45 disabled:hover:brightness-100 ${className}`}
      {...rest}
    />
  )
}

export function ButtonLink({ kind = 'secondary', className = '', ...rest }: ComponentProps<'a'> & { kind?: Kind }) {
  return <a className={`${BASE} ${KIND[kind]} ${className}`} {...rest} />
}
