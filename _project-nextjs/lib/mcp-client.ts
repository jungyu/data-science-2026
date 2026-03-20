/**
 * MCP Server HTTP 客戶端
 *
 * 開發模式：MCP_SERVER_URL=http://localhost:3000
 * Docker 模式：MCP_SERVER_URL=http://mcp-server:3000（容器內網路）
 */

const MCP_URL = process.env.MCP_SERVER_URL || 'http://localhost:3000'

/**
 * 呼叫 MCP Server 上的工具
 * @param toolName  工具名稱（對應 MCP Server 定義的 tool）
 * @param args      工具參數
 * @returns         工具回傳的文字內容
 */
export async function callMcpTool(
  toolName: string,
  args: Record<string, unknown>
): Promise<string> {
  try {
    const res = await fetch(`${MCP_URL}/tools/${toolName}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(args),
      // 10 秒超時
      signal: AbortSignal.timeout(10_000),
    })

    if (!res.ok) {
      console.warn(`MCP 工具 [${toolName}] 回傳 ${res.status}，使用空白 context`)
      return ''
    }

    const data = await res.json()
    // MCP Server 回傳格式：{ content: string } 或直接 string
    return typeof data === 'string' ? data : (data.content ?? JSON.stringify(data))

  } catch (err) {
    // MCP Server 未啟動時，不中斷 AI 回答，只是沒有外部知識
    console.warn(`MCP Server 連線失敗 (${MCP_URL})，將在無 context 下回答`)
    return ''
  }
}
