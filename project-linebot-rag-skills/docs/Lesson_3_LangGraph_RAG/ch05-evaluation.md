# Ch 05：量化 + 觀測

> **本章對應**：[task-19](../ai-agent/tasks/task-19-eval-framework.md)（Evaluation Framework）+
> [task-20](../ai-agent/tasks/task-20-observability.md)（Observability）
>
> **本章目標**：把「感覺好像有改善」變成「數字證明改善了多少」。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ 有一份 golden case set，覆蓋四種問題類型             ║
║  ✅ 三個變體的 6 個 metric 都有數字                      ║
║  ✅ 每次 query 的成本和 latency 都有 log                 ║
╚══════════════════════════════════════════════════════════╝
```

---

## 5-1  問題：你怎麼知道 reflection 真的有改善？

前四章做了很多改進：multi-seed、sufficiency check、two-stage、reflection loop。
但你怎麼知道這些改進有沒有用？

目前你的答案可能是：
```
「感覺好像有改善，judge 的分數比較高了」
```

這不夠好。**感覺不是數據**，你需要：

```
1. 固定的測試題目（golden case set）
2. 固定的評分標準（6 個 metric）
3. 三個變體都跑一遍，做比較
```

---

## 5-2  Golden Case Set：你的考試卷

Golden case set 是一組**人工標注的問答對**，用來評估系統表現。

每個 golden case 長這樣：

```yaml
# tests/cases/golden.yaml

- id: faq_001
  type: faq
  query: "Next.js 14 的 App Router 和 Pages Router 有什麼不同？"
  expected_chunks: ["chunk_appdir_001", "chunk_pages_002"]
  expected_answer_contains: ["App Router", "server-side", "file-based routing"]
  ground_truth: "App Router 是 Next.js 13+ 的新路由系統，基於 React Server Components..."
  should_clarify: false

- id: multi_001
  type: multi_condition
  query: "在 Vercel 部署 Next.js 14 時，Server Components 的快取策略怎麼設定？"
  expected_chunks: ["chunk_vercel_003", "chunk_cache_007", "chunk_sc_002"]
  expected_answer_contains: ["cache", "revalidate", "Vercel edge"]
  ground_truth: "..."
  should_clarify: false

- id: gap_001
  type: knowledge_gap
  query: "Kubernetes HPA 的 cooldown period 預設是幾秒？"
  expected_chunks: []
  expected_answer_contains: []
  ground_truth: null
  should_clarify: true   # ← 這題應該觸發 clarify

- id: ground_001
  type: grounding_check
  query: "Next.js 的 getServerSideProps 在 App Router 裡怎麼用？"
  expected_chunks: ["chunk_migration_001"]
  expected_answer_contains: []
  ground_truth: "getServerSideProps 不存在於 App Router，需要改用..."
  should_clarify: false
  forbidden_phrases: ["getServerSideProps 在 App Router 裡可以直接用"]
```

---

### 四種問題類型

```
╔══════════════════════════════════════════════════════════╗
║  type: faq            → 知識庫有直接答案的標準問題       ║
║  type: multi_condition → 跨多個 chunk 的複合問題         ║
║  type: knowledge_gap  → 知識庫沒有答案（應該 clarify）   ║
║  type: grounding_check → 驗證不幻覺（forbidden_phrases） ║
╚══════════════════════════════════════════════════════════╝
```

每種類型至少 3 個 case，總共 12+ 個。

---

## 5-3  六個 Metric

### Metric 1：chunk_recall

```
問：你的 golden cases 裡標注了「應該撈到哪些 chunk」
   bot 實際撈到了幾個？

chunk_recall = 命中的 expected_chunks 數量 / 全部 expected_chunks 數量
```

```
期望：["chunk_001", "chunk_002", "chunk_003"]
實際：["chunk_001", "chunk_003"]
chunk_recall = 2/3 = 0.67
```

**basic vs selfrag 的差距通常最明顯在這裡。**

---

### Metric 2：clarify_accuracy

```
type=knowledge_gap 的 case，bot 是否正確進入 clarify？
type!=knowledge_gap 的 case，bot 是否正確「不進入」clarify？

clarify_accuracy = 正確分類的 case 數 / 全部 case 數
```

---

### Metric 3：groundedness_score

```
reflection 版本才有
= JudgeScore.groundedness 的平均值（跑過所有 golden cases）
```

---

### Metric 4：forbidden_phrase_rate

```
type=grounding_check 的 case，回答有沒有出現 forbidden_phrases？

forbidden_phrase_rate = 出現 forbidden_phrase 的 case 數 / grounding_check 總數
越低越好，理想是 0.0
```

---

### Metric 5：latency_p50 / latency_p95

```
跑完所有 golden cases，記錄每個 case 的 end-to-end 時間
p50（中位數）：一半 case 比這個快
p95（95th percentile）：95% case 比這個快
```

**三個變體 latency 比較通常長這樣：**

```
basic:      p50=800ms,  p95=1200ms
selfrag:    p50=2500ms, p95=4000ms
reflection: p50=5500ms, p95=9000ms
```

---

### Metric 6：cost_per_query

```
每個 query 平均花多少 API 費用

cost_per_query = 總費用 / query 數量
```

追蹤方法：在每次 LLM 呼叫後記錄 token 數量 × 單價。

---

## 5-4  Eval Runner：自動跑完所有 cases

```bash
# 跑所有 golden case，對比三個變體
python scripts/run_eval.py \
  --cases tests/cases/golden.yaml \
  --variants basic selfrag reflection \
  --output reports/eval_baseline.md
```

輸出範例：

```markdown
# Eval Baseline — 2026-W5

## 環境
- AI Provider: OpenAI gpt-4.1-mini
- 知識庫 chunks: 47
- Golden cases: 12 (faq×3, multi×3, gap×3, grounding×3)

## 結果

| metric                | basic  | selfrag | reflection |
|-----------------------|--------|---------|-----------|
| chunk_recall          | 0.52   | 0.81    | 0.81      |
| clarify_accuracy      | 0.67   | 0.92    | 0.92      |
| groundedness_score    | N/A    | N/A     | 0.88      |
| forbidden_phrase_rate | 0.33   | 0.11    | 0.00      |
| latency_p50 (ms)      | 820    | 2450    | 5680      |
| cost_per_query (USD)  | 0.0004 | 0.0012  | 0.0028    |
```

---

## 5-5  Observability：讓每次 query 都留下足跡

光有 eval 結果不夠——生產環境中你需要知道**每一次 query 發生了什麼**。

### 在 graph 每個節點加 log

```python
import logging
import time

logger = logging.getLogger(__name__)

async def judge_node(state: RAGState, services: RuntimeServices) -> dict:
    start = time.monotonic()
    
    score = await services.judge.evaluate(
        user_input=state["user_input"],
        contract=state["answer_contract"],
        narrative=state["responses"][-1],
        context=state["rag_context"],
    )
    
    elapsed_ms = (time.monotonic() - start) * 1000
    
    logger.info(
        "judge",
        extra={
            "user_id":          state["line_user_id"],
            "overall_score":    score.overall,
            "pass_threshold":   score.pass_threshold,
            "reflection_count": state.get("reflection_count", 0),
            "elapsed_ms":       elapsed_ms,
        }
    )
    
    return {
        "judge_score":      score,
        "reflection_count": state.get("reflection_count", 0),
    }
```

---

### Structured Logging（結構化日誌）

把 log 輸出成 JSON，後面才能用工具查詢：

```python
# app/observability/logger.py
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "time":    self.formatTime(record),
            "level":   record.levelname,
            "event":   record.getMessage(),
        }
        if hasattr(record, "extra"):
            data.update(record.__dict__.get("extra", {}))
        return json.dumps(data, ensure_ascii=False)
```

輸出範例：

```json
{"time": "2026-05-01 10:32:15", "level": "INFO", "event": "judge",
 "user_id": "U_abc123", "overall_score": 0.71, "pass_threshold": false,
 "reflection_count": 0, "elapsed_ms": 1234.5}
```

---

### Cost Tracking（成本追蹤）

```python
# app/observability/cost_tracker.py

PRICE_PER_1K_TOKENS = {
    "gpt-4.1-mini":     {"input": 0.00015, "output": 0.0006},
    "gpt-4.1":          {"input": 0.002,   "output": 0.008},
    "claude-haiku-4-5": {"input": 0.00025, "output": 0.00125},
}

def log_llm_call(model: str, input_tokens: int, output_tokens: int, event: str):
    price = PRICE_PER_1K_TOKENS.get(model, {"input": 0, "output": 0})
    cost = (input_tokens / 1000) * price["input"] + \
           (output_tokens / 1000) * price["output"]
    logger.info(
        "llm_call",
        extra={
            "model":         model,
            "event":         event,
            "input_tokens":  input_tokens,
            "output_tokens": output_tokens,
            "cost_usd":      round(cost, 6),
        }
    )
```

---

## 5-6  解讀你的 baseline 結果

拿到數字後，問自己這幾個問題：

```
1. chunk_recall 的 basic vs selfrag 差距夠大嗎？
   - 差距 <0.1 → multi-seed 沒什麼幫助，可能是知識庫太小
   - 差距 >0.3 → multi-seed 很有效，selfrag 值得維持

2. clarify_accuracy 是否夠高（>0.8）？
   - 偏低 → 調整 min_top_score 或 min_feature_overlap

3. forbidden_phrase_rate 是否已降到 0？
   - reflection 版本還有 forbidden phrase → judge prompt 需要加強

4. reflection 的 latency 你的使用者能接受嗎？
   - LINE Bot 超過 8 秒沒回覆，使用者通常覺得卡死
   - 如果 p95 > 8000ms，考慮 basic/selfrag 而非 reflection

5. 每月成本是否在預算內？
   - cost_per_query × 每日預估 query 數 × 30 天
```

---

## 5-7  Metric 失敗時的調試迴圈

「數字不達標」之後不是重跑，而是按問題追根源：

### chunk_recall(selfrag) < 0.60

```
Step 1：確認 expected_chunks 的 ID 是否真實存在
  python -c "
  import asyncio
  from app.config import Settings
  from app.storage.supabase_client import SupabaseRestClient
  async def check():
      rows = await SupabaseRestClient(Settings()).select(
          'private_knowledge', {'select': 'id', 'id': 'in.(ID1,ID2)'})
      print([r['id'] for r in rows])
  asyncio.run(check())
  "
  → ID 不在結果裡 → golden case 的 expected_chunks 填錯了，先修這個

Step 2：ID 存在但還是沒被 retrieve → Feature Extractor 問題
  → 用 scripts/dump_seeds.py 印出你的問題展開的 seeds
  → 看 seeds 是否包含 expected_chunk 的關鍵詞
  → 不包含 → 加強 LLMFeatureExtractor prompt，或改用 Rule-based

Step 3：seeds 正確但 chunk 沒排到前面 → fusion 策略問題
  → 試換 FUSION_STRATEGY=rrf（如果還在用 max/mean）
  → 或降低 knowledge_top_k（5 → 3），提高召回精準度

Step 4：以上都試過，recall 仍低 → KB 品質問題
  → 增加文件數量，或把 max_chars 從 1200 降到 800，切更細
```

---

### clarify_accuracy < 0.75

```
先看失敗是哪個方向：

A. gap 類問題沒有 clarify（應該問但沒問）
   → Sufficiency Check 太寬鬆
   → 試 SUFFICIENCY_MIN_TOP_SCORE=0.50 → 0.60
   → 試 SUFFICIENCY_MIN_CHUNKS=2 → 3

B. faq 類問題誤觸 clarify（不應該問卻問了）
   → Sufficiency Check 太嚴格
   → 試 SUFFICIENCY_MIN_TOP_SCORE=0.60 → 0.45
   → 或 KB chunk 品質問題：重新 ingest，確認 embedding 有效

每次改一個參數，重跑 eval，記錄變化。
不要同時改兩個——你不會知道是哪個生效。
```

---

### forbidden_phrase_rate(reflection) > 0

```
Step 1：看是哪個 case 觸發 forbidden phrase
  → eval 報告會列出失敗的 case_id

Step 2：看 AnswerContract 裡有沒有那個 phrase
  → 有 → 問題在 Stage 1（contract 引入了幻覺）
     → 加強 CONTRACT_PROMPT：明確說「不得使用 chunks 裡沒有的斷言」
  → 沒有 → 問題在 Stage 2（narrative 自行補充）
     → 加強 NARRATIVE_PROMPT：在「規則」區加入 forbidden_phrases 清單

Step 3：Judge 沒抓到（reflection variant 後仍出現）
  → judge prompt 的 4 個軸都沒覆蓋這個 phrase 類型
  → 針對你的領域加第 5 軸（例如：「領域安全語言」）
```

---

> 💡 **每次 fix 後都要重跑 eval，確認沒有其他 metric 退步。**
> 改善 clarify_accuracy 有時會讓 chunk_recall 下降——這是系統性的 tradeoff，
> 不是 bug。記錄每次的完整數字，不要只看目標 metric。

---

## ✏️ 本章任務

1. 完成 task-19：建 `tests/cases/golden.yaml`（你的領域，12 個 case）
2. 完成 task-20：structured log + cost tracking 加進 judge / generate 節點
3. 跑 `run_eval.py`，填寫 `reports/eval_baseline.md`（見 [eval-baseline.md](../ai-agent/examples/eval-baseline.md) 範本）
4. 找出你的系統最弱的一個 metric，按 5-7 的調試迴圈跑一輪
5. 把數字和結論記在 `WEEK5.md`

---

## 📝 沒有蠢問題

**Q：golden case 要自己寫嗎？很花時間？**

A：是的，需要人工標注。12 個 case 大約 1–2 小時。
這是整個課程最值得投資的時間之一——
有了 golden case，每次改動後就能立刻知道有沒有退步。

**Q：chunk_recall 的 expected_chunks 要怎麼決定？**

A：先跑一次 retriever，看撈到哪些 chunk。
打開 Supabase 找到那幾個 chunk 的 ID。
然後人工確認：這些 chunk 確實是回答這個問題需要的嗎？
加進 `expected_chunks`。

**Q：為什麼只追蹤 6 個 metric？少了很多面向吧？**

A：6 個是最小可行集合，能覆蓋「效果 + 品質 + 性能 + 成本」四個維度。
更多 metric 見 [RAG survey](../rag-theory/rag-survey.md)。
先把 6 個做好，再擴展。

---

## 🧠 腦力激盪

> 你的領域最關心哪個 metric？
>
> 例如：
> - **醫療**：forbidden_phrase_rate 必須是 0（不能說「一定沒問題」）
> - **客服**：latency 最重要（使用者等不及）
> - **法規研究**：chunk_recall 最重要（漏掉條文比說錯更糟）
>
> 了解你的領域的 metric 優先順序，才能知道哪裡需要優先投資。

---

## 🎯 本章里程碑

```
golden.yaml 有 12 個 case。
eval baseline 表格有三個變體的 6 個數字。
至少能說出你的系統哪個 metric 最需要改善。
```

---

上一章 → [Ch 04：自我審查](ch04-self-correction.md)
下一章 → [Ch 06：解耦 channel + store](ch06-channel-store.md)
