# Ch 07：多格式 + 人工介入

> **本章對應**：[task-24](../ai-agent/tasks/task-24-hitl.md)（HITL）+
> [task-25](../ai-agent/tasks/task-25-multi-format-ingestion.md)（Multi-format Ingestion）
>
> **本章目標**：讓知識庫能吃進 PDF 和 CSV，並讓高風險回答在送出前等人工確認。
>
> 🔗 **延伸閱讀**：HITL 真實 production 流程（`hitl_pending_reviews` schema、`_is_interrupted` 偵測、`mark_pending_review`、`make_route_after_judge` 的 HARD_MAX 保險、既有 [`scripts/review_queue.py`](../../scripts/review_queue.py) CLI 用法）見 [Lesson 5 Ch 08：Judge + Reflection 迴圈 + HITL](../Lesson_5_Production/ch08-judge-hitl.md)；checkpointer 三後端（memory / sqlite / postgres）的 async lifespan 整合見 [Lesson 5 Ch 10 §Step 1-2](../Lesson_5_Production/ch10-deployment-pitfalls.md#step-1build_checkpointer--三種後端)。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ 把 PDF / CSV 入庫，並且 citation 有頁碼              ║
║  ✅ 高分風險回答暫停等待，人工 approve / revise / drop   ║
║  ✅ 能解釋 LangGraph interrupt_before 怎麼運作           ║
╚══════════════════════════════════════════════════════════╝
```

---

## 7-1  問題：知識庫只能吃 Markdown

目前的 `ingest_markdown.py` 只能處理 `.md` 檔。
但現實中，知識來源有各種格式：

```
藥品仿單 → PDF（有頁碼）
副作用資料庫 → CSV（有欄位）
法條全文 → PDF（多層章節）
課程教材 → Markdown（已處理）
```

如果不能把 PDF/CSV 入庫，你的知識庫永遠不夠完整。

---

## 7-2  Document 中介格式：統一所有來源

**核心設計**：無論來源是什麼格式，先轉成 `Document`，再走同一條 chunk → embed → store 流程。

```python
# app/ingest/base.py
from pydantic import BaseModel

class Document(BaseModel):
    content:        str
    source_url:     str
    title:          str
    category:       str
    page_number:    int | None = None   # PDF 才有
    row_index:      int | None = None   # CSV 才有
    extra_metadata: dict = {}

class Ingester(Protocol):
    def ingest(self, source: str, category: str) -> list[Document]: ...
```

每個 Ingester 把不同格式轉成 `list[Document]`，後面的 chunker 不需要知道來源格式。

---

## 7-3  PDF Ingester

```python
# app/ingest/pdf_ingester.py
import pypdf   # pip install pypdf

class PdfIngester:
    def ingest(self, source: str, category: str) -> list[Document]:
        reader = pypdf.PdfReader(source)
        docs = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if len(text.strip()) < 50:   # 跳過空頁 / 純圖片頁
                continue
            
            docs.append(Document(
                content=text,
                source_url=source,
                title=f"{source} — page {page_num}",
                category=category,
                page_number=page_num,
            ))
        
        return docs
```

入庫指令：

```bash
python scripts/ingest.py \
  --source docs/RAG/drug-manual.pdf \
  --category drug_info \
  --type pdf
```

---

## 7-4  CSV Ingester

```python
# app/ingest/csv_ingester.py
import csv

class CsvIngester:
    def __init__(self, text_columns: list[str], metadata_columns: list[str] = None):
        self._text_cols = text_columns
        self._meta_cols = metadata_columns or []
    
    def ingest(self, source: str, category: str) -> list[Document]:
        docs = []
        with open(source, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                text = "\n".join(
                    f"{col}: {row[col]}"
                    for col in self._text_cols
                    if col in row and row[col]
                )
                if not text.strip():
                    continue
                
                docs.append(Document(
                    content=text,
                    source_url=source,
                    title=f"{source} — row {idx+1}",
                    category=category,
                    row_index=idx,
                    extra_metadata={c: row.get(c, "") for c in self._meta_cols},
                ))
        return docs
```

入庫指令：

```bash
python scripts/ingest.py \
  --source docs/RAG/drug-interactions.csv \
  --category drug_interaction \
  --type csv \
  --text-columns "drug_a,drug_b,interaction_description" \
  --metadata-columns "severity,reference_url"
```

---

## 7-5  頁碼 Citation：讓使用者知道答案來自哪一頁

`Document.page_number` 存進 chunk metadata 後，Generate 節點可以在回答裡加入來源頁碼：

```python
# generate_node 裡，建構 context 時加入頁碼
def build_context_with_citation(chunks: list[KnowledgeChunk]) -> str:
    parts = []
    for c in chunks:
        citation = f"[p.{c.page_number}]" if c.page_number else "[網頁]"
        parts.append(f"{citation} {c.content}")
    return "\n\n".join(parts)
```

回答效果：

```
根據藥品仿單（p.12），布洛芬的成人建議劑量為每次 400mg。
請注意副作用說明在 p.23，服用前建議閱讀。
```

---

## 7-6  HITL：為什麼需要人工介入？

某些回答即使 judge 給了高分，也不應該自動送出。

**例子**：

```
使用者：「我胸口悶，可以吃什麼藥？」
judge 分數：groundedness=0.9, overall=0.87  ← 高分

但這是緊急醫療症狀，不應該讓 bot 自動回答！
```

---

**HITL 的設計**：在 push 之前加一個「暫停點」，等人工決定。

```
judge → route_after_judge
    → "hitl_required"（高風險條件觸發）
           ↓
    [interrupt_before: push]  ← graph 暫停在這裡
           ↓
    人工收到通知（LINE 管理員 / Web UI）
           ↓
    approve → push（送出原始回答）
    revise  → 人工改好再 push
    drop    → 不送出（通知使用者「感謝，人工會跟進」）
```

---

## 7-7  LangGraph interrupt_before

> 📘 本節示範教學版的 interrupt + resume。Production 版本（含 `_is_interrupted(graph, config)`、`mark_pending_review` 落庫 audit、`reviewer_decision` 寫入 state 與 `ainvoke(None)` resume）的完整實作見 [Lesson 5 Ch 08 §Step 8](../Lesson_5_Production/ch08-judge-hitl.md#step-8hitl-流程--interrupt--resume)。

LangGraph 的 `interrupt_before` 讓 graph 在指定節點前暫停，等外部 resume：

```python
# 建構時加入 checkpointer（儲存 graph 狀態）
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

graph = build_reflection_graph(services).compile(
    checkpointer=checkpointer,
    interrupt_before=["human_review"],  # 只有路由到 human_review 的路徑才會暫停
)
```

> ⚠️ **interrupt_before 是 compile-time 設定，不是 runtime 條件。**
>
> 你在 `compile()` 時決定哪些節點名稱會觸發暫停——這個清單是固定的。
> 動態的「要不要進 HITL」邏輯必須寫在 routing function 裡：
> 只有當 `route_after_judge` 回傳 `"human_review"` 時，graph 才會走到這個節點並暫停。
> 直接路由到 `"push"` 的路徑不受 interrupt 影響，繼續正常執行。

---

### 暫停 + 繼續的流程

```python
# 1. 啟動 graph（路由到 human_review 節點時暫停）
thread_config = {"configurable": {"thread_id": user_id}}

state = await graph.ainvoke(
    {"user_input": message, "external_user_id": user_id, "channel": channel, ...},
    config=thread_config,
)
# graph 暫停在 human_review 之前，state 儲存到 checkpointer

# 2. 人工審查（通常在另一個 webhook 或 Web UI 觸發）
# 人工看到 state["responses"][-1]，決定 approve / revise / drop

# 3a. Approve（原樣送出）
await graph.ainvoke(None, config=thread_config)   # 繼續執行，human_review → push

# 3b. Revise（修改後送出）
await graph.aupdate_state(
    config=thread_config,
    values={"responses": [revised_text]},
)
await graph.ainvoke(None, config=thread_config)   # human_review → push（用修改後的回答）

# 3c. Drop（不送出）
# 做法：把決定寫進 state，讓 graph 繼續跑到 push_node，
# 但 push_node 看到 hitl_decision == "drop" 就改發「感謝」通知，不送出原始回答
await graph.aupdate_state(
    config=thread_config,
    values={"hitl_decision": "drop"},
)
await graph.ainvoke(None, config=thread_config)   # push_node 會發「感謝跟進」通知後結束
```

push_node 裡加一個判斷：

```python
async def push_node(state: RAGState, services: RuntimeServices) -> dict:
    if state.get("hitl_decision") == "drop":
        # 通知使用者「人工跟進」，不送出原始 AI 回答
        await services.channel.push_text(
            state["external_user_id"],
            ["感謝提問，我們的專家會儘快跟進。"],
        )
        return {}
    # 正常路徑：送出 AI 回答
    for text in state["responses"]:
        await services.channel.push_text(state["external_user_id"], [text])
    return {}
```

> 💡 **為什麼不能直接「放棄」thread，不 resume？**
>
> `SqliteSaver` / `PostgresSaver` 沒有「刪除 thread」的 API。
> 讓 interrupted thread 永遠留在 pending 狀態，會讓 `/api/review/pending` 越積越多。
> 推薦做法：永遠 resume（即使是 drop），讓 graph 走到 `END`，checkpointer 標記為 completed。

---

## 7-8  HITL 觸發條件

不是所有回答都需要人工介入。觸發條件寫成一個純函式，**供 routing function 呼叫**：

```python
# app/graph/hitl.py
def should_trigger_hitl(state: RAGState, settings: Settings) -> bool:
    judge_score = state.get("judge_score")

    # 條件 1：skill 標記為 always_hitl（例如：醫療緊急、法律建議）
    skill = state.get("skill")
    if skill and getattr(skill, "always_hitl", False):
        return True

    # 條件 2：judge 分數低但超過 HARD_MAX（勉強通過的回答）
    retry_count = state.get("reflection_retry", 0)
    if judge_score and not judge_score.pass_threshold and retry_count >= HARD_MAX:
        return True

    # 條件 3：特定關鍵詞（緊急症狀、法律責任）
    urgent_keywords = settings.hitl_urgent_keywords  # ["胸痛", "呼吸困難", ...]
    if any(kw in state["user_input"] for kw in urgent_keywords):
        return True

    return False
```

這個函式**不能獨立觸發 interrupt**——它只是一個布林判斷。
實際串接方式：在 `make_route_after_judge`（Ch04）的 routing function 裡呼叫它：

```python
# app/graph/nodes.py（在 Ch04 的 make_route_after_judge 基礎上擴充）
def make_route_after_judge(
    max_retries: int,
    *,
    hitl_enabled: bool = False,
    settings: Settings | None = None,
) -> Callable[[RAGState], str]:
    def route_after_judge(state: RAGState) -> str:
        score       = state["judge_score"]
        retry_count = state.get("reflection_retry", 0)
        effective_max = min(max(max_retries, 0), HARD_MAX)

        if score.pass_threshold:
            # 分數夠：還要檢查 HITL 條件（如 always_hitl skill）
            if hitl_enabled and settings and should_trigger_hitl(state, settings):
                return "human_review"
            return "push"

        if retry_count >= effective_max:
            # 達到重試上限：分數仍不夠
            if hitl_enabled and settings and should_trigger_hitl(state, settings):
                return "human_review"
            return "push"   # 強制送出（已盡力）

        return "reflect"

    return route_after_judge

# graph 組裝
route_fn = make_route_after_judge(
    max_retries=2,
    hitl_enabled=settings.hitl_enabled,
    settings=settings,
)
g.add_conditional_edges(
    "judge",
    route_fn,
    {"push": "push", "reflect": "reflect", "human_review": "human_review"},
)
g.add_edge("human_review", "push")   # human_review 只是暫停點，繼續走到 push
```

`interrupt_before=["human_review"]` 讓 graph 在進入 `human_review` 節點前暫停——
路由到 `"push"` 的路徑完全不受影響，繼續正常執行。

---

## 7-9  Review Queue（管理介面）

> 💡 本節示範一個自寫 review queue HTTP endpoint。本專案已備好 CLI 版本 [`scripts/review_queue.py`](../../scripts/review_queue.py)（spec-21 / task-21 步驟 6），用 checkpointer 列出 `next=human_review` 的 thread、approve / revise / drop 都直接 resume graph。下方教學版用 HTTP，產品版用 CLI——兩條軸都用得上。完整解說見 [Lesson 5 Ch 08 §Step 10](../Lesson_5_Production/ch08-judge-hitl.md#step-10-啟用-hitl--寫-review-cli)。

人工審查需要一個地方看到等待中的回答：

```python
# app/api/review_queue.py

@router.get("/api/review/pending")
async def list_pending():
    """列出所有等待人工審查的對話"""
    pending = checkpointer.list({"status": "interrupted"})
    return [
        {
            "thread_id":   p.config["configurable"]["thread_id"],
            "user_input":  p.values["user_input"],
            "response":    p.values["responses"][-1],
            "judge_score": p.values.get("judge_score"),
        }
        for p in pending
    ]

@router.post("/api/review/{thread_id}/approve")
async def approve(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    await graph.ainvoke(None, config=config)
    return {"status": "approved"}

@router.post("/api/review/{thread_id}/revise")
async def revise(thread_id: str, body: ReviseRequest):
    config = {"configurable": {"thread_id": thread_id}}
    await graph.aupdate_state(config, values={"responses": [body.revised_text]})
    await graph.ainvoke(None, config=config)
    return {"status": "revised"}

@router.post("/api/review/{thread_id}/drop")
async def drop(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    # 把 drop 決定寫進 state，再 resume；push_node 會發「感謝跟進」通知後走到 END
    await graph.aupdate_state(config, values={"hitl_decision": "drop"})
    await graph.ainvoke(None, config=config)
    return {"status": "dropped"}
```

完整範例見 [hitl-walkthrough.md](../ai-agent/examples/hitl-walkthrough.md)。

---

## ✏️ 本章任務

1. 完成 task-25（`PdfIngester` + `CsvIngester` + `Document` 中介格式）
2. 把你領域的至少一份 PDF 入庫，確認 `page_number` 存進 chunk metadata
3. 完成 task-24（HITL 觸發條件 + `interrupt_before` + review queue）
4. 測試 approve / revise / drop 三條路徑（可用 HTTP adapter + curl）
5. 在 `WEEK7.md` 記錄：你的領域哪些 skill 需要設 `always_hitl=True`？

---

## 📝 沒有蠢問題

**Q：interrupt_before 的 checkpointer 存在哪裡？生產環境用什麼？**

A：本地開發用 `SqliteSaver`（一個 .db 檔）。
生產環境建議用 `PostgresSaver`（Supabase 的 PostgreSQL 就行）。
切換只需要改 `checkpointer` 的初始化，graph 邏輯不用動。

**Q：使用者等人工審查，要等多久？LINE 超時怎麼辦？**

A：LINE 的 webhook 必須在 **30 秒內** 回應 200 OK，否則重試。
但 push message API 沒有時間限制——你可以等 10 分鐘後再 push。
所以：webhook 收到訊息後立刻回 200，再讓 graph 在背景執行（async）。
人工審查後再用 push API 送出，不會有超時問題。

**Q：PDF 裡有圖片（掃描版），怎麼辦？**

A：`pypdf` 無法提取掃描版 PDF 的文字，需要 OCR。
推薦 `pytesseract` 或 AWS Textract（付費但更準）。
掃描版 PDF 是 Ch07 的進階選項，不是必要條件。

---

## 🧠 腦力激盪

> 你的領域的 CSV 資料，哪些欄位應該合成 `content`，哪些應該放進 `extra_metadata`？
>
> 例如藥物交互作用 CSV：
> ```
> drug_a, drug_b, interaction_description, severity, reference_url
> ```
> - `content` → drug_a + drug_b + interaction_description（讓語意搜尋能找到）
> - `extra_metadata` → severity + reference_url（附加資訊，不影響向量距離）
>
> 如果把 severity 也放進 content，可能讓「嚴重的交互作用」被優先找到——
> 這對你的領域是好事還是壞事？

---

## 🎯 本章里程碑

```
一份你領域的 PDF 已入庫，citation 包含頁碼。
HITL 能成功 approve 一條回答，並 push 到使用者（或 HTTP endpoint）。
drop 一條回答，使用者收到「人工跟進」通知。
```

---

上一章 → [Ch 06：解耦 channel + store](ch06-channel-store.md)

---

## 接下來

讀完整個 Lesson 3 後若要把 reflection agent 上 production，建議讀 [Lesson 5：Production 化](../Lesson_5_Production/README.md)：

- [Ch 08：Judge + Reflection 迴圈 + HITL](../Lesson_5_Production/ch08-judge-hitl.md) — 本章 HITL 教學版的 production 對應，含 `hitl_pending_reviews` opt-in 表、`HARD_MAX` retry 保險、reflection variant 完整 graph 組裝
- [Ch 09：觀測 + 安全 Guards](../Lesson_5_Production/ch09-observability-security.md) — Tracer、token cost、JSON logging、prompt injection 防禦
- [Ch 10：Checkpoint / Cache / 成本 / 部署清單](../Lesson_5_Production/ch10-deployment-pitfalls.md) — checkpointer 後端選擇、12 條地雷集
下一章 → [Ch 08：Capstone 整合](ch08-capstone.md)
