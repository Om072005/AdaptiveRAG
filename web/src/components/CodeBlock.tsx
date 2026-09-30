import { useState } from 'react'
import { CheckIcon, CopyIcon } from './Icons'

/** A command in mono on the terminal surface, with a Copy button that says Copied for 2 seconds. */
export function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <div className="mt-3 flex items-start gap-2 rounded-[2px] border border-code-rule bg-code-bg">
      <pre tabIndex={0} className="m-0 min-w-0 flex-1 overflow-x-auto py-3.5 pl-4 font-mono text-[13px] leading-5 text-code-text md:text-[13.5px] md:leading-[22px]">
        <code>
          {code.split('\n').map((line, i) => (
            <span key={i} className="block">
              <span aria-hidden="true" className="mr-3 text-code-prompt select-none">$</span>
              {line}
            </span>
          ))}
        </code>
      </pre>
      <button
        type="button"
        onClick={copy}
        className="mt-2 mr-2 inline-flex min-h-8 shrink-0 cursor-pointer items-center gap-1.5 rounded-[2px] border border-code-rule bg-transparent px-2.5 text-[12.5px] leading-5 text-code-text hover:border-line"
      >
        {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}
