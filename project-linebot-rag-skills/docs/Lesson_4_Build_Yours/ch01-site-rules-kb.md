# Ch 01：替換點 1 — 知識庫

> 核心檔案：[`scripts/site_rules.py`](../../scripts/site_rules.py)

---

## 1-1  先確認你的領域屬於哪種類型

| 類型 | 例子 | 建議來源格式 |
|------|------|------------|
| 技術文件 | FastAPI 文件、K8s 文件 | 爬官方網站（web） |
| 法規 / 條文 | 勞基法、食品安全法 | PDF 入庫 |
| 商品 / 服務資料 | 藥品清單、菜單 | CSV 入庫 |
| 內部 wiki | Notion、Confluence | Notion export / Markdown |
| 混合型 | 醫療 = 仿單 PDF + 衛福部網站 | 多種格式並行 |

---

## 1-2  決定 `category` 名稱（最重要的一步）

`category` 是整個系統的路由 key。
**knowledge base 的 category 必須和 skill 的 `rag_categories` 完全一致**，
否則 retriever 找不到任何 chunk。

先決定你的 category，之後所有步驟都用同一個名稱：

```
# 好的命名（具體、小寫、無空格）
"drug_info"          ← 藥物資訊 bot
"labor_law"          ← 勞動法規 bot
"menu_items"         ← 餐廳點餐 bot
"company_policy"     ← 內部 HR bot

# 避免的命名
"data"               ← 太廣泛
"my knowledge"       ← 有空格，容易出錯
"知識庫"             ← 用英文，跨語言處理更穩定
```

### 常見靜默失敗：category 不對齊

這是 L4 最常見、最難排查的問題：bot 能跑、能回答，但完全不引用你的知識庫。
原因是 `rag_categories` 和 `private_knowledge.category` 名稱差一個字。

**在開始入庫之前，先用這個指令確認對齊**：

```bash
# 看 KB 裡有哪些 category（入庫後用）
python -c "
import asyncio
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient
async def main():
    rows = await SupabaseRestClient(Settings()).select(
        'private_knowledge', {'select': 'category'})
    cats = sorted(set(r['category'] for r in rows))
    for c in cats:
        print(c)
asyncio.run(main())
"

# 看 skills 裡宣告了哪些 rag_categories
grep -r "rag_categories" skills/
```

**對照範例**：

```
KB category:       fastapi
skill rag_categories: [fastapi]    ← ✅ 完全一致，retriever 能找到

KB category:       fastapi
skill rag_categories: [FastAPI]    ← ❌ 大小寫不同，查到 0 chunks
```

---

## 1-3  替換點 1a：加入你的網站規則

打開 [`scripts/site_rules.py`](../../scripts/site_rules.py)，在 `SITE_RULES` 裡新增：

```python
SITE_RULES: dict[str, dict] = {
    "nextjs.org": { ... },   # 原有的，保留不動
    "react.dev":  { ... },   # 原有的，保留不動

    # ↓ 加你的
    "docs.fastapi.tiangolo.com": {
        "main_selector":    "article",
        "remove_selectors": ["nav", ".md-sidebar", ".md-header"],
        "wait_selector":    "article",
    },
}
```

**怎麼找到正確的 selector**：
1. 用 Chrome 開目標頁面
2. 按 F12 開 DevTools
3. 點左上角的「選取元素」工具（或按 Ctrl+Shift+C）
4. 點擊文章主體
5. 右鍵 HTML 節點 → Copy → Copy selector

---

## 1-4  替換點 1b：建立你的知識庫

根據你的來源格式選對應指令：

**網站**
```bash
python scripts/crawl_to_markdown.py \
  --urls https://docs.fastapi.tiangolo.com/tutorial/first-steps/ \
         https://docs.fastapi.tiangolo.com/tutorial/path-params/ \
         https://docs.fastapi.tiangolo.com/tutorial/query-params/ \
  --out  docs/RAG/crawled/fastapi/ \
  --category fastapi

# 先看看 .md 檔案內容對不對
ls docs/RAG/crawled/fastapi/
cat docs/RAG/crawled/fastapi/docs_fastapi_tiangolo_com__tutorial_first_steps.md | head -50

# 確認沒問題後入庫
python scripts/ingest.py \
  --source docs/RAG/crawled/fastapi/ \
  --type markdown --category fastapi
```

**PDF**
```bash
python scripts/ingest.py \
  --source docs/RAG/labor-standards-act.pdf \
  --type pdf --category labor_law
```

**CSV**（例：藥物交互作用資料庫）

```bash
# CSV 格式範例
# drug_a,drug_b,severity,description,reference
# 阿斯匹靈,布洛芬,moderate,合併使用可能增加腸胃出血風險,DOI:xxx

python scripts/ingest.py \
  --source docs/RAG/drug-interactions.csv \
  --type csv \
  --category drug_interaction \
  --text-columns "drug_a,drug_b,description"
```

---

## 1-5  驗證：至少 30 個 chunk

```bash
python -c "
import asyncio
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient
async def main():
    rows = await SupabaseRestClient(Settings()).select(
        'private_knowledge', {'select': 'id', 'category': 'eq.YOUR_CATEGORY'})
    print(f'chunks: {len(rows)}')
asyncio.run(main())
"
```

30 個 chunk 是 eval 的最低要求。不到 30 個的常見解法：
- 多抓幾頁（加更多 URL）
- 加入另一種格式（官網 + PDF 並行）
- 把 `max_chars` 從 1200 降到 600，讓每份文件切更多 chunk

---

## Eval Gate 1

```
✅ chunks >= 30
✅ 用 L2 Ch04 的 search() 查詢一個標準問題，top-1 score > 0.04
```

下一章 → [Ch 02：Skill 定義](ch02-skills.md)
