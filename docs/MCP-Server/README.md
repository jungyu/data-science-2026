# MCP Server 完全實戰課程

> **O'Reilly Head First 風格 · 繁體中文 · Python + FastMCP**
>
> 本課程是 **MCP（Model Context Protocol）的完整概念課**，不限於 RAG 情境。
> 完成後你能設計、測試並部署一個生產就緒的 MCP Server。

---

## 什麼是 MCP？

MCP 是 Anthropic 於 2024 年發布的開放協議，讓 AI 模型能以標準化方式呼叫外部工具、讀取資料、使用提示範本。

```
沒有 MCP：Claude 是一座孤島，只會說話
有了 MCP：Claude 能查資料庫、搜尋向量庫、執行計算、讀取檔案
```

---

## 學習路徑

```
Ch01           Ch02           Ch03           Ch04           Ch05
─────          ─────          ─────          ─────          ─────
你的 AI        打造第一       工具設計        Resources      測試·安全
不會用工具  →  個工具     →  的藝術      →  與 Prompts  →  部署
（為什麼）     （怎麼做）     （做對了嗎）   （其他原語）    （交出去）
```

---

## 課程大綱

| 章節 | 標題 | 核心技術 | 難度 | 預計時間 |
|------|------|----------|------|----------|
| [Ch01](ch01-why-mcp.md) | 你的 AI 不會用工具 | MCP 架構、三個原語 | ⭐ | 2 小時 |
| [Ch02](ch02-first-tool.md) | 打造你的第一個工具 | FastMCP、stdio、JSON Schema | ⭐⭐ | 3 小時 |
| [Ch03](ch03-tool-design.md) | 工具設計的藝術 | Description 工程、MCP Inspector | ⭐⭐⭐ | 3 小時 |
| [Ch04](ch04-resources-prompts.md) | Resources 與 Prompts | URI Template、MIME、Prompt 庫 | ⭐⭐⭐ | 3 小時 |
| [Ch05](ch05-test-security-deploy.md) | 測試、安全、部署 | Inspector、Streamable HTTP、Docker | ⭐⭐⭐⭐ | 4 小時 |

---

## 技術選擇

**語言**：Python 3.11+
**框架**：`mcp` 官方 SDK（FastMCP 已內建）

```python
from mcp.server.fastmcp import FastMCP  # 官方 SDK 內建，無需額外安裝

mcp = FastMCP("my-server")

@mcp.tool()
def search(query: str) -> str:
    """搜尋知識庫，回傳最相關的內容"""
    ...
```

**為什麼選 Python 而非 TypeScript？**

- 70% 的生產 MCP Server 採用 FastMCP 模式（Python）
- 與 RAG 課程（qdrant-client、openai）同語言，直接複用
- 裝飾器 API 比 TypeScript 的 zod Schema 直觀 5 倍
- 官方 SDK 在 Transport 支援上已與 TypeScript 完全對齊

---

## 環境設定

```bash
# Python 3.11+
pip install "mcp[cli]"     # 含 FastMCP + MCP Inspector CLI

# 驗證安裝
mcp version
mcp dev --help
```

**Claude Desktop 設定**（`~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/絕對路徑/server.py"]
    }
  }
}
```

---

## 先決知識

- Python 基礎（函式、型別提示、裝飾器概念即可）
- 用過 Claude Desktop（知道對話是什麼）
- 不需要：網路協議背景、TypeScript、深度學習

---

## 與 RAG 課程的關係

| | RAG Module A | 本課程 |
|--|-------------|-------|
| **定位** | 在 RAG 情境下快速跑起來 | MCP 的完整概念與設計 |
| **Tools** | 2 個（search + query） | 從設計到測試的完整流程 |
| **Resources** | 未涵蓋 | Ch04 完整說明 |
| **Prompts** | 未涵蓋 | Ch04 完整說明 |
| **測試** | curl 驗收 | MCP Inspector + 單元測試 |
| **安全** | 未涵蓋 | Ch05 完整說明 |
| **部署** | Docker SSE | stdio / SSE / Streamable HTTP 三種 |

---

*最後更新：2026-03*
