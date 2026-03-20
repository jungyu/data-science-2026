# Module A｜MCP Server — 把 RAG 包裝成工具

> **前置條件**：已完成 ch01–ch06（RAG Pipeline），Qdrant 中已有向量資料
>
> **學習成果**：自架一個 MCP Server，讓 Claude Desktop 和 Next.js Dashboard 都能呼叫你的 RAG

---

## 為什麼需要 MCP Server？

你已經有了一個 RAG pipeline，它能回答問題。但問題是：

```
現狀：
  你 → [寫 Python 腳本] → RAG → 答案

目標：
  Claude Desktop → [自動呼叫工具] → RAG → 答案
  Next.js 側欄   → [HTTP 請求]    → RAG → 答案
```

**MCP（Model Context Protocol）** 是 Anthropic 制定的開放協議，讓 AI 模型能以標準化方式呼叫外部工具。你只需要定義好「工具」，Claude Desktop 就能在對話中自動決定何時呼叫它。

### 腦力激盪

> **想一想**：如果沒有 MCP，要讓 Claude 用你的 RAG，你需要做什麼？
> 為什麼「讓 AI 自己決定何時搜尋知識庫」比「每次手動貼上相關文件」更好？

---

## MCP 協議基本概念

```
┌─────────────────────────────────────────────────┐
│  MCP 的三種能力（本課只用 Tools）                  │
│                                                   │
│  Tools     → 讓 AI 呼叫函式（我們要做的）          │
│  Resources → 讓 AI 讀取資源（檔案、URL）           │
│  Prompts   → 預設提示範本                         │
└─────────────────────────────────────────────────┘
```

### 工具（Tool）的結構

```python
Tool(
    name="search_knowledge_base",     # 工具名稱（AI 看到的）
    description="搜尋向量知識庫...",   # AI 決定何時用的依據 ← 很重要！
    inputSchema={                      # 參數規格（JSON Schema）
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜尋關鍵字"},
        },
        "required": ["query"],
    },
)
```

> **關鍵**：`description` 寫得好不好，直接決定 AI 會不會在對的時機呼叫工具。

---

## A1｜了解專案中的 MCP Server

### 檔案位置

```
_project-fullstack/
└── mcp-server/
    ├── server.py          ← 主程式（你主要修改這裡）
    ├── requirements.txt   ← Python 套件
    └── Dockerfile         ← 打包成容器
```

### server.py 架構

```
單一 FastAPI app，port 3000
├── GET  /sse           → SSE transport（Claude Desktop 連線）
├── POST /messages      → SSE 配合端點
├── POST /tools/{name}  → REST API（Next.js Dashboard 用）
└── GET  /health        → 健康檢查
```

**為什麼一個 port 兩種用途？**

Claude Desktop 使用 SSE（Server-Sent Events）協議——它保持長連線，AI 工具呼叫透過這個通道來回傳遞。Next.js 則用普通的 HTTP POST，呼叫完就斷線。兩種協議都掛在 port 3000，路徑不同。

---

## A2｜自架 MCP Server

### 啟動（開發模式）

```bash
cd _project-fullstack/mcp-server

# 建立虛擬環境
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt

# 設定環境變數
cp ../.env.example .env
# 填入 QDRANT_URL, OPENAI_API_KEY 等

# 啟動
python server.py
```

你應該看到：
```
DS MCP Server 啟動中（port 3000）
  /sse          → Claude Desktop SSE transport
  /tools/<name> → Next.js REST API
  /health       → 健康檢查
```

### 驗收：呼叫健康檢查

```bash
curl http://localhost:3000/health
# 應回傳：
# {
#   "status": "ok",
#   "qdrant": "http://localhost:6333",
#   "supabase": false,
#   "tools": ["search_knowledge_base", "query_supabase"]
# }
```

### 驗收：直接測試工具

```bash
curl -X POST http://localhost:3000/tools/search_knowledge_base \
  -H "Content-Type: application/json" \
  -d '{"query": "你的測試問題"}'

# 應回傳：
# { "content": "...(知識庫搜尋結果)..." }
```

---

## A3｜定義你的工具

**這是你在 Module A 最重要的工作。** 起始模板有兩個預設工具，你需要根據自己的專題調整或新增。

### 修改現有工具

開啟 `mcp-server/server.py`，找到工具函式：

```python
def search_knowledge_base(
    query: str,
    collection: str = "knowledge",  # ← 改成你的 Qdrant collection 名稱
    top_k: int = 5,
) -> str:
    """搜尋向量知識庫，回傳最相關的文件片段。"""
    # ... 實作不需動，調整參數預設值即可
```

```python
def query_supabase(
    table: str,
    filters: str = "{}",
    limit: int = 20,
    select: str = "*",
) -> str:
    """查詢 Supabase 資料表，回傳 JSON 格式結果。"""
    # ... 實作不需動
```

### 新增自訂工具

在 `TOOLS` 和 `TOOL_SCHEMAS` 登記即可：

```python
# 1. 撰寫工具函式
def get_statistics(metric: str, period: str = "monthly") -> str:
    """
    取得指定指標的統計摘要。

    Args:
        metric: 指標名稱（如 "sales", "users"）
        period: 統計週期（"daily" | "weekly" | "monthly"）
    """
    # 你的實作：查 Supabase 或計算本地資料
    data = supabase_client.table("metrics") \
        .select("date, value") \
        .eq("metric", metric) \
        .execute().data

    if not data:
        return f"找不到 {metric} 的資料"

    values = [row["value"] for row in data]
    return f"{metric}（{period}）：平均 {sum(values)/len(values):.2f}，最大 {max(values)}，最小 {min(values)}"


# 2. 登記到 TOOLS 字典
TOOLS = {
    "search_knowledge_base": search_knowledge_base,
    "query_supabase":        query_supabase,
    "get_statistics":        get_statistics,      # ← 新增這行
}

# 3. 登記到 TOOL_SCHEMAS（讓 Claude 知道這個工具存在）
TOOL_SCHEMAS = [
    # ... 現有工具 ...
    Tool(
        name="get_statistics",
        description="取得指定指標的統計摘要，適合在使用者問『平均』『趨勢』『最大最小值』時呼叫",
        inputSchema={
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "指標名稱，例如 sales, users, revenue",
                },
                "period": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly"],
                    "default": "monthly",
                },
            },
            "required": ["metric"],
        },
    ),
]
```

> **寫好 description 的技巧**：
> 描述「什麼情況下應該用這個工具」，而不只是「工具做什麼」。
> 好：`"適合在使用者問趨勢、平均值、最大最小值時呼叫"`
> 差：`"回傳統計資料"`

---

## A4｜整合進 docker-compose

開發完成後，讓 MCP Server 在 docker 環境中運行：

```bash
cd _project-fullstack

# 確認 .env 已填妥
cat .env

# 只啟動 qdrant + mcp-server（還不需要 nginx / crawler）
docker compose up -d qdrant mcp-server

# 查看啟動日誌
docker compose logs mcp-server -f
```

驗收：

```bash
# 從宿主機呼叫容器內的 MCP Server
curl http://localhost:3000/health
```

---

## A5｜連接 Claude Desktop

### 設定 claude_desktop_config.json

**macOS** 路徑：`~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows** 路徑：`%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ds-mcp": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

儲存後**重新啟動 Claude Desktop**。

### 驗收對話

開啟 Claude Desktop，在對話中輸入：

```
請搜尋知識庫中關於「[你的專題主題]」的相關資料
```

Claude 應該會顯示「使用工具 search_knowledge_base」，然後回答來自你知識庫的內容。

如果在側邊欄看到鎚子圖示（🔨），代表工具連線成功。

> **常見問題**：Claude Desktop 顯示「無法連接工具」？
> 1. 確認 `python server.py` 或 `docker compose up mcp-server` 正在執行
> 2. 確認 port 3000 沒有被其他程式佔用：`lsof -i :3000`
> 3. 確認 `claude_desktop_config.json` 語法正確（用 JSON validator 檢查）

---

## 重點回顧

```
╔══════════════════════════════════════════════════════════╗
║  Module A 核心概念                                        ║
╠══════════════════════════════════════════════════════════╣
║  • MCP Tool = 名稱 + description + inputSchema + 函式    ║
║  • description 決定 AI 呼叫時機，要寫「何時用」不只是「做什麼」║
║  • 單一 port 3000：/sse（Claude）、/tools（Next.js）      ║
║  • 新增工具 3 步驟：寫函式 → 加入 TOOLS → 加入 TOOL_SCHEMAS ║
║  • docker compose up qdrant mcp-server 先驗收再整合       ║
╚══════════════════════════════════════════════════════════╝
```

---

## 課後練習

**⭐ 基本（必要）**
1. 啟動 MCP Server，成功呼叫 `GET /health` 和 `POST /tools/search_knowledge_base`
2. 修改 `collection` 預設值，指向你的 Qdrant collection 名稱
3. 在 Claude Desktop 完成一次成功的工具呼叫

**⭐⭐ 進階**
4. 新增一個自訂工具（例如：`get_summary`，用 AI 摘要某個主題的知識庫內容）
5. 讓 `query_supabase` 查你自己的資料表，並在 Claude 中測試

**⭐⭐⭐ 挑戰**
6. 新增一個 `generate_chart_data` 工具，讓它查詢資料後回傳 Chart.js 格式的 JSON，在 Next.js Dashboard 動態更新圖表

---

## 常見問題

**Q：`mcp` 套件安裝失敗？**
A：確認 Python >= 3.11，嘗試 `pip install "mcp>=1.3.0"`。若在 docker 中出錯，看 `docker compose logs mcp-server`。

**Q：工具呼叫成功但結果是空的？**
A：Qdrant 中可能還沒有資料。先確認 `curl http://localhost:6333/dashboard` 能打開，且你的 collection 存在。

**Q：Next.js 呼叫 `/tools/search_knowledge_base` 但 MCP Server 沒有啟動怎麼辦？**
A：`mcp-client.ts` 設計為連線失敗 silent fail，AI 仍可回答，只是沒有知識庫內容。這是刻意的設計，讓開發過程不會因 MCP Server 未啟動而中斷。

**Q：我能在同一個 MCP Server 加超過 10 個工具嗎？**
A：技術上可以，但不建議超過 5–7 個。工具太多時 Claude 容易選錯。建議把功能相關的工具合併成一個（用參數區分），保持工具列表精簡。

---

> 完成 Module A 後，繼續 **Module B｜Dashboard + AI 側欄**，把 MCP Server 接到視覺化介面。
