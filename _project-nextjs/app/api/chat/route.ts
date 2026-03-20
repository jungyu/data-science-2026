import { NextRequest } from 'next/server'
import { callMcpTool } from '@/lib/mcp-client'

export const runtime = 'nodejs'

export async function POST(req: NextRequest) {
  const { message } = await req.json()

  if (!message?.trim()) {
    return new Response('請輸入問題', { status: 400 })
  }

  // ── 建立 SSE 串流回應 ──────────────────────────────────────
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {

      const send = (text: string) => {
        // SSE 格式：每行以 "data: " 開頭，以 "\n\n" 結尾
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`))
      }

      try {
        // Step 1：呼叫 MCP Server 搜尋相關知識
        send('[搜尋知識庫中...]\n\n')
        const context = await callMcpTool('search_knowledge_base', { query: message })

        // Step 2：呼叫 OpenAI，把知識庫內容當作 context
        const apiKey = process.env.OPENAI_API_KEY
        if (!apiKey) throw new Error('未設定 OPENAI_API_KEY')

        const systemPrompt = `你是一個資料科學專題助理。
請根據以下知識庫內容回答使用者的問題。
如果需要顯示流程圖，請用 \`\`\`mermaid 語法。
如果需要顯示圖表數據，請用 \`\`\`chart-json 語法，格式為 Chart.js data 物件。

知識庫內容：
${context}

請用繁體中文回答，語氣親切。`

        const openaiRes = await fetch('https://api.openai.com/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({
            model: 'gpt-4o-mini',
            stream: true,
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: message },
            ],
          }),
        })

        if (!openaiRes.ok) {
          const err = await openaiRes.text()
          throw new Error(`OpenAI API 錯誤：${err}`)
        }

        // Step 3：逐 token 轉送給前端
        const reader = openaiRes.body!.getReader()
        const dec = new TextDecoder()

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = dec.decode(value)
          for (const line of chunk.split('\n')) {
            if (!line.startsWith('data: ')) continue
            const data = line.slice(6)
            if (data === '[DONE]') break

            try {
              const parsed = JSON.parse(data)
              const token = parsed.choices?.[0]?.delta?.content
              if (token) send(token)
            } catch {
              // 忽略解析失敗的行
            }
          }
        }

      } catch (err) {
        const msg = err instanceof Error ? err.message : '未知錯誤'
        send(`\n\n> ⚠️ 錯誤：${msg}`)
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
