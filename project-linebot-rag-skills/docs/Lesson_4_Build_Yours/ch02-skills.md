# Ch 02：替換點 2 — Skill 定義

> 核心檔案：[`skills/tech-architect/SKILL.md`](../../skills/tech-architect/SKILL.md)（現有範例）、
> [`app/skills/loader.py`](../../app/skills/loader.py)、
> [`scripts/seed_skills.py`](../../scripts/seed_skills.py)

---

## 2-1  Skill 是什麼？

Skill 告訴 router 三件事：

1. **什麼情況下用我**（`use_when`）
2. **從哪些 category 的 chunk 找資料**（`rag_categories`）
3. **用什麼語氣和格式回答**（`system_prompt`）

---

## 2-2  看現有的 `tech-architect` 範例

[`skills/tech-architect/SKILL.md`](../../skills/tech-architect/SKILL.md)：

```markdown
---
skill_id: tech_architect
name: 技術架構師
category: engineering
version: 0.1.0
description: 用於系統架構、RAG、API、部署、技術選型分析。
use_when:
  - 使用者詢問系統設計
  - 使用者詢問 Supabase、FastAPI、LINE Bot、RAG
avoid_when:
  - 使用者只是情緒抒發
  - 使用者需要行銷文案
default_temperature: 0.3
rag_categories:
  - engineering
  - architecture
  - code
  - rag
---

你是一位技術架構師。回答時請遵守：

1. 回答要可落地，不做空泛建議。
2. 若 RAG context 不足，明確說「目前知識庫不足」。
3. 若有風險，列出風險與緩解方式。
```

**注意**：`rag_categories` 裡的值（`engineering`、`architecture`...）
必須和 `private_knowledge.category` 的實際值對齊。

**快速確認對齊**：

```bash
# 查 KB 裡有哪些 category
python -c "
import asyncio
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient
async def main():
    rows = await SupabaseRestClient(Settings()).select(
        'private_knowledge', {'select': 'category'})
    for c in sorted(set(r['category'] for r in rows)):
        print(c)
asyncio.run(main())
"

# 把輸出的 category 值填進你的 SKILL.md rag_categories
```

如果 `rag_categories` 和 KB category 不一致，router 找到你的 skill 後
retriever 仍會回傳 0 chunks，bot 會誠實說「我不知道」——
但你不會看到任何錯誤訊息，這是最容易卡住的地方。

---

## 2-3  建立你的 Skill 目錄

先看一下現有的範例目錄結構：

```
skills/
├── tech-architect/          ← 現有示範 skill
│   └── SKILL.md             ← 唯一必要的檔案
└── your-domain/             ← 你要建的
    └── SKILL.md
```

```bash
# 確認現有結構
ls skills/tech-architect/

# 建立你的
mkdir -p skills/your-domain/
```

`skills/` 目錄下每個子目錄就是一個 skill。
`seed_skills.py` 會遞迴掃描所有子目錄的 `SKILL.md`，不需要手動登記。

建立 `skills/your-domain/SKILL.md`。以下提供三個領域的範本：

---

### 範本 A：技術文件 bot（FastAPI）

```markdown
---
skill_id: fastapi_guide
name: FastAPI 教學助理
category: webdev
version: 0.1.0
description: 回答 FastAPI 路由、依賴注入、非同步、部署相關問題。
use_when:
  - 使用者問 FastAPI 怎麼用
  - 使用者問 Pydantic、uvicorn、starlette
  - 使用者遇到 HTTP exception / validation error
avoid_when:
  - 使用者問和 FastAPI 完全無關的事
  - 使用者在情緒抒發
default_temperature: 0.3
rag_categories:
  - fastapi        ← 和你的 ingest --category 完全一致
---

你是一位 FastAPI 專家助理。回答時：

1. 優先給出可以直接執行的程式碼範例。
2. 若知識庫沒有相關資料，誠實說「我不確定」，不要捏造。
3. 涉及版本差異時，明確標出 FastAPI 版本。
```

---

### 範本 B：法規查詢 bot（勞基法）

```markdown
---
skill_id: labor_law_faq
name: 勞基法小幫手
category: legal
version: 0.1.0
description: 回答台灣勞動基準法的常見問題，例如工時、資遣費、休假規定。
use_when:
  - 使用者詢問工時、加班費、特休、資遣
  - 使用者問勞工權益或雇主義務
  - 使用者引用法條號碼（例：第 24 條、第 38 條）
avoid_when:
  - 使用者詢問其他國家的法律
  - 使用者要求我提供法律意見（建議諮詢律師）
default_temperature: 0.2      ← 法規類建議低溫度（更確定性）
rag_categories:
  - labor_law
---

你是一位勞動法規查詢助理。回答時：

1. 引用法條時，標明條號（例：依勞基法第 24 條）。
2. 若問題涉及個案判斷，建議使用者諮詢專業律師。
3. 若知識庫沒有明確答案，說「這個問題需要查閱更多法規」，不要推測。
4. 回答保持中立，不偏向勞方或資方。
```

---

### 範本 C：醫療資訊 bot（需要 HITL）

```markdown
---
skill_id: drug_info
name: 藥物資訊查詢
category: medical
version: 0.1.0
description: 查詢藥品用法、劑量、禁忌症、交互作用。
use_when:
  - 使用者詢問藥品名稱
  - 使用者詢問副作用、交互作用
  - 使用者問「可以和 X 一起吃嗎」
avoid_when:
  - 使用者描述緊急症狀（應走 triage skill）
  - 使用者要求診斷
default_temperature: 0.1      ← 醫療類用最低溫度
rag_categories:
  - drug_info
  - drug_interaction
---

你是藥物資訊查詢助理。回答時：

1. 只引用知識庫裡有的資料，不補充個人推測。
2. 每個回答加上：「以上資訊僅供參考，用藥前請諮詢醫師或藥師。」
3. 涉及劑量時，必須標明適用對象（成人/兒童/老年人）。
4. 若使用者描述緊急症狀，立刻說「請立即就醫或撥打 119」。
```

---

## 2-4  種入 Supabase

```bash
# 把 skills/ 目錄下所有 SKILL.md 種入 ai_skills 表
python scripts/seed_skills.py

# 確認已種入
python -c "
import asyncio
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient
async def main():
    rows = await SupabaseRestClient(Settings()).select('ai_skills', {'select': 'skill_id,name'})
    for r in rows: print(r)
asyncio.run(main())
"
```

---

## 2-5  驗證 router 能認出你的 skill

啟動 server 後，用 `curl` 測試：

```bash
./scripts/run_local.sh &

curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "FastAPI 的 path parameter 怎麼定義？", "user_id": "test"}' \
  | python -m json.tool
```

看 log 裡的 `routing → <skill_id>` 是否對應到你新建的 skill：

```
INFO  routing → fastapi_guide   ← ✅ 對了
INFO  routing → general_chat    ← ❌ 沒認出來，檢查 use_when
```

如果 router 一直走 `general_chat`，加強 `use_when` 的描述（更具體的觸發條件）。

---

## Eval Gate 2

```
✅ seed_skills.py 跑通，ai_skills 表有你的 skill
✅ curl /api/chat 問一個和你 skill 相關的問題，log 顯示 routing → your_skill_id
```

下一章 → [Ch 03：Feature Extractor](ch03-feature-extractor.md)
