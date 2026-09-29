import { useState } from 'react'

/** A command in mono on the raised background, with a Copy button that says Copied for 2 seconds. */
export function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <div className="mt-3 flex items-start gap-2 rounded-[6px] bg-raised">
      <pre tabIndex={0} className="m-0 min-w-0 flex-1 overflow-x-auto py-4 pl-5 font-mono text-[13px] leading-5 text-text md:text-[14px] md:leading-[22px]">
        <code>{code}</code>
      </pre>
      <button
        type="button"
        onClick={copy}
        className="mt-2.5 mr-2.5 min-h-8 shrink-0 cursor-pointer rounded-[6px] border border-rule bg-transparent px-3 text-[13px] leading-5 text-cream-100"
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}
