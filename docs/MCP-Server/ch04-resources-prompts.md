# 第四章：Resources 與 Prompts

## ──讓 Claude 自己去翻你的資料

---

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  對話一：（沒有 Resources）                                 │
│                                                             │
│  你：「幫我查一下 orders 資料表裡的資料」                   │
│  Claude：「你的 orders 資料表有哪些欄位？」                 │
│  你：「有 id、user_id、amount、created_at...」              │
│  Claude：「好，那 user_id 是整數還是字串？」                │
│  你：「整數。還有外鍵指向 users 表...」                     │
│  Claude：「users 表有哪些欄位？」                           │
│  你：[崩潰]                                                 │
│                                                             │
│  對話二：（有 Resources）                                   │
│                                                             │
│  你：「幫我查一下 orders 資料表裡的資料」                   │
│  Claude 直接去讀 db://tables/orders/schema → 知道欄位了    │
│  Claude：「orders 表有以下欄位：...                         │
│            我來幫你查詢...」                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

你已經是 Tools 的高手了。但你的同事小美提出了一個問題：

「每次開新對話，我都要花 5 分鐘告訴 Claude 我們的資料庫結構。有沒有辦法讓 Claude 自己去查？」

有。這就是 **Resources** 存在的理由。

而你的另一個同事小強說：「我每次都要用很長的提示詞告訴 Claude 怎麼做數據分析，每次都得重打。能不能打包起來讓大家共用？」

也有。這是 **Prompts** 的功能。

本章前三分之二講 Resources，後三分之一講 Prompts。

---

# PART 1：Resources

## 4.1 Tools vs Resources：什麼時候用哪個？

這個問題困擾了很多 MCP 新手。工具和資源都能讓 AI 獲取資料，差別到底在哪？

```
決策框架：

                    ┌──────────────────────────────┐
                    │   這個操作會改變任何東西嗎？  │
                    │   （寫入、刪除、發送、觸發）  │
                    └──────────────┬───────────────┘
                              是 ↓        ↓ 否
                    ┌─────────────┐  ┌────────────────────────┐
                    │    Tool     │  │  它是結構化、可瀏覽的  │
                    │（有副作用）  │  │  靜態或半靜態資料嗎？  │
                    └─────────────┘  └────────────┬───────────┘
                                              是 ↓        ↓ 否
                                   ┌──────────────┐  ┌─────────┐
                                   │   Resource   │  │  Tool   │
                                   │ （唯讀資料） │  │（需要計算）│
                                   └──────────────┘  └─────────┘
```

用更直白的語言說：

```
用 Tool 當：
  ✅ 需要執行動作（查資料庫、呼叫 API、計算結果）
  ✅ 有副作用（寫入、刪除、發送）
  ✅ 需要動態參數來決定要做什麼
  ✅ 結果每次都不同，需要即時計算

用 Resource 當：
  ✅ 純粹是讀取既有的資料
  ✅ 資料結構相對穩定（不常變動）
  ✅ 使用者（或 AI）可能想「瀏覽」這份資料
  ✅ 類似「文件」、「設定」、「Schema」這樣的東西
```

實際範例：

```
資料庫 Schema 定義    → Resource（唯讀，不常變）
執行一個 SQL 查詢     → Tool（動態、有副作用）
應用程式設定          → Resource（唯讀設定檔）
更新設定值            → Tool（會修改設定）
Qdrant 的 collection 列表 → Resource（可瀏覽的目錄）
在 Qdrant 搜尋相似向量   → Tool（需要計算，動態結果）
```

> **重要**：Resources 是給「**名詞**」用的，Tools 是給「**動詞**」用的。
>
> Resources 代表「什麼東西存在於你的系統裡」。
> Tools 代表「你的系統能做什麼事情」。

---

### 腦力激盪 🧠

> 以下哪些適合做成 Resource？哪些適合做成 Tool？
>
> 1. 查詢使用者的訂單歷史記錄
> 2. 應用程式支援的語言列表（zh-TW、en、ja...）
> 3. 計算兩個日期之間的天數
> 4. 資料庫中所有資料表的名稱列表
> 5. 即時的伺服器 CPU 使用率

---

## 4.2 靜態 Resource — 固定 URI，固定內容

最簡單的 Resource 是靜態的：URI 是固定的，內容也是相對穩定的。

```python
# config_server.py — 靜態 Resource 範例
from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("設定服務")

# 靜態 Resource：URI 是固定的字串，沒有變數
@mcp.resource("config://app-settings")
def get_app_settings() -> str:
    """
    應用程式的全域設定，包含 UI 偏好、語言設定和功能開關。
    這是唯讀設定，不會因為呼叫而改變。
    """
    settings = {
        "ui": {
            "theme": "dark",
            "language": "zh-TW",
            "sidebar_collapsed": False,
        },
        "features": {
            "ai_suggestions": True,
            "auto_save": True,
            "beta_features": False,
        },
        "limits": {
            "max_upload_size_mb": 50,
            "max_items_per_page": 100,
        }
    }
    return json.dumps(settings, ensure_ascii=False, indent=2)


@mcp.resource("config://supported-languages")
def get_supported_languages() -> str:
    """應用程式支援的語言列表，包含代碼和顯示名稱。"""
    languages = [
        {"code": "zh-TW", "name": "繁體中文", "is_default": True},
        {"code": "zh-CN", "name": "简体中文", "is_default": False},
        {"code": "en", "name": "English", "is_default": False},
        {"code": "ja", "name": "日本語", "is_default": False},
    ]
    return json.dumps(languages, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
```

Resource 的 URI 格式是自訂的，沒有嚴格規定，但有一些常見的慣例：

```
URI 命名慣例：

config://...        設定類資料
db://...            資料庫相關
file://...          檔案系統
schema://...        資料 Schema
docs://...          文件
```

> **提醒**：Resource URI 的 scheme（`config://`、`db://` 等）是你自己決定的，不是網路協議。它們只是幫助你和 AI 理解「這個 Resource 屬於哪個類別」的命名慣例。

---

## 4.3 動態 Resource Template — URI 裡的變數

當你有很多相似的 Resource（例如每個資料表都有自己的 Schema），可以用 **URI 模板（URI Template）**，讓 URI 裡包含變數：

```python
# db_server.py — 動態 Resource Template 範例
from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("資料庫探索服務")

# 模擬的資料庫 Schema
DB_SCHEMAS = {
    "users": {
        "columns": [
            {"name": "id", "type": "integer", "primary_key": True},
            {"name": "email", "type": "varchar(255)", "unique": True, "nullable": False},
            {"name": "display_name", "type": "varchar(100)", "nullable": False},
            {"name": "role", "type": "varchar(20)", "default": "user"},
            {"name": "created_at", "type": "timestamptz", "default": "now()"},
        ],
        "row_count": 2341,
    },
    "orders": {
        "columns": [
            {"name": "id", "type": "integer", "primary_key": True},
            {"name": "user_id", "type": "integer", "foreign_key": "users.id"},
            {"name": "amount", "type": "decimal(10,2)", "nullable": False},
            {"name": "status", "type": "varchar(20)", "default": "pending"},
            {"name": "created_at", "type": "timestamptz", "default": "now()"},
        ],
        "row_count": 18720,
    },
    "products": {
        "columns": [
            {"name": "id", "type": "integer", "primary_key": True},
            {"name": "name", "type": "varchar(200)", "nullable": False},
            {"name": "price", "type": "decimal(10,2)", "nullable": False},
            {"name": "stock", "type": "integer", "default": 0},
        ],
        "row_count": 452,
    }
}


# 靜態 Resource：列出所有資料表
@mcp.resource("db://tables")
def list_tables() -> str:
    """
    列出資料庫中所有可用的資料表名稱和基本統計。
    在查詢特定資料表之前，可以先用這個 Resource 了解有哪些表。
    """
    tables_summary = [
        {
            "table_name": table_name,
            "row_count": schema["row_count"],
            "column_count": len(schema["columns"]),
        }
        for table_name, schema in DB_SCHEMAS.items()
    ]
    return json.dumps(tables_summary, ensure_ascii=False, indent=2)


# 動態 Resource Template：URI 裡有 {table_name} 變數
@mcp.resource("db://tables/{table_name}/schema")
def get_table_schema(table_name: str) -> str:
    """
    回傳指定資料表的完整欄位定義，包含欄位名稱、型別、約束條件和預設值。

    先用 db://tables 取得所有資料表名稱，再用這個 Resource 查看特定表的結構。
    """
    # 從 URI 模板提取的 table_name 變數會自動傳入函式
    if table_name not in DB_SCHEMAS:
        available = list(DB_SCHEMAS.keys())
        return json.dumps({
            "error": f"找不到資料表 '{table_name}'",
            "available_tables": available,
        }, ensure_ascii=False)

    schema = DB_SCHEMAS[table_name]
    return json.dumps({
        "table_name": table_name,
        "columns": schema["columns"],
        "row_count": schema["row_count"],
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
```

URI 模板的使用方式：

```
URI 模板：db://tables/{table_name}/schema

具體的 Resource URI：
  db://tables/users/schema       → 查詢 users 表的 Schema
  db://tables/orders/schema      → 查詢 orders 表的 Schema
  db://tables/products/schema    → 查詢 products 表的 Schema
```

FastMCP 會自動把 URI 裡的 `{table_name}` 部分提取出來，作為函式的參數傳入。

---

## 4.4 MIME Type — 告訴 Claude 這是什麼格式的資料

Resource 可以指定 **MIME Type（媒體類型）**，告訴客戶端（和 AI）這份資料的格式：

```python
# 不同 MIME type 的 Resource 範例
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("多格式資源服務")

# 純文字
@mcp.resource("docs://readme", mime_type="text/plain")
def get_readme() -> str:
    """系統的 README 文件（純文字格式）"""
    return "# 歡迎使用本系統\n\n這是一個資料分析平台..."


# JSON 資料
@mcp.resource("data://config", mime_type="application/json")
def get_config() -> str:
    """系統設定（JSON 格式，可直接解析）"""
    import json
    return json.dumps({"version": "2.0", "debug": False})


# Markdown 格式的文件
@mcp.resource("docs://api-guide", mime_type="text/markdown")
def get_api_guide() -> str:
    """API 使用指南（Markdown 格式）"""
    return """# API 使用指南

## 認證

所有 API 請求需要在 Header 中帶入 Bearer Token：

```
Authorization: Bearer <your-token>
```

## 速率限制

每個 Token 每分鐘最多 60 次請求。
"""
```

常用的 MIME Type：

```
text/plain          純文字（預設）
application/json    JSON 資料（Claude 會嘗試解析結構）
text/markdown       Markdown 格式文件
text/csv            CSV 表格資料
image/png           PNG 圖片
image/jpeg          JPEG 圖片
```

> **重要**：MIME type 不只是標籤，它會影響 Claude 如何處理資料。
>
> - `application/json`：Claude 知道可以解析 JSON 結構，查詢特定欄位
> - `text/markdown`：Claude 知道這是格式化文件，會以適當方式展示
> - `image/png`：Claude 可以直接「看」這張圖片（需要多模態支援）

---

## 4.5 實作：把 Qdrant Collections 和 Supabase 資料表暴露為 Resources

這是一個更接近真實專案的範例。我們要把向量資料庫（Qdrant）的 collection 列表和 Supabase 的資料表暴露為 Resources。

```python
# knowledge_resources.py — 真實專案範例
from mcp.server.fastmcp import FastMCP
import json
import os

mcp = FastMCP("知識庫探索服務")

# ─── Qdrant Resources ────────────────────────────────────────────────

def get_qdrant_client():
    """取得 Qdrant 客戶端（延遲初始化）"""
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )


@mcp.resource("qdrant://collections")
def list_qdrant_collections() -> str:
    """
    列出 Qdrant 向量資料庫中所有 collection 的名稱和統計資料。

    在用向量搜尋工具搜尋之前，可以先讀這個 Resource 了解有哪些 collection 可用。
    每個 collection 包含名稱、向量數量和向量維度。
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections

        result = [
            {
                "name": col.name,
                "status": col.status.value if hasattr(col.status, 'value') else str(col.status),
            }
            for col in collections
        ]

        # 取得每個 collection 的詳細資訊
        detailed = []
        for col in collections:
            try:
                info = client.get_collection(col.name)
                detailed.append({
                    "name": col.name,
                    "vectors_count": info.vectors_count,
                    "vector_size": info.config.params.vectors.size
                    if hasattr(info.config.params.vectors, 'size') else "未知",
                })
            except Exception:
                detailed.append({"name": col.name, "note": "無法取得詳細資訊"})

        return json.dumps(detailed, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"無法連接到 Qdrant：{str(e)}",
            "hint": "請確認 QDRANT_URL 環境變數是否設定正確",
        }, ensure_ascii=False)


@mcp.resource("qdrant://collections/{collection_name}/info")
def get_qdrant_collection_info(collection_name: str) -> str:
    """
    取得指定 Qdrant collection 的詳細設定，包含向量維度、距離計算方式和索引設定。

    在決定要用哪個 collection 做搜尋之前，可以先查看它的詳細設定。
    """
    try:
        client = get_qdrant_client()
        info = client.get_collection(collection_name)

        result = {
            "collection_name": collection_name,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "status": str(info.status),
            "optimizer_status": str(info.optimizer_status),
        }

        # 嘗試提取向量設定
        if hasattr(info.config.params, 'vectors'):
            vec_config = info.config.params.vectors
            if hasattr(vec_config, 'size'):
                result["vector_config"] = {
                    "size": vec_config.size,
                    "distance": str(vec_config.distance),
                }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"無法取得 collection '{collection_name}' 的資訊：{str(e)}",
            "hint": "請先用 qdrant://collections 確認 collection 名稱是否正確",
        }, ensure_ascii=False)


# ─── Supabase Resources ──────────────────────────────────────────────

def get_supabase_client():
    """取得 Supabase 客戶端"""
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # 用 service role key 才能查 schema
    if not url or not key:
        raise ValueError("請設定 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY 環境變數")
    return create_client(url, key)


@mcp.resource("supabase://tables")
def list_supabase_tables() -> str:
    """
    列出 Supabase 資料庫中所有公開的（public schema）資料表名稱。

    在查詢特定資料表之前，可以先讀這個 Resource 了解有哪些表可用。
    """
    try:
        client = get_supabase_client()
        # 查詢 Postgres 的 information_schema 取得資料表列表
        result = client.rpc("get_table_names").execute()

        if result.data:
            return json.dumps(result.data, ensure_ascii=False, indent=2)

        # 備用方案：直接查 information_schema
        result = client.from_("information_schema.tables").select(
            "table_name"
        ).eq("table_schema", "public").execute()

        tables = [row["table_name"] for row in result.data]
        return json.dumps({"tables": tables}, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"無法取得資料表列表：{str(e)}",
            "hint": "請確認 Supabase 連線設定是否正確",
        }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
```

---

---

# PART 2：Prompts

## 4.6 Prompt 原語：標準化問法的捷徑

你和同事每天都在做數據分析，每次都要輸入類似的提示詞：

```
「請幫我分析 sales 資料表的趨勢，
  先查最近 30 天的數據，
  計算日均值、週環比、月環比，
  找出異常點，
  用繁體中文寫分析報告...」
```

這段提示詞寫了一次、兩次、三次之後，你開始想：有沒有辦法把它**打包**起來，讓所有人都能用同一個標準流程？

這就是 **MCP Prompts** 的用途。

**Prompt 原語**讓你能夠把**可重用的提示詞模板**打包進 MCP Server。使用者可以在 Claude Desktop 的「/」選單裡直接呼叫這些模板，就像使用斜線指令一樣。

```
在 Claude Desktop 輸入 /  →  看到你定義的 Prompts 列表
選擇「analyze_data」       →  Claude 自動填入分析流程的提示詞
你只需要確認 parameters   →  Claude 開始按照標準流程工作
```

> **提醒**：Prompts 和 Tools、Resources 的最大差異是：Prompt 不**執行**任何操作，它只是**準備一段提示詞**，讓 Claude 知道接下來要做什麼、按照什麼流程做。真正的操作（查資料庫、搜尋向量）還是靠 Tools 和 Resources。

---

## 4.7 靜態 vs 動態 Prompt

### 靜態 Prompt：固定的提示詞

```python
from mcp.server.fastmcp import FastMCP
from mcp.types import Message, TextContent

mcp = FastMCP("分析助理")

@mcp.prompt()
def quick_data_check() -> str:
    """
    快速資料品質檢查流程。
    在 Claude Desktop 的 / 選單中呼叫，讓 Claude 按照標準流程檢查資料品質。
    """
    return """請執行標準資料品質檢查，步驟如下：

1. **資料探索**：先用 list_tables 工具列出所有資料表，選擇要分析的表
2. **基本統計**：查詢總筆數、最早/最新的資料時間戳
3. **缺失值檢查**：找出每個欄位的 NULL 比例
4. **重複值檢查**：確認主鍵是否有重複
5. **異常值初步掃描**：對數值欄位進行基本統計（min/max/平均）

請用繁體中文撰寫檢查報告，並用清單格式呈現發現的問題。"""
```

### 動態 Prompt：帶參數的提示詞模板

```python
@mcp.prompt()
def analyze_data(table: str, metric: str = "trend") -> str:
    """
    資料分析標準流程。
    table 是要分析的資料表名稱，metric 是分析重點（trend/anomaly/summary）。
    """
    metric_instructions = {
        "trend": "重點分析時間趨勢，計算日環比、週環比，找出成長或衰退的模式",
        "anomaly": "重點找出異常數據點，使用 2 個標準差法則標記異常值",
        "summary": "重點提供全面的描述性統計摘要，適合定期報告使用",
    }

    metric_desc = metric_instructions.get(metric, metric_instructions["trend"])

    return f"""請分析 **{table}** 資料表的資料。分析重點：{metric_desc}

## 分析步驟

1. **取得 Schema**：讀取 db://tables/{table}/schema，了解欄位結構
2. **取得資料**：呼叫 query_database 工具取得最近 30 天的資料
3. **統計計算**：計算以下指標：
   - 基本統計：平均值、最大值、最小值、標準差
   - 時間趨勢：日均值、週環比（與上週同期比較）
   - 異常偵測：標記超過 2 個標準差的數據點
4. **報告撰寫**：用繁體中文撰寫分析報告，包含：
   - 執行摘要（2-3 句話）
   - 主要發現（條列式）
   - 數據圖表建議（說明應該畫什麼圖）
   - 建議行動項目

請在開始分析前，先確認 {table} 資料表存在。如果不存在，請列出可用的資料表供選擇。"""
```

---

## 4.8 實作：建立資料分析 Prompt 庫

我們來建立一個完整的 Prompt 庫，包含三個分析模板：

```python
# analysis_prompts.py — 完整的資料分析 Prompt 庫
from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("資料分析助理")

# ─── 工具（分析需要的）──────────────────────────────────────────────

@mcp.tool()
def query_database(sql: str) -> str:
    """
    執行 SQL 查詢並回傳結果。

    當需要從資料庫取得資料進行分析時使用。
    sql 是要執行的 SELECT 查詢語句（不支援 INSERT/UPDATE/DELETE）。
    如果不確定 Schema，請先讀取對應的 db://tables/{table}/schema Resource。

    ⚠️  只允許 SELECT 語句，不接受修改資料的語句。
    """
    # 安全檢查：只允許 SELECT
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return "錯誤：只允許 SELECT 查詢。不接受 INSERT、UPDATE、DELETE 等修改語句。"

    # 這裡是模擬實作，實際要連接真實資料庫
    mock_data = [
        {"date": "2026-03-01", "sales": 12500, "orders": 87},
        {"date": "2026-03-02", "sales": 15200, "orders": 103},
        {"date": "2026-03-03", "sales": 9800, "orders": 67},
        {"date": "2026-03-04", "sales": 18300, "orders": 124},
        {"date": "2026-03-05", "sales": 21000, "orders": 142},
    ]
    return json.dumps({
        "query": sql,
        "row_count": len(mock_data),
        "data": mock_data,
        "note": "（這是模擬資料，實際部署時會連接真實資料庫）"
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def calculate_statistics(data: list[float]) -> str:
    """
    計算一組數值的完整統計摘要。

    提供數字列表，回傳包含平均值、標準差、四分位數等統計指標的報告。
    適合在分析資料後，對數值欄位進行快速統計。
    """
    import math
    if not data:
        return "錯誤：data 列表不能是空的。"

    n = len(data)
    mean = sum(data) / n
    sorted_data = sorted(data)
    variance = sum((x - mean) ** 2 for x in data) / n
    std = math.sqrt(variance)

    # 計算四分位數
    def percentile(sorted_list, pct):
        idx = (len(sorted_list) - 1) * pct / 100
        lower = sorted_list[int(idx)]
        upper = sorted_list[min(int(idx) + 1, len(sorted_list) - 1)]
        return lower + (upper - lower) * (idx - int(idx))

    result = {
        "count": n,
        "mean": round(mean, 2),
        "std": round(std, 2),
        "min": round(sorted_data[0], 2),
        "q25": round(percentile(sorted_data, 25), 2),
        "median": round(percentile(sorted_data, 50), 2),
        "q75": round(percentile(sorted_data, 75), 2),
        "max": round(sorted_data[-1], 2),
        "outlier_threshold_upper": round(mean + 2 * std, 2),
        "outlier_threshold_lower": round(mean - 2 * std, 2),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ─── Resources（分析需要的背景資訊）────────────────────────────────

@mcp.resource("db://tables")
def list_tables() -> str:
    """資料庫中所有可用的資料表"""
    tables = [
        {"name": "sales", "description": "每日銷售記錄", "row_count": 15420},
        {"name": "users", "description": "用戶資料", "row_count": 2341},
        {"name": "orders", "description": "訂單記錄", "row_count": 18720},
        {"name": "products", "description": "產品目錄", "row_count": 452},
    ]
    return json.dumps(tables, ensure_ascii=False, indent=2)


@mcp.resource("db://tables/{table_name}/schema")
def get_table_schema(table_name: str) -> str:
    """指定資料表的欄位定義"""
    schemas = {
        "sales": {
            "columns": [
                {"name": "date", "type": "date"},
                {"name": "sales_amount", "type": "decimal(12,2)"},
                {"name": "order_count", "type": "integer"},
                {"name": "product_id", "type": "integer"},
            ]
        },
        "orders": {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "user_id", "type": "integer"},
                {"name": "amount", "type": "decimal(10,2)"},
                {"name": "status", "type": "varchar(20)"},
                {"name": "created_at", "type": "timestamptz"},
            ]
        },
    }
    schema = schemas.get(table_name)
    if not schema:
        return json.dumps({"error": f"找不到資料表 {table_name}"}, ensure_ascii=False)
    return json.dumps({"table": table_name, **schema}, ensure_ascii=False, indent=2)


# ─── Prompts（三個分析模板）─────────────────────────────────────────

@mcp.prompt()
def trend_analysis(table: str, date_column: str = "created_at", value_column: str = "amount") -> str:
    """
    趨勢分析標準流程。
    分析指定資料表的時間趨勢，找出成長、衰退或週期性模式。

    table：要分析的資料表名稱
    date_column：時間欄位的名稱（預設 created_at）
    value_column：要分析的數值欄位（預設 amount）
    """
    return f"""請對 **{table}** 資料表執行趨勢分析。

## 分析目標
找出 `{value_column}` 欄位在時間維度（`{date_column}`）上的趨勢。

## 執行步驟

### 第一步：了解資料結構
讀取 Resource `db://tables/{table}/schema`，確認欄位存在且型別正確。

### 第二步：取得資料
```sql
SELECT
    DATE_TRUNC('day', {date_column}) AS analysis_date,
    COUNT(*) AS record_count,
    SUM({value_column}) AS total_value,
    AVG({value_column}) AS avg_value
FROM {table}
WHERE {date_column} >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', {date_column})
ORDER BY analysis_date
```
用 `query_database` 工具執行此查詢。

### 第三步：統計分析
把 `total_value` 的值取出，用 `calculate_statistics` 工具計算統計摘要。

### 第四步：趨勢判斷
計算以下指標：
- **日環比**：今日 vs 昨日的變化百分比
- **7 日移動平均**：找出趨勢方向
- **異常點**：超過 2 個標準差的日期

### 第五步：撰寫報告
用繁體中文輸出報告，格式：
1. **執行摘要**（2-3 句話描述整體趨勢）
2. **關鍵指標**（表格呈現）
3. **異常日期**（條列，說明可能原因）
4. **建議**（根據趨勢提出的行動建議）"""


@mcp.prompt()
def anomaly_detection(table: str, value_column: str, threshold_std: float = 2.0) -> str:
    """
    異常偵測標準流程。
    使用統計方法（Z-score）找出資料中的異常值。

    table：要分析的資料表
    value_column：要檢查異常的數值欄位
    threshold_std：判斷異常的標準差倍數（預設 2.0，更嚴格可用 3.0）
    """
    return f"""請對 **{table}** 資料表的 `{value_column}` 欄位執行異常偵測。

## 異常偵測方法
使用 Z-score 方法：當某個值距離平均值超過 **{threshold_std} 個標準差**時，標記為異常。

## 執行步驟

### 第一步：取得所有資料
```sql
SELECT id, {value_column}, created_at
FROM {table}
WHERE {value_column} IS NOT NULL
ORDER BY created_at DESC
LIMIT 1000
```
用 `query_database` 工具執行。

### 第二步：計算統計基準
把所有 `{value_column}` 的值取出，放入 `calculate_statistics` 工具。
記錄回傳的 `mean`、`std`、`outlier_threshold_upper`、`outlier_threshold_lower`。

### 第三步：標記異常
找出所有超出 [{threshold_std} 個標準差] 範圍的資料筆：
- 上界異常：{value_column} > (mean + {threshold_std} × std)
- 下界異常：{value_column} < (mean - {threshold_std} × std)

### 第四步：輸出異常報告
用繁體中文輸出：
1. **異常摘要**：共發現幾筆異常（佔總筆數百分比）
2. **異常清單**：列出每一筆異常的 ID、值、與平均值的偏差
3. **模式分析**：這些異常有沒有共同點（時間集中？特定類別？）
4. **建議處置**：是資料錯誤？還是真實的業務異常？建議如何跟進"""


@mcp.prompt()
def generate_report(table: str, report_type: str = "weekly", audience: str = "management") -> str:
    """
    定期報告生成流程。
    生成適合不同受眾的標準化資料分析報告。

    table：資料表名稱
    report_type：報告週期（daily/weekly/monthly）
    audience：目標受眾（management/technical/customer）
    """
    period_map = {
        "daily": "今日（與昨日比較）",
        "weekly": "本週（與上週比較）",
        "monthly": "本月（與上月比較）",
    }
    audience_map = {
        "management": "管理層（著重 KPI 達成率、業務影響、決策建議）",
        "technical": "技術團隊（著重數據細節、異常原因、系統指標）",
        "customer": "客戶（著重服務表現、改善成果、正面呈現）",
    }

    period_desc = period_map.get(report_type, period_map["weekly"])
    audience_desc = audience_map.get(audience, audience_map["management"])

    return f"""請為 **{table}** 資料表生成{period_desc}分析報告。

## 報告目標受眾
{audience_desc}

## 生成步驟

### 第一步：資料準備
1. 讀取 `db://tables/{table}/schema` 了解欄位
2. 查詢本期資料（過去 {7 if report_type == 'weekly' else 1 if report_type == 'daily' else 30} 天）
3. 查詢上期資料（相同天數，用於環比計算）

### 第二步：計算核心指標
- 總量：本期 vs 上期，計算環比變化（%）
- 平均：本期 vs 上期，計算環比變化（%）
- 最高/最低：記錄極值及發生時間

### 第三步：撰寫報告
報告結構：

**{period_desc}報告**
生成日期：（今日日期）

---

**執行摘要**
（2-3 句話，重點說明本期最重要的發現）

**核心 KPI**
| 指標 | 本期 | 上期 | 變化 |
|------|------|------|------|
| ... | ... | ... | ...% |

**主要發現**
1. （最重要的發現）
2. （第二重要的發現）
3. （第三重要的發現）

**建議行動**
- （針對受眾的具體建議）

---
報告語氣要符合受眾：{audience_desc}"""


if __name__ == "__main__":
    mcp.run()
```

---

## 動手做：Resources + Prompts 綜合 Lab

### 目標

建立一個「知識庫探索伺服器」，整合 Resources 和 Prompts：

### 規格

```
Resources（2個）：
  1. qdrant://collections
     列出所有 Qdrant collections 的名稱
     （若沒有 Qdrant，用 mock 資料代替）

  2. qdrant://collections/{name}/sample
     回傳指定 collection 的 3 筆範例資料點
     （展示向量資料的欄位結構）

Prompts（2個）：
  1. search_knowledge(query, collection)
     標準的 RAG 搜尋流程提示詞
     引導 Claude：先確認 collection 存在，
     再呼叫 semantic_search 工具，
     最後整合結果回答

  2. audit_knowledge_base()
     知識庫健康度審計提示詞
     引導 Claude：列出所有 collections，
     對每個做基本統計，
     找出可能有問題的 collections（太小、太舊）
```

### 起始框架

```python
# knowledge_lab.py
from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("知識庫探索服務")

# Mock 資料（沒有真實 Qdrant 時用這個）
MOCK_COLLECTIONS = {
    "product_faq": {
        "count": 1250,
        "vector_size": 1536,
        "sample": [
            {"id": "faq_001", "payload": {"question": "如何退貨？", "category": "退換貨"}},
            {"id": "faq_002", "payload": {"question": "保固期多久？", "category": "保固"}},
            {"id": "faq_003", "payload": {"question": "如何追蹤訂單？", "category": "物流"}},
        ]
    },
    "technical_docs": {
        "count": 3420,
        "vector_size": 1536,
        "sample": [
            {"id": "doc_001", "payload": {"title": "API 使用指南", "section": "認證"}},
            {"id": "doc_002", "payload": {"title": "Webhook 設定", "section": "整合"}},
            {"id": "doc_003", "payload": {"title": "錯誤代碼一覽", "section": "除錯"}},
        ]
    },
}


# 你的任務：實作以下 Resources 和 Prompts

@mcp.resource("qdrant://collections")
def list_collections() -> str:
    """列出所有知識庫 collection"""
    # 使用 MOCK_COLLECTIONS 實作
    pass


@mcp.resource("qdrant://collections/{name}/sample")
def get_collection_sample(name: str) -> str:
    """回傳指定 collection 的範例資料"""
    # 使用 MOCK_COLLECTIONS 實作，如果找不到要回傳有意義的錯誤
    pass


@mcp.prompt()
def search_knowledge(query: str, collection: str = "product_faq") -> str:
    """RAG 搜尋流程提示詞"""
    # 回傳引導 Claude 做 RAG 搜尋的提示詞字串
    pass


@mcp.prompt()
def audit_knowledge_base() -> str:
    """知識庫健康度審計提示詞"""
    # 回傳引導 Claude 做知識庫審計的提示詞字串
    pass


if __name__ == "__main__":
    mcp.run()
```

### 測試步驟

```bash
# 啟動 Inspector
mcp dev knowledge_lab.py

# 在 Inspector 裡測試：
# 1. 切換到 Resources 標籤
# 2. 讀取 qdrant://collections
# 3. 讀取 qdrant://collections/product_faq/sample
# 4. 讀取 qdrant://collections/不存在的名稱/sample（確認錯誤處理）
# 5. 切換到 Prompts 標籤
# 6. 呼叫 search_knowledge，填入 query 和 collection
# 7. 觀察生成的提示詞是否清楚、完整
```

---

## 重點回顧 📌

```
┌─────────────────────────────────────────────────────┐
│                  第四章重點回顧                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  PART 1 - Resources：                               │
│                                                     │
│  • Tool vs Resource 決策：                          │
│    有副作用/需要計算 → Tool                         │
│    唯讀/結構化/可瀏覽 → Resource                    │
│    名詞 → Resource，動詞 → Tool                     │
│                                                     │
│  • 靜態 Resource：@mcp.resource("固定://URI")       │
│  • 動態 Resource：@mcp.resource("uri/{variable}")   │
│    URI 變數自動成為函式參數                         │
│                                                     │
│  • MIME Type 影響 Claude 的解讀方式：               │
│    application/json → 可解析結構                    │
│    text/markdown    → 格式化文件                    │
│    image/png        → 視覺圖像                      │
│                                                     │
│  PART 2 - Prompts：                                 │
│                                                     │
│  • Prompt 是可重用的提示詞模板                      │
│  • 出現在 Claude Desktop 的「/」選單裡              │
│  • 靜態（無參數）和動態（有參數）兩種               │
│  • Prompt 不執行操作，只準備提示詞                  │
│  • 真正的操作還是靠 Tools 和 Resources              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 常見問題 FAQ

**Q1：Resource 和 Tool 的回傳值格式一樣嗎？**

都是字串，但 Resource 額外支援 MIME type 標記。Tool 的回傳永遠被當成純文字（或 JSON 字串）。Resource 可以透過 `mime_type` 參數告訴客戶端「這是 JSON」、「這是圖片」，讓客戶端做出不同的處理。

**Q2：Claude Desktop 在什麼時候會自動讀取 Resource？**

Claude 不會「主動」讀取 Resource——它需要判斷「我需要這個背景資訊」才會去讀。你可以在 Tool 的 description 或 Prompt 裡提示 Claude：「在做 X 之前，先讀取 Resource Y 取得背景資訊」，這樣 Claude 就會在適當時機讀取 Resource。

**Q3：Prompt 和直接把提示詞寫在 System Prompt 裡有什麼差別？**

System Prompt 是每次對話都固定存在的背景指令。MCP Prompt 是使用者**主動觸發**的提示詞模板，使用者可以選擇要不要用、用哪一個。MCP Prompt 更靈活，適合多種分析場景的標準化流程；System Prompt 適合固定的行為約束。

**Q4：Resource 的內容會自動更新嗎？**

不會自動更新，但你可以讓 Resource 函式每次被讀取時都去查詢最新的資料（就像我們的範例那樣）。如果你的 Resource 需要通知客戶端「資料已更新」，MCP 協議有 Resource Subscription 機制，但這是進階功能，大多數情況不需要。

---

## 課後練習

### ⭐ 基礎練習：完成 Lab

完成 `knowledge_lab.py` 的四個函式（2 個 Resource，2 個 Prompt），確保：
- Resources 能正確回傳 mock 資料
- 找不到 collection 時回傳有意義的錯誤
- Prompts 生成的提示詞清楚、可操作

### ⭐⭐ 進階練習：個人設定面板

建立一個 `personal_settings.py`，把使用者的個人化設定暴露為 Resources：

```
config://profile          → 使用者的姓名、偏好語言、時區
config://shortcuts        → 常用查詢的快捷方式列表
config://recent-tables    → 最近使用的資料表（模擬，用列表）
```

並且建立一個 Prompt：`my_analysis(question)` — 根據使用者的偏好設定，生成個人化的分析提示詞（例如：如果偏好語言是 zh-TW，提示詞要求用繁體中文輸出）。

### ⭐⭐⭐ 挑戰練習：動態 Prompt 工廠

設計並實作一個「Prompt 工廠」：

根據使用者選擇的分析目的（銷售分析/用戶行為/系統監控）和資料表，動態生成最適合的分析提示詞。

要求：
- 至少支援 3 種分析目的
- 每種分析目的有不同的 SQL 模板和分析重點
- Prompt 要包含錯誤處理提示（如果查詢失敗，Claude 應該怎麼辦）
- 所有 Prompt 都要求 Claude 在開始前先驗證資料表是否存在

---

## 下一章預告

你現在有了完整的 MCP Server——Tools、Resources、Prompts 都齊了。接下來的挑戰是：怎麼確保它**可靠**、**安全**，並且能夠**部署到生產環境**？

第五章是最後一章，也是最實用的一章：測試策略（從單元測試到整合測試）、安全防線（Prompt Injection 防禦、稽核日誌）、以及三種部署方式（本機 stdio、Docker SSE、雲端 Streamable HTTP）。

→ [第五章：測試、安全、部署](./ch05-test-security-deploy.md)

← [第三章：工具設計的藝術](./ch03-tool-design.md)
