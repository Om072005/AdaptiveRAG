import type { ComponentProps } from 'react'

const BASE =
  'inline-flex min-h-11 cursor-pointer items-center rounded-[6px] border px-5 font-sans text-[15px] leading-none font-medium no-underline transition-colors duration-150 ease-page'
const KIND = {
  primary: 'border-transparent bg-white text-black hover:bg-cream-100 hover:text-black',
  secondary: 'border-cream-300 bg-transparent text-cream-100 hover:border-white hover:text-white',
}

type Kind = keyof typeof KIND

export function Button({ kind = 'secondary', className = '', ...rest }: ComponentProps<'button'> & { kind?: Kind }) {
  return <button type="button" className={`${BASE} ${KIND[kind]} disabled:cursor-default disabled:opacity-50 ${className}`} {...rest} />
}

export function ButtonLink({ kind = 'secondary', className = '', ...rest }: ComponentProps<'a'> & { kind?: Kind }) {
  return <a className={`${BASE} ${KIND[kind]} ${className}`} {...rest} />
}
