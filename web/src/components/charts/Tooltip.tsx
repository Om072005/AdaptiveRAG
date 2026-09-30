import { type ReactNode, type MouseEvent, useCallback, useRef, useState } from 'react'

type Tip = { x: number; y: number; width: number; content: ReactNode } | null

/** A hover tooltip that follows the pointer inside a relative container; keyboard focus shows it too. */
export function useTooltip() {
  const box = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<Tip>(null)
  const at = useCallback((clientX: number, clientY: number, content: ReactNode) => {
    const r = box.current?.getBoundingClientRect()
    if (!r) return
    setTip({ x: clientX - r.left, y: clientY - r.top, width: r.width, content })
  }, [])
  const show = useCallback((e: MouseEvent, content: ReactNode) => at(e.clientX, e.clientY, content), [at])
  const showAt = useCallback(
    (el: Element, content: ReactNode) => {
      const b = el.getBoundingClientRect()
      at(b.left + b.width / 2, b.top, content)
    },
    [at],
  )
  const hide = useCallback(() => setTip(null), [])
  const layer = tip && (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute z-10 w-max max-w-[240px] rounded-[10px] border border-rule bg-surface px-3 py-2 text-[13px] leading-5 text-text shadow-md"
      style={{
        left: Math.min(Math.max(tip.x, 8), Math.max(8, tip.width - 8)),
        top: tip.y,
        transform: `translate(${tip.x > tip.width * 0.6 ? 'calc(-100% - 12px)' : '12px'}, calc(-100% - 8px))`,
      }}
    >
      {tip.content}
    </div>
  )
  return { box, show, showAt, hide, layer }
}
