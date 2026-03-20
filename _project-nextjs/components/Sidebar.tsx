'use client'

import { useState, useRef, useEffect } from 'react'
import MermaidBlock from './MermaidBlock'

interface Message {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

interface SidebarProps {
  presetQuestions: string[]
}

/**
 * 解析 AI 回應，將 ```mermaid 和 ```chart-json 區塊拆分出來
 */
function parseContent(text: string): Array<{ type: 'text' | 'mermaid' | 'chart-json'; content: string }> {
  const parts: Array<{ type: 'text' | 'mermaid' | 'chart-json'; content: string }> = []
  const regex = /```(mermaid|chart-json)\n([\s\S]*?)```/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    parts.push({ type: match[1] as 'mermaid' | 'chart-json', content: match[2].trim() })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.slice(lastIndex) })
  }

  return parts
}

/**
 * AI 側欄元件
 *
 * 功能：
 * - 預設問題快速按鈕（學生自訂）
 * - 自由輸入問題
 * - SSE streaming 回應
 * - 自動渲染 Mermaid 圖表
 */
export default function Sidebar({ presetQuestions }: SidebarProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '你好！我是你的資料科學助理。\n\n請點選下方的預設問題，或直接輸入你的問題。',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // 自動捲動到最新訊息
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return

    const userMessage: Message = { role: 'user', content: text }
    const assistantMessage: Message = { role: 'assistant', content: '', streaming: true }

    setMessages((prev) => [...prev, userMessage, assistantMessage])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })

      if (!res.body) throw new Error('無回應串流')

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = dec.decode(value)
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const { text: token } = JSON.parse(line.slice(6))
            accumulated += token
            setMessages((prev) => {
              const updated = [...prev]
              updated[updated.length - 1] = {
                role: 'assistant',
                content: accumulated,
                streaming: true,
              }
              return updated
            })
          } catch {
            // 忽略
          }
        }
      }

      // 串流結束，移除 streaming 標記
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: accumulated }
        return updated
      })

    } catch (err) {
      const msg = err instanceof Error ? err.message : '發生錯誤'
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `> ⚠️ ${msg}`,
        }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <aside className="w-80 flex flex-col bg-base-100 border-l border-base-300">

      {/* 標題 */}
      <div className="p-3 border-b border-base-300">
        <h2 className="font-semibold text-sm flex items-center gap-2">
          <span className="text-primary">✦</span> AI 助理
        </h2>
      </div>

      {/* 對話訊息列表 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`chat ${msg.role === 'user' ? 'chat-end' : 'chat-start'}`}>
            <div
              className={`chat-bubble text-sm ${
                msg.role === 'user'
                  ? 'chat-bubble-primary'
                  : 'chat-bubble-neutral'
              } ${msg.streaming ? 'cursor-blink' : ''}`}
            >
              <MessageContent content={msg.content} />
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* 預設問題按鈕 */}
      <div className="p-3 border-t border-base-300 space-y-1">
        <p className="text-xs text-base-content/50 mb-2">快速提問</p>
        {presetQuestions.map((q) => (
          <button
            key={q}
            className="btn btn-xs btn-outline btn-primary w-full text-left justify-start normal-case h-auto py-1 px-2 text-xs"
            onClick={() => sendMessage(q)}
            disabled={loading}
          >
            {q}
          </button>
        ))}
      </div>

      {/* 輸入框 */}
      <div className="p-3 border-t border-base-300 flex gap-2">
        <input
          type="text"
          className="input input-bordered input-sm flex-1 text-sm"
          placeholder="輸入問題..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              sendMessage(input)
            }
          }}
          disabled={loading}
        />
        <button
          className="btn btn-primary btn-sm"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          {loading ? <span className="loading loading-spinner loading-xs" /> : '送出'}
        </button>
      </div>

    </aside>
  )
}

/** 解析並渲染訊息內容（文字 + Mermaid + Chart JSON） */
function MessageContent({ content }: { content: string }) {
  const parts = parseContent(content)

  return (
    <>
      {parts.map((part, i) => {
        if (part.type === 'mermaid') {
          return <MermaidBlock key={i} chart={part.content} />
        }
        if (part.type === 'chart-json') {
          return (
            <pre key={i} className="bg-base-300 rounded p-2 text-xs overflow-x-auto mt-1">
              {part.content}
            </pre>
          )
        }
        return (
          <span key={i} className="whitespace-pre-wrap">
            {part.content}
          </span>
        )
      })}
    </>
  )
}
