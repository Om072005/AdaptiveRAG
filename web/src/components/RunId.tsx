import { useState } from 'react'

/** A run id in mono that copies itself on click. */
export function RunId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard?.writeText(id).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button
      type="button"
      onClick={copy}
      title="Copy run id"
      className="cursor-pointer border-0 bg-transparent p-0 font-mono text-[13px] leading-5 text-text hover:text-white"
    >
      {id}
      <span className="sr-only">{copied ? ' copied' : ' (copy)'}</span>
    </button>
  )
}
