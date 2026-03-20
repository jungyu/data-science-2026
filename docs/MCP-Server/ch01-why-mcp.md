# 第一章：你的 AI 不會用工具

## ──為什麼 Claude 說謊？

---

```
┌─────────────────────────────────────────────────────────┐
│  你：「我的 Supabase 裡有幾筆使用者資料？」              │
│                                                         │
│  Claude：「根據一般 SaaS 應用的規模，你大概有            │
│            1,000 到 5,000 筆使用者資料。」               │
│                                                         │
│  你：「......它在亂猜。」                                │
└─────────────────────────────────────────────────────────┘
```

小明是一個資料科學系的學生。他花了三個月建了一個 Supabase 資料庫，裡面有使用者表、交易記錄表、產品表。他每天都用 Claude 幫他分析資料、寫 Python、解 Bug。

有一天，他問 Claude：「我的 Supabase 裡有幾筆使用者資料？」

Claude 回答：「根據一般 SaaS 應用的規模，你的資料庫大概有 1,000 到 5,000 筆使用者資料。」

小明盯著螢幕，沉默了五秒。他的資料庫裡只有 23 筆測試資料。

Claude 沒有在說謊。Claude 根本就**看不到**他的資料庫。

這就是問題的核心。

---

## 1.1 AI 的孤島困境

**大型語言模型（LLM）** 是一個關在語言孤島上的天才。

它讀過幾乎所有人類寫過的文字。它能寫程式、分析資料、翻譯語言、解釋量子力學。但是當你問它「現在幾點？」或「我的資料庫有幾筆資料？」，它只能——猜。

因為 LLM 的本質是：

```
輸入文字 → 預測下一個 token → 輸出文字
```

它的「知識」全部來自訓練資料的截止日期之前。訓練完成之後，它就被**凍結**了。它不知道：

- 現在幾點幾分
- 你的資料庫裡有什麼
- 今天的股票價格
- 你昨天推送的程式碼有沒有錯誤
- 你剛才上傳的 CSV 檔案內容（除非你把它貼到對話框裡）

> **重要**：LLM 不是懶，也不是壞。它真的沒有辦法。就像一個天才學者被鎖在圖書館裡——圖書館裡的書都讀完了，但圖書館的門通到外面世界的那把鑰匙，一直不在他手上。

這個問題有一個名字：**知識截止問題（Knowledge Cutoff Problem）** 和**行動能力缺失（Lack of Action Capability）**。

---

### 腦力激盪 🧠

> 如果沒有 MCP，讓 Claude 查你的 Supabase 資料庫需要做什麼？

花 60 秒思考看看。你會怎麼讓 Claude 知道你的資料庫裡有什麼？

<details>
<summary>點開看參考答案</summary>

沒有 MCP 的解法，你可能會：

1. **手動貼資料**：把 SELECT 查詢結果複製貼上到對話框
2. **寫一個 Python 腳本**：先查資料庫，把結果儲存成字串，再貼給 Claude
3. **客製化 Function Calling**：為這個特定的 App 寫一套工具整合
4. **上傳 CSV**：把資料匯出成 CSV 上傳

每一種方法都很麻煩，而且每換一個 AI 應用就要重做一次。

</details>

---

## 1.2 Function Calling vs MCP — 你的工具只能用一次嗎？

「等等，」你可能會說，「OpenAI 不是有 Function Calling 嗎？GPT-4 可以呼叫工具啊！」

對。**Function Calling** 是第一個讓 AI 模型能夠「呼叫工具」的機制。你告訴 GPT：「你有一個工具叫 `get_database_count()`，你可以呼叫它。」然後 GPT 會在回應裡說：「我想呼叫這個工具」，你的程式碼去執行，把結果回傳給 GPT，GPT 再繼續回答。

這個設計有一個根本的問題：

```
Function Calling 的世界：

你的 App A ─→ 為 App A 寫的工具 A（只有 App A 能用）
你的 App B ─→ 為 App B 寫的工具 B（只有 App B 能用）
你的 App C ─→ 為 App C 寫的工具 C（只有 App C 能用）

結果：每個 App 都要重新造輪子
```

你在 App A 裡辛苦寫好的「查詢 Supabase」工具，在 App B 裡根本用不了。你要換一個 AI 框架？重寫。你要讓同事的 App 也能查你的資料庫？重寫。

**MCP（Model Context Protocol）** 的想法完全不同：

```
MCP 的世界：

你的 App A ─┐
你的 App B ─┤→ MCP Server → 你的服務（一次定義，到處使用）
你的 App C ─┘

任何支援 MCP 的 AI 客戶端都能呼叫同一個 MCP Server
```

**MCP** 是 Anthropic 在 2024 年 11 月開源的協議。它的設計理念是：**讓工具定義和 AI 應用解耦**。你寫一個 MCP Server，定義你的工具。任何支援 MCP 的客戶端（Claude Desktop、Cursor、Zed、你自己寫的 App）都能使用這些工具。

> **提醒**：MCP 不是 Anthropic 專屬技術。它是一個開放協議，OpenAI、Google 等都已宣佈支援。就像 HTTP 不是某家公司的，MCP 是 AI 工具整合的通用標準。

---

### 腦力激盪 🧠

> Tools 和 Resources 都能讓 AI 讀取資料，差在哪？

先想一下，我們在下一節會回答這個問題。

---

## 1.3 三個核心原語

MCP 定義了三種「原語（Primitives）」——這是你能在 MCP Server 裡放的三種東西：

### 原語一：Tools（工具）— 動詞，有副作用

**Tools** 是讓 AI 能夠**執行動作**的能力。

- `search_database(query)` — 查詢資料庫
- `send_email(to, subject, body)` — 寄送電子郵件
- `create_ticket(title, description)` — 建立工單
- `run_sql(query)` — 執行 SQL

Tools 的特點：
- 通常需要**參數**
- 可能有**副作用**（寫入、刪除、發送）
- AI 決定何時呼叫、傳什麼參數
- 回傳**執行結果**

### 原語二：Resources（資源）— 名詞，唯讀資料

**Resources** 是讓 AI 能夠**讀取結構化資料**的能力。

- `db://users/schema` — 使用者資料表的欄位定義
- `config://app-settings` — 應用程式設定
- `file://report-2024.csv` — 一份 CSV 報告

Resources 的特點：
- 有**固定或模板化的 URI**（像網址）
- **唯讀**，不應該有副作用
- 像瀏覽檔案系統一樣可以**瀏覽和列出**
- AI 或使用者可以主動**訂閱**更新

> **重要**：Tools 和 Resources 都能讀資料，但設計意圖不同。
>
> Tools 是「我要執行一個動作，資料是副產品」。
> Resources 是「我只是要讀這份資料，不會改變任何東西」。
>
> 就像 HTTP 的 POST 和 GET：功能上都能傳資料，但語意不同。

### 原語三：Prompts（提示範本）— 標準化的問法

**Prompts** 是讓你能夠把**常用的提示詞模板**打包進 MCP Server 的能力。

- `analyze_sales_trend(month)` — 分析銷售趨勢的標準提示詞
- `write_commit_message(diff)` — 根據 diff 寫 commit message 的提示詞
- `summarize_meeting(transcript)` — 會議記錄摘要提示詞

Prompts 的特點：
- 在 Claude Desktop 的「/」選單裡出現
- 可以帶**動態參數**
- **標準化**你的 AI 工作流程
- 讓團隊成員用**一致的方式**和 AI 互動

---

```
三個原語的關係：

┌──────────────────────────────────────────────────┐
│                  MCP Server                       │
│                                                  │
│   Tools     ──→ 執行動作（搜尋、寫入、呼叫 API） │
│   Resources ──→ 讀取資料（設定、Schema、報告）   │
│   Prompts   ──→ 標準提示詞範本（分析、摘要）     │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 1.4 Client-Server 架構：資料怎麼流動的？

理解 MCP 的架構，你需要認識四個角色：

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Host（主機程式）                                              │
│   例如：Claude Desktop、Cursor、你寫的 Python App              │
│   ┌─────────────────┐                                           │
│   │   MCP Client    │ ←─── 內建在 Host 裡，管理連線            │
│   └────────┬────────┘                                           │
│            │  MCP 協議（JSON-RPC over stdio 或 HTTP）           │
│            ↓                                                    │
│   ┌─────────────────┐                                           │
│   │   MCP Server    │ ←─── 你寫的程式！                        │
│   │                 │                                           │
│   │  你的 Tools     │                                           │
│   │  你的 Resources │                                           │
│   │  你的 Prompts   │                                           │
│   └────────┬────────┘                                           │
│            │                                                    │
│            ↓                                                    │
│   你的服務（Supabase、Qdrant、外部 API...）                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

資料流的完整路徑：

1. **使用者**問 Claude：「我的資料庫有幾筆使用者資料？」
2. **Claude（LLM）** 判斷：我需要呼叫 `count_users` 這個工具
3. **Host（Claude Desktop）** 透過 **MCP Client** 發送工具呼叫請求
4. **MCP Server** 接收請求，執行 `count_users()` 函式
5. 函式查詢 **Supabase**，得到「23」
6. 結果原路回傳給 **Claude**
7. **Claude** 回答：「你的資料庫目前有 23 筆使用者資料。」

> **提醒**：注意 Claude（LLM）本身永遠不會直接碰你的資料庫。它只能看到工具回傳的**字串結果**。你的 MCP Server 才是真正做事的那個。這個設計讓安全控制變得很容易——你可以在 MCP Server 裡加上驗證、稽核、速率限制。

---

## 1.5 兩種傳輸協議：資料怎麼傳？

MCP 客戶端和伺服器之間要傳資料，需要一個**傳輸層（Transport）**。主要有兩種：

### 第一種：stdio（標準輸入輸出）— 本機最簡單

```
Claude Desktop
    │
    │  fork/spawn subprocess
    ↓
Python process（你的 server.py）
    │
    │  stdin  ← JSON-RPC 請求
    │  stdout → JSON-RPC 回應
    │
    ↓
你的服務
```

**stdio** 的工作方式：Claude Desktop 直接**啟動**你的 Python 程式作為子程序，然後透過標準輸入（stdin）送請求，從標準輸出（stdout）讀回應。

優點：
- 最簡單，不需要網路
- 安全（在本機，不開任何 port）
- 延遲最低

缺點：
- 只能本機使用，不能多人共用
- 每個用戶都需要在自己的機器上安裝

### 第二種：Streamable HTTP — 現代雲端標準

```
任何 MCP 客戶端
    │
    │  HTTP POST（帶 Accept: text/event-stream）
    ↓
你的 MCP Server（監聽 port 3000）
    │
    │  HTTP 回應（可串流）
    ↓
你的服務
```

**Streamable HTTP** 是 MCP 規範在 2025 年 3 月確立的現代傳輸標準。它讓 MCP Server 變成一個可以透過網路訪問的服務。

優點：
- 可以部署到雲端，多人共用
- 支援 HTTP/2、可水平擴展
- 無狀態設計，更容易運維

缺點：
- 需要處理網路、認證等問題
- 比 stdio 複雜一些

> **重要**：你可能在舊文章裡看到 **SSE（Server-Sent Events）** 傳輸。SSE 是 MCP 的第二代傳輸協議，在 Docker 環境中很常見。但請注意：**SSE 已在 MCP 規範 v2025-03-26 中被標記為棄用（Deprecated）**，被 Streamable HTTP 取代。新專案請直接用 Streamable HTTP。本課程的 Docker 章節會展示 SSE 以相容現有環境，但雲端部署會使用 Streamable HTTP。

---

```
傳輸協議速查表：

場景              | 協議             | 狀態
------------------|------------------|------------------
個人開發、測試    | stdio            | ✅ 推薦
本機 Claude Desktop| stdio           | ✅ 推薦
現有 Docker 環境  | SSE              | ⚠️  已棄用但可用
雲端生產部署      | Streamable HTTP  | ✅ 現代標準
```

---

## 動手做：安裝 MCP 並用 Inspector 探索

讓我們馬上把手弄髒。這個 Lab 不需要你自己寫伺服器——我們先用一個現成的 MCP Server 來感受一下 MCP 是什麼感覺。

### 步驟一：安裝 MCP CLI

```bash
# 安裝官方 MCP Python SDK（包含 FastMCP 和 CLI 工具）
pip install "mcp[cli]"

# 確認安裝成功
mcp --version
```

> **重要**：套件名稱是 `mcp[cli]`，不是 `fastmcp`。雖然 FastMCP 原本是獨立套件，但它已經被合併進官方 MCP SDK。安裝 `mcp[cli]` 就可以用 FastMCP，而且還附贈 `mcp dev`（Inspector）和 `mcp run` 等 CLI 工具。

### 步驟二：建立一個最小的 MCP Server

```python
# hello_mcp.py — 你的第一個 MCP Server（10 行）
from mcp.server.fastmcp import FastMCP

# 建立 MCP Server 實例，給它一個名字
mcp = FastMCP("我的第一個 MCP Server")

@mcp.tool()
def say_hello(name: str) -> str:
    """向指定的人打招呼。當使用者要求問候某人時呼叫此工具。"""
    return f"你好，{name}！歡迎使用 MCP！"

if __name__ == "__main__":
    # stdio 模式執行（適合本機開發）
    mcp.run()
```

### 步驟三：用 MCP Inspector 測試

```bash
# 啟動 MCP Inspector（官方 SDK 內建的測試工具）
mcp dev hello_mcp.py
```

執行後，你會看到：

```
MCP Inspector 啟動中...
在瀏覽器開啟：http://localhost:5173
伺服器已連線：我的第一個 MCP Server
```

在瀏覽器的 Inspector 介面裡：

1. 點選左側的「Tools」標籤
2. 你會看到 `say_hello` 工具，還有它的參數 Schema
3. 在 `name` 欄位輸入你的名字，按「Call Tool」
4. 觀察右側的 JSON 請求和回應

恭喜！你剛才做的事，就是 Claude Desktop 在幕後做的事——只是 Claude Desktop 是用 LLM 的判斷力來決定什麼時候呼叫工具、傳什麼參數。

### 步驟四：探索工具的 Schema

在 Inspector 裡，找到「Schema」標籤，你會看到：

```json
{
  "name": "say_hello",
  "description": "向指定的人打招呼。當使用者要求問候某人時呼叫此工具。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string"
      }
    },
    "required": ["name"]
  }
}
```

這個 JSON Schema 就是 Claude 在決定「要不要呼叫這個工具」、「要傳什麼參數」時參考的資訊。**description 對 AI 的重要性不亞於 name**——這是第三章的重點。

---

## 重點回顧 📌

```
┌─────────────────────────────────────────────────────┐
│                  第一章重點回顧                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  • LLM 是語言孤島：它只能看到你餵給它的文字，      │
│    無法主動存取外部系統                             │
│                                                     │
│  • MCP = Model Context Protocol，開放的 AI 工具    │
│    整合協議，一次定義工具，多個 AI App 都能使用     │
│                                                     │
│  • 三個原語：                                       │
│    - Tools：執行動作（有副作用）                    │
│    - Resources：讀取結構化資料（唯讀）              │
│    - Prompts：標準化提示詞範本                      │
│                                                     │
│  • 架構：Host → MCP Client → MCP Server → 你的服務 │
│                                                     │
│  • 傳輸協議：                                       │
│    - stdio：本機最簡單                              │
│    - Streamable HTTP：現代雲端標準                  │
│    - SSE：已棄用（v2025-03-26），勿用於新專案       │
│                                                     │
│  • 安裝：pip install "mcp[cli]"                     │
│  • 測試：mcp dev server.py                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 常見問題 FAQ

**Q1：MCP 和 LangChain 的工具有什麼不同？**

LangChain 的工具是**框架內**的概念——你用 LangChain 建的工具，只能在 LangChain 的 Agent 裡用。MCP 是一個**獨立的開放協議**，任何遵守 MCP 規範的客戶端都能用你的工具。就像 REST API 可以被任何 HTTP 客戶端呼叫，MCP Server 可以被任何 MCP 客戶端呼叫。

**Q2：我需要 Claude Desktop 才能用 MCP 嗎？**

不需要。Claude Desktop 只是最常見的 MCP 客戶端（Host）之一。你可以用 Cursor、Zed、自己寫的 Python 程式、或任何實作了 MCP 客戶端的應用程式。甚至可以用 `mcp` 套件裡的 `ClientSession` 類別，寫一個程式來直接呼叫你的 MCP Server。

**Q3：MCP Server 一定要用 Python 寫嗎？**

不需要。MCP 是一個協議規範，官方有 Python SDK 和 TypeScript SDK。社群也有 Go、Rust、Java 等語言的實作。本課程用 Python，因為資料科學領域 Python 最普遍，而且官方 Python SDK 的 FastMCP 讓開發體驗最簡單。

**Q4：MCP 和 RAG 是競爭關係嗎？**

不是，它們是互補的。**RAG（Retrieval-Augmented Generation）** 是一種讓 AI 能從向量資料庫中搜尋相關文件的技術。**MCP** 是一個讓 AI 能夠執行工具呼叫的協議框架。你可以把 RAG 的搜尋功能封裝成一個 MCP Tool——這正是本課程後面章節要做的事！

---

## 課後練習

### ⭐ 基礎練習：安裝並探索

1. 安裝 `mcp[cli]` 套件
2. 建立 `hello_mcp.py`（使用本章的範例）
3. 用 `mcp dev hello_mcp.py` 啟動 Inspector
4. 在 Inspector 裡呼叫 `say_hello` 工具三次，傳入不同的 `name` 值
5. 截圖 Inspector 的介面，記錄你看到的 JSON Schema

### ⭐⭐ 進階練習：設計你的工具清單

想像你要為你的**期末專案**建立一個 MCP Server。寫下 3 個你希望有的工具：

對每個工具，回答：
- 工具名稱（英文，snake_case）
- 它應該做什麼（一句話描述）
- 需要哪些參數？型別是什麼？
- 回傳什麼？
- 它是 Tool 還是 Resource？為什麼？

### ⭐⭐⭐ 挑戰練習：分析開源 MCP Server

在 GitHub 上找 2 個開源的 MCP Server（搜尋 `awesome-mcp-servers` 或 `mcp-server` 主題標籤）。對每個 Server：

1. 它暴露了哪些 Tools？哪些 Resources？
2. 工具的 description 寫得清楚嗎？AI 能看懂嗎？
3. 它使用哪種傳輸協議？
4. 你認為它的設計有什麼優點或缺點？

寫一份 200-300 字的比較分析。

---

## 下一章預告

你已經理解了 MCP 是什麼、為什麼它存在。現在是時候打造你自己的第一個工具了。

在第二章，我們會從最簡單的例子開始：讓 Claude 知道現在幾點。然後一步一步擴展到呼叫真實的外部 API。你會看到 FastMCP 的裝飾器魔法，以及怎麼把你的 MCP Server 連接到 Claude Desktop。

→ [第二章：打造你的第一個工具](./ch02-first-tool.md)
