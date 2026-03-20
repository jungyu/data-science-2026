# Module Pre-A｜ETL Pipeline — 把知識存進 Qdrant

> **前置條件**：已完成 ch02（ETL 切塊理論）和 ch03（向量搜尋理論）
> **後置條件**：Qdrant 中有資料 → Module A（MCP Server）才能搜尋得到東西
>
> **學習成果**：能把網頁、PDF、自訂文字存進 Qdrant，建立你的 RAG 知識庫

---

## 這個模組解決什麼問題？

```
ch02 教你「如何切塊」         ─┐
ch03 教你「向量是什麼」        ─┤→ 理論都有了，但 Qdrant 裡是空的！
Module A 說「從 Qdrant 搜尋」 ─┘

Module Pre-A 就是把這些串起來的那條線：
  你的文件 → 爬蟲/貼文字 → 切塊 → Embedding → Qdrant
```

---

## 爬蟲服務架構

```
POST /crawl               POST /crawl/text
     │                          │
     ▼                          ▼
fetch_page_text()          直接使用輸入文字
（Playwright 抓網頁）
     │                          │
     └──────────┬───────────────┘
                ▼
          chunk_text()
       （按 token 數切塊，帶 overlap）
                ▼
          embed_chunks()
       （OpenAI text-embedding-3-small）
                ▼
          upsert_chunks()
       （存進 Qdrant collection）
```

---

## Pre-A1｜啟動爬蟲服務

### 方式一：docker compose（推薦）

```bash
cd _project-fullstack

# Qdrant 和 crawler 一起啟動
docker compose up -d qdrant crawler

# 確認兩個服務都起來了
docker compose ps

# 查看爬蟲日誌
docker compose logs crawler -f
```

### 方式二：本機開發

```bash
cd _project-fullstack/crawler

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium   # 只裝 chromium，約 200MB

cp ../.env.example .env
# 填入 OPENAI_API_KEY
# QDRANT_URL=http://localhost:6333（Qdrant 需另外啟動）

python crawler.py
```

### 驗收

```bash
curl http://localhost:3001/health
# {
#   "status": "ok",
#   "qdrant_ok": true,
#   "collections": []
# }
```

---

## Pre-A2｜把你的資料存進 Qdrant

### 方法一：爬網頁

```bash
curl -X POST http://localhost:3001/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://你的目標網頁",
    "collection": "knowledge"
  }'

# 回傳：
# {
#   "status": "ok",
#   "url": "https://...",
#   "collection": "knowledge",
#   "chunks": 12,      ← 切了幾塊
#   "chars": 8432      ← 原始文字字元數
# }
```

**適合的資料來源**：
- 公司/組織的官網說明頁
- 政府開放資料說明頁
- Wikipedia 條目
- 技術文件頁面

> ⚠️ **爬不到的情況**：需要登入的頁面、純 JavaScript 渲染（SPA）、有爬蟲防護的網站
> → 改用方法二直接貼文字

### 方法二：直接貼文字（最萬用）

```bash
curl -X POST http://localhost:3001/crawl/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你的文字內容，可以從 PDF 複製貼上，或是手動輸入",
    "source": "產品手冊第三章",
    "collection": "knowledge"
  }'
```

**適合的資料來源**：
- PDF 文件內容（先用 `pdfplumber` 或直接複製）
- Word 文件內容
- 已有的問答集（FAQ）
- 你自己寫的說明文件

### 用 Python 批次匯入

如果資料量大，用 Python 腳本批次處理更有效率：

```python
# batch_import.py — 批次匯入多個 URL 或文字

import requests

BASE = "http://localhost:3001"
COLLECTION = "knowledge"   # 改成你的 collection 名稱

# ── 批次爬網頁 ────────────────────────────────────────────
urls = [
    "https://example.com/page-1",
    "https://example.com/page-2",
    "https://example.com/page-3",
]

for url in urls:
    res = requests.post(f"{BASE}/crawl", json={
        "url": url,
        "collection": COLLECTION,
    })
    data = res.json()
    print(f"✓ {url} → {data.get('chunks', '?')} 塊")


# ── 批次匯入文字 ──────────────────────────────────────────
texts = [
    {"text": "第一段文字內容...", "source": "文件A第1節"},
    {"text": "第二段文字內容...", "source": "文件A第2節"},
]

for item in texts:
    res = requests.post(f"{BASE}/crawl/text", json={
        **item,
        "collection": COLLECTION,
    })
    data = res.json()
    print(f"✓ {item['source']} → {data.get('chunks', '?')} 塊")
```

---

## Pre-A3｜確認資料存入成功

### 查看 collection 狀態

```bash
curl http://localhost:3001/collections
# {
#   "collections": [
#     {"name": "knowledge", "points": 47}   ← 你有 47 個向量點
#   ]
# }
```

### 用 Qdrant Web UI 查看

瀏覽器開啟 `http://localhost:6333/dashboard`

1. 左側選 Collections → 點選你的 collection
2. 可以看到每個向量點的 payload（text、source、chunk_index）
3. 點「Search」可以用文字測試搜尋

### 用 Python 快速驗收搜尋

```python
# verify_search.py — 確認 RAG 搜尋可以找到相關內容

from openai import OpenAI
from qdrant_client import QdrantClient

openai_client = OpenAI()
qdrant_client = QdrantClient("http://localhost:6333")

COLLECTION = "knowledge"
QUERY      = "你的測試問題"   # ← 改成你預期能找到答案的問題

# 嵌入問題
vector = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input=QUERY,
).data[0].embedding

# 搜尋
hits = qdrant_client.search(
    collection_name=COLLECTION,
    query_vector=vector,
    limit=3,
    with_payload=True,
)

print(f"問題：{QUERY}\n")
for i, hit in enumerate(hits, 1):
    print(f"[{i}] 相似度：{hit.score:.3f}")
    print(f"     來源：{hit.payload['source']}")
    print(f"     內容：{hit.payload['text'][:200]}...\n")
```

如果能找到相關內容，代表你的知識庫建好了，可以繼續 Module A。

---

## Pre-A4｜切塊參數調整

專案預設值：

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `CHUNK_TOKENS` | 400 | 每塊大約 400 個 token（約 300 個中文字） |
| `CHUNK_OVERLAP` | 50 | 相鄰塊重疊 50 個 token，確保語意不斷裂 |
| `EMBEDDING_MODEL` | text-embedding-3-small | OpenAI 最新小型嵌入模型 |

**什麼時候要調整？**

- 資料是**長篇論述**（新聞、學術論文）→ 可以加大到 600–800 tokens
- 資料是**FAQ 問答**（每題很短）→ 縮小到 200–300 tokens
- 搜尋結果**語意跳躍**（前後文不連貫）→ 增加 overlap 到 100

修改方式：直接編輯 `crawler.py` 上方的常數：

```python
CHUNK_TOKENS  = 400   # ← 改這裡
CHUNK_OVERLAP = 50    # ← 改這裡
```

---

## 重點回顧

```
╔══════════════════════════════════════════════════════╗
║  Module Pre-A 核心概念                                ║
╠══════════════════════════════════════════════════════╣
║  • 爬蟲流程：抓取 → 切塊 → Embedding → Qdrant        ║
║  • /crawl（網頁）和 /crawl/text（貼文字）二選一        ║
║  • 驗收：/collections 看點數，Qdrant UI 看內容         ║
║  • 確認搜尋有結果後才進 Module A                       ║
║  • chunk 大小影響搜尋品質，FAQ 用小塊，長文用大塊        ║
╚══════════════════════════════════════════════════════╝
```

---

## 課後練習

**⭐ 基本（必要）**
1. 啟動 qdrant + crawler，呼叫 `/health` 確認兩個服務都正常
2. 用 `/crawl/text` 把你的專題主題文字（至少 500 字）存進 `knowledge` collection
3. 執行 `verify_search.py` 確認搜尋有結果

**⭐⭐ 進階**
4. 用 `batch_import.py` 批次匯入 ≥ 3 個來源（網頁或文字）
5. 在 Qdrant Web UI 觀察各個 chunk 的 payload，確認 source 標籤正確

**⭐⭐⭐ 挑戰**
6. 調整 `CHUNK_TOKENS` 和 `CHUNK_OVERLAP`，重新匯入同一份文件，比較搜尋品質差異

---

## 常見問題

**Q：`POST /crawl` 回傳 422「網頁內容太短」？**
A：該頁面可能需要 JavaScript 執行才能顯示內容（SPA 框架）。改用 `/crawl/text`，把網頁內容手動複製貼上。

**Q：Dockerfile 建置時卡在 `playwright install chromium`？**
A：Chromium 約 200MB，第一次建置需要時間。確認網路連線，或設定 Docker 的 HTTP proxy。

**Q：存了很多資料但搜尋結果都不準？**
A：常見原因：chunk 太大導致語意稀釋，或資料品質太差（HTML 殘留、亂碼）。
建議：先用 Qdrant UI 查看存入的 payload 文字是否可讀，再調整 chunk 大小。

**Q：可以同時有多個 collection 嗎？**
A：可以。不同主題的資料建議放不同 collection，方便管理和重置。
例如：`collection: "faq"` 存問答集，`collection: "reports"` 存報表。
Module A 的 `search_knowledge_base` 工具有 `collection` 參數可以指定。

---

> 完成本模組後，你的 Qdrant 裡有了資料，繼續 **Module A｜MCP Server**，讓 Claude Desktop 能搜尋它。
