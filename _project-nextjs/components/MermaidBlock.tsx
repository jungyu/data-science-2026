'use client'

import { useEffect, useRef, useState } from 'react'

interface MermaidBlockProps {
  chart: string  // Mermaid 語法字串
}

/**
 * Mermaid 圖表渲染元件
 *
 * 使用方式：
 * <MermaidBlock chart="graph LR\n  A --> B" />
 *
 * 也可以傳入 AI 回傳的 mermaid code block 內容。
 */
export default function MermaidBlock({ chart }: MermaidBlockProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current || !chart.trim()) return

    // 動態 import mermaid（避免 SSR 問題）
    import('mermaid').then((m) => {
      const mermaid = m.default
      mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
      })

      const id = `mermaid-${Math.random().toString(36).slice(2)}`
      mermaid
        .render(id, chart)
        .then(({ svg }) => {
          if (containerRef.current) {
            containerRef.current.innerHTML = svg
            setError(null)
          }
        })
        .catch((err) => {
          setError(`Mermaid 語法錯誤：${err.message}`)
        })
    })
  }, [chart])

  if (error) {
    return (
      <div className="alert alert-error text-sm">
        <span>{error}</span>
        <details className="mt-1">
          <summary className="cursor-pointer">查看原始語法</summary>
          <pre className="text-xs mt-1 overflow-x-auto">{chart}</pre>
        </details>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="mermaid-container flex justify-center py-2 overflow-x-auto"
    />
  )
}
