# Ch 05：Eval Gate — 最終驗收

> 核心檔案：[`tests/cases/golden.yaml`](../../tests/cases/)、
> [`scripts/eval.py`](../../scripts/eval.py)

---

## 5-1  為什麼需要 Eval Gate？

四個替換點做完，bot 能動了——但「能動」不等於「夠好」。

Eval Gate 把「感覺不錯」變成可量化的數字：

```
換領域前（nextjs）：chunk_recall=0.81  clarify_accuracy=0.92  forbidden_phrase_rate=0.00
換領域後（你的）：  chunk_recall=?     clarify_accuracy=?     forbidden_phrase_rate=?
```

如果你的數字比這個差很多，說明哪個步驟出問題了。

---

## 5-2  建立你的 `golden.yaml`

在 `tests/cases/` 建立你的領域的 golden case 檔案，至少 12 個 case（4 種類型各 3 個）。

**格式說明**（對照現有的 nextjs 範例修改）：

```yaml
# tests/cases/golden_your_domain.yaml

# 類型 1：faq — 知識庫有直接答案的標準問題
- id: faq_001
  type: faq
  query: "FastAPI 的 path parameter 怎麼定義？"
  expected_chunks:
    - "docs.fastapi.tiangolo.com__tutorial_path_params#px#c1"   # 你的真實 chunk ID
  expected_answer_contains:
    - "Path"
    - "int"
    - "@app.get"
  should_clarify: false

# 類型 2：multi_condition — 跨多個 chunk 的複合問題
- id: multi_001
  type: multi_condition
  query: "FastAPI 配合 SQLAlchemy async session 的 dependency injection 怎麼寫？"
  expected_chunks:
    - "docs.fastapi.tiangolo.com__tutorial_dependencies#px#c2"
    - "docs.fastapi.tiangolo.com__tutorial_sql_databases#px#c1"
  expected_answer_contains:
    - "Depends"
    - "AsyncSession"
  should_clarify: false

# 類型 3：knowledge_gap — 知識庫完全沒有，應該觸發 clarify
- id: gap_001
  type: knowledge_gap
  query: "Django REST Framework 的 serializer 怎麼用？"  # ← 不在你的 KB 裡
  expected_chunks: []
  expected_answer_contains: []
  should_clarify: true

# 類型 4：grounding_check — 驗證不幻覺
- id: ground_001
  type: grounding_check
  query: "FastAPI 支援 GraphQL 嗎？"
  expected_chunks:
    - "docs.fastapi.tiangolo.com__advanced_graphql#px#c1"
  expected_answer_contains: []
  forbidden_phrases:
    - "FastAPI 原生支援 GraphQL"     # ← 如果知識庫說需要 strawberry，不應該說「原生支援」
  should_clarify: false
```

---

## 5-3  怎麼找 `expected_chunks` 的真實 ID？

```python
import asyncio
from app.config import Settings
from app.ai.providers.openai_provider import OpenAIEmbedder
from app.storage.supabase_client import SupabaseRestClient
from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.stores.supabase_store import SupabaseStore
from app.storage.knowledge_store import SearchFilters

async def find_chunk_ids(query: str, category: str):
    settings = Settings()
    store = SupabaseStore(
        client=SupabaseRestClient(settings),
        repo=KnowledgeRepository(SupabaseRestClient(settings)),
    )
    vec    = await OpenAIEmbedder(settings).embed_query(query)
    chunks = await store.search(
        query_embedding=vec,
        query_text=query,
        filters=SearchFilters(categories=[category]),
        top_k=5,
    )
    for c in chunks:
        print(f"id={c.id}  score={c.combined_score:.4f}")
        print(f"   {c.content[:80]}...")

asyncio.run(find_chunk_ids("path parameter 怎麼定義", "fastapi"))
```

輸出裡的 `id` 就是你要填進 `expected_chunks` 的值。

---

## 5-4  跑 Eval

```bash
# 三個 variant 都跑，輸出到報告
python scripts/eval.py \
  --cases tests/cases/golden_your_domain.yaml \
  --variants basic selfrag reflection \
  --output reports/eval_YOUR_DOMAIN.md
```

輸出範例：

```markdown
# Eval Report — fastapi bot — 2026-05-06

## 環境
- Provider: OpenAI gpt-4.1-mini + text-embedding-3-small
- KB chunks (fastapi): 47
- Golden cases: 12 (faq×3, multi×3, gap×3, grounding×3)

## 結果

| metric                | basic  | selfrag | reflection |
|-----------------------|--------|---------|-----------|
| chunk_recall          | 0.44   | 0.78    | 0.78      |
| clarify_accuracy      | 0.58   | 0.89    | 0.89      |
| groundedness_score    | N/A    | N/A     | 0.91      |
| forbidden_phrase_rate | 0.33   | 0.11    | 0.00      |
| latency_p50 (ms)      | 750    | 2300    | 5100      |
| cost_per_query (USD)  | 0.0003 | 0.0011  | 0.0025    |
```

---

## 5-5  通過門檻 vs 失敗時的診斷

**必過門檻**（任一失敗 = 需要修正）：

| 門檻 | 失敗時的診斷 |
|------|------------|
| `chunk_recall (selfrag) ≥ 0.60` | KB 太少（加更多文件）或 feature extractor 沒抓到 entities |
| `clarify_accuracy ≥ 0.75` | Sufficiency Check 門檻需要調整（[L3 Ch03](../Lesson_3_LangGraph_RAG/ch03-sufficiency-generation.md)） |
| `forbidden_phrase_rate (reflection) = 0.00` | Judge prompt 需要加強，或 grounding_check cases 的 forbidden_phrases 不夠精確 |

**常見失敗模式與修法**：

```
chunk_recall 低（< 0.50）
  → 先確認 expected_chunks 的 ID 是不是真的存在
  → python -c "asyncio.run(find_chunk_ids(...))" 確認能找到

clarify_accuracy 低（gap 類問題沒有 clarify）
  → min_top_score 太低，調高（0.65 → 0.70）
  → min_chunks 太低，調高（2 → 3）

clarify_accuracy 低（faq 類問題誤觸 clarify）
  → min_top_score 太高，調低（0.70 → 0.60）
  → 或 KB chunk 品質問題：重新 ingest，確認 embedding 有效

forbidden_phrase_rate > 0 in reflection
  → 加強 judge prompt：明確列出 forbidden_phrases 類型
  → 或在 grounding_check case 裡補更多 forbidden_phrases
```

---

## 5-6  Capstone 自評清單

```
知識庫
  □ ≥ 30 個你自己領域的 chunk（Eval Gate 1）
  □ 至少一個非 markdown 格式（PDF 或 CSV）

Skill
  □ ≥ 1 個你自己領域的 skill（Eval Gate 2）
  □ curl /api/chat 能 routing 到你的 skill

Feature Extractor
  □ 5 個真實問題 entities 正確（Eval Gate 3）

Channel
  □ 選好一個 channel，end-to-end 能收到回覆（Eval Gate 4）

Eval
  □ golden.yaml 有 12 個 case（faq/multi/gap/grounding 各 3）
  □ 三個必過門檻全達成
  □ reports/eval_YOUR_DOMAIN.md 有完整數字
```

---

## 🎯 Lesson 4 里程碑

```
用你自己的領域問一個複合條件問題：
  - selfrag 版本找到的 chunk 比 basic 多
  - reflection 版本的 forbidden_phrase_rate = 0
  - 整個 eval 跑通，報告有數字

這就是一個可以上線的 domain-specific AI bot。
```
