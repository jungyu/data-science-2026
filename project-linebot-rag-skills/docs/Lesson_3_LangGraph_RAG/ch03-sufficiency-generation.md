# Ch 03：誠實追問 + 兩段式生成

> **本章對應**：[task-15](../ai-agent/tasks/task-15-sufficiency-clarify.md)（Sufficiency Check）+
> [task-16](../ai-agent/tasks/task-16-two-stage-generator.md)（Two-stage Generator）
>
> **本章目標**：讓 bot 知道「什麼時候不知道」，並讓回答可以被自動驗證。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ 知識庫沒有答案時，bot 誠實說「我不確定」             ║
║  ✅ 能解釋 Sufficiency Check 的三條規則                  ║
║  ✅ 回答拆成 contract + narrative 兩層，測試容易寫       ║
╚══════════════════════════════════════════════════════════╝
```

---

## 3-1  問題：bot 目前會「假裝知道」

把這個問題丟給你的 bot（用一個知識庫裡沒有的主題）：

```
「請問 Kubernetes HPA 的 cooldown period 預設是多少秒？」
```

如果你的知識庫裡沒有 Kubernetes 的文件，你可能看到：

```
Kubernetes HPA 的 cooldown period 預設是 300 秒，
你可以在 kube-controller-manager 的 --horizontal-pod-autoscaler-downscale-stabilization
參數裡調整…
```

這個回答聽起來很有信心。但它是**幻覺**——bot 用 LLM 的訓練記憶亂答，
不是從你的知識庫回答的。

**為什麼危險？**

```
使用者相信了這個回答
      ↓
設定了錯誤的參數
      ↓
生產環境 scale-down 出問題
      ↓
你的 bot 被當成不可信任的工具
```

---

## 3-2  解法：在生成前加一道「夠不夠」的檢查

```
fuse_scores
    ↓
[sufficiency_check]  ← 新節點
    ↓
夠？             不夠？
  ↓                 ↓
generate         clarify   ← 新節點（回覆「我不確定，你可以問更具體的問題嗎？」）
```

**Sufficiency Check 做什麼？**

它看三件事：

```
規則 1：min_chunks      撈到的 chunk 數量是否夠多？
規則 2：min_top_score   最高分的 chunk 相似度夠不夠高？
規則 3：min_feature_overlap  chunks 裡有沒有出現使用者問的關鍵詞？
```

三條全過 → **sufficient**，繼續生成
任一條不過 → **insufficient**，觸發 clarify

---

## 3-3  Sufficiency Check 的三條規則

### 規則 1：min_chunks

```python
# 至少要撈到 N 個 chunk
if len(chunks) < settings.sufficiency_min_chunks:   # 預設 2
    return SufficiencyResult(sufficient=False, reason="too_few_chunks")
```

**直覺解釋**：
- 0 個 chunk → 知識庫根本沒有相關內容
- 1 個 chunk → 可能只是部分命中，不夠可靠

---

### 規則 2：min_top_score

```python
# 最高分要超過門檻
top_score = max(c.score for c in chunks)
if top_score < settings.sufficiency_min_top_score:  # 預設 0.65
    return SufficiencyResult(sufficient=False, reason="low_top_score")
```

**直覺解釋**：
```
score 0.90+  → 幾乎完全命中，非常可信
score 0.70+  → 合理命中，可以生成
score 0.65-  → 相似度太低，可能是不同主題的 chunk 湊進來的
```

---

### 規則 3：min_feature_overlap

```python
# features 是從 Feature Extractor 抽出的關鍵詞
# context 是所有 chunks 合起來的文字
feature_hits = sum(
    1 for f in features.entities
    if f.lower() in context.lower()
)
overlap_rate = feature_hits / max(len(features.entities), 1)

if overlap_rate < settings.sufficiency_min_feature_overlap:  # 預設 0.3
    return SufficiencyResult(sufficient=False, reason="low_feature_overlap")
```

**直覺解釋**：

```
使用者問：「Next.js 14 hydration error」
entities:  ["Next.js", "hydration", "error"]

chunks 裡出現了：["Next.js", "hydration"] → 2/3 = 0.67 ✅
chunks 裡只出現了：["hydration"] → 1/3 = 0.33 ≈ 剛剛過門檻
chunks 裡都沒有 → 0.0 ❌
```

> 💡 **跨語言查詢的坑（Ch01 曾提到）**
>
> 你問中文，知識庫是英文 → `feature_overlap` 一定是 0（字面沒有交集）
>
> 解法：把 `SUFFICIENCY_MIN_FEATURE_OVERLAP=0` 或讓 Feature Extractor
> 把中文翻成英文 entity。Ch05 eval 時再用數據確認哪種更好。

---

## 3-4  LangGraph 的條件邊

到目前為止，graph 裡只有**普通邊**（A → B，永遠往同一個方向）。

這章第一次加入**條件邊**（根據 state 裡的值，走不同路徑）：

```python
def route_after_sufficiency(state: RAGState) -> str:
    if state["sufficiency_result"].sufficient:
        return "generate"
    else:
        return "clarify"

# graph 建構時
g.add_conditional_edges(
    "sufficiency_check",          # 從這個節點離開
    route_after_sufficiency,      # 呼叫這個函式，回傳字串
    {
        "generate": "generate",   # 回傳 "generate" → 走 generate 節點
        "clarify":  "clarify",    # 回傳 "clarify"  → 走 clarify 節點
    }
)
```

Mermaid 圖：

```
fuse_scores → sufficiency_check
                    ↓ sufficient
                  generate → push → end
                    ↓ insufficient
                  clarify  → push → end
```

---

## 3-5  Clarify 節點：誠實說不知道

```python
async def clarify_node(state: RAGState, services: RuntimeServices) -> dict:
    reason = state["sufficiency_result"].reason
    
    templates = {
        "too_few_chunks":       "我在知識庫裡找不到足夠的相關資料來回答這個問題。",
        "low_top_score":        "我找到了一些資料，但相關度不夠高，不確定是否正確。",
        "low_feature_overlap":  "你的問題涵蓋了一些我的知識庫可能沒有的主題。",
    }
    
    base_msg = templates.get(reason, "我目前無法確定這個問題的答案。")
    suggestion = "你可以試試更具體的問題，或告訴我你想了解哪個面向？"
    
    return {"responses": [f"{base_msg}\n\n{suggestion}"]}
```

> 💡 **誠實有時比「答錯」更有價值**
>
> 一個說「我不知道」的 bot，比一個自信地答錯的 bot 更值得信任。
> 這也是你的 bot 和「通用 ChatGPT」的差異：
> 通用 LLM 用訓練記憶回答，你的 bot 只用你的知識庫。

---

## 3-6  兩段式生成：為什麼把回答拆成兩層？

Ch04 會加入「自我審查」——judge 要驗證 bot 的回答是不是根據 chunks 說的。

**問題是**：judge 怎麼驗證？

如果回答是自由形式的文字：
```
「Next.js 14 在 Vercel 上部署時，hydration 問題通常出現在 Server Components 
和 Client Components 的邊界。根據官方文件，你需要確認...」
```

judge 必須把整段話和 chunks 比對——這很難自動化，也很難寫測試。

---

**解法：先出一份「骨架」（Answer Contract），再填肉（Narrative）**

```
[Generator — Stage 1: Contract]
輸入：user_input + chunks
輸出（JSON）：
{
  "answer_points": ["點 1", "點 2", "點 3"],
  "citations":     ["chunk_id_001", "chunk_id_003"],
  "confidence":    0.85,
  "uncertainty":   null
}

[Generator — Stage 2: Narrative]
輸入：answer_points + citations + uncertainty
輸出（自然語言）：
「根據我查到的資料，有幾個重點要注意...」
```

---

### 為什麼這樣做更好？

| 面向 | 一段式 | 兩段式 |
|------|--------|--------|
| **可測試性** | 很難斷言「回答有無根據 chunks」 | `citations` 是 JSON，可直接驗證 chunk ID 存在 |
| **可稽核性** | 只能讀文字判斷 | `confidence` + `uncertainty` 是結構化欄位 |
| **Judge 友善** | Judge 要做全文比對 | Judge 只需驗證 `answer_points` 與 citations 對應 |
| **可解釋性** | 難以說明「為什麼這樣回答」 | Contract 的 `citations` 直接指向來源 |

---

## 3-7  Stage 1：Answer Contract

> 實際實作：[`app/generator/contract.py`](../../app/generator/contract.py)（`AnswerContract` 類別）、
> [`app/graph/nodes.py`](../../app/graph/nodes.py)（`build_answer_contract_node`）

```python
# app/generator/contract.py（簡化版）
from pydantic import BaseModel

class AnswerContract(BaseModel):
    answer_points: list[str]   # 每個論點是一個 chunk 能支撐的短語
    citations:     list[str]   # chunk ID 清單（對應 KnowledgeChunk.id）
    confidence:    float       # 0.0–1.0，LLM 自我評估
    uncertainty:   str | None  # 「我不確定 X 的部分」，None 表示完全確定

CONTRACT_PROMPT = """
你是一個嚴謹的知識摘要員。
根據以下 chunks，列出可以回答使用者問題的論點。

規則：
- 每個 answer_point 必須有對應的 chunk 支撐
- 不要加入 chunks 沒有的資訊
- 如果有不確定的部分，填入 uncertainty
- confidence 是你對整體回答可靠度的自我評估

使用者問題：{user_input}

Chunks：
{context}

以 JSON 格式輸出 AnswerContract。
"""
```

---

## 3-8  Stage 2：Narrative Generator

> 實際實作：[`app/generator/narrative.py`](../../app/generator/narrative.py)（`generate_narrative`）、
> [`app/graph/nodes.py`](../../app/graph/nodes.py)（`render_narrative_node`）

```python
# app/generator/narrative.py（簡化版）

NARRATIVE_PROMPT = """
你是一個友善的 AI 助理。
根據以下已驗證的論點，生成自然語言回覆。

規則（嚴格遵守）：
1. 只使用 answer_points 裡的論點——不要加料
2. 如果有 uncertainty，在回覆中明確提及
3. 語氣友善、清楚，適合對話（LINE / HTTP 均可）

論點：
{answer_points}

不確定的部分：{uncertainty}

輸出：自然語言回覆（不需要 JSON）
"""

async def generate_narrative(contract: AnswerContract, ...) -> str:
    points_str = "\n".join(f"- {p}" for p in contract.answer_points)
    prompt = NARRATIVE_PROMPT.format(
        answer_points=points_str,
        uncertainty=contract.uncertainty or "無",
    )
    return await llm.generate(prompt)
```

---

> 💡 **Grounded Constraint 的核心原則**
>
> Stage 2 的 prompt 說「只使用 answer_points 裡的論點」——
> 這叫做 **grounded constraint**（接地約束）。
>
> LLM 的預訓練記憶很豐富，很容易「自行補充」。
> 明確告訴它「只用這份材料」，並在 Stage 1 把材料結構化，
> 是防止幻覺最有效的方法之一。

---

## 3-9  更新後的 Graph

```python
# app/graph/rag_graph.py — selfrag 版本（加入 sufficiency + two-stage）

def build_selfrag_graph(services: RuntimeServices):
    g = StateGraph(RAGState)

    g.add_node("route",              partial(route_node,              services=services))
    g.add_node("extract_features",   partial(extract_features_node,   services=services))
    g.add_node("expand_seeds",       expand_seeds_node)
    g.add_node("retrieve_one_seed",  partial(retrieve_seed_node,      services=services))
    g.add_node("fuse_scores",        fuse_scores_node)
    g.add_node("sufficiency_check",  partial(sufficiency_node,        services=services))
    g.add_node("clarify",            partial(clarify_node,            services=services))
    g.add_node("generate",           partial(generate_node,           services=services))
    g.add_node("push",               partial(push_node,               services=services))

    g.add_edge(START,                "route")
    g.add_edge("route",              "extract_features")
    g.add_edge("extract_features",   "expand_seeds")
    g.add_conditional_edges("expand_seeds", expand_seeds, ["retrieve_one_seed"])
    g.add_edge("retrieve_one_seed",  "fuse_scores")
    g.add_edge("fuse_scores",        "sufficiency_check")
    g.add_conditional_edges(
        "sufficiency_check",
        route_after_sufficiency,
        {"generate": "generate", "clarify": "clarify"},
    )
    g.add_edge("generate", "push")
    g.add_edge("clarify",  "push")
    g.add_edge("push",     END)

    return g.compile()
```

---

## ✏️ 本章任務

1. 完成 task-15（`sufficiency_node` + `clarify_node` 接進 graph）
2. 完成 task-16（`AnswerContract` + `generate_narrative` + `generate_node` 改兩段式）
3. 測試「知識庫沒有的問題」→ 確認進入 clarify 分支
4. 測試「知識庫有的問題」→ 確認 `responses` 裡有 contract 的論點
5. 在 `WEEK3.md` 記錄：哪些門檻值對你的領域最適合（調整 `min_top_score`、`min_feature_overlap`）

---

## 📝 沒有蠢問題

**Q：三條規則要全過才算 sufficient，這樣門檻會不會太高？**

A：預設值已經是偏寬鬆的（`min_chunks=2`、`min_top_score=0.65`、`min_feature_overlap=0.3`）。
如果你的知識庫很小（<50 chunks），可能 `min_chunks=1` 更適合。
Ch05 的 eval 會幫你找到最佳值。

**Q：clarify 的回覆會不會讓使用者覺得 bot 沒用？**

A：這取決於領域。醫療/法規 bot：誠實說不確定 = 非常重要。
一般問答 bot：可以加一句「你可以試試問 ChatGPT，它的訓練資料更廣」。
用 `clarify_node` 的 reason 來客製不同的誠實訊息。

**Q：`AnswerContract` 的 `confidence` 是 LLM 自我評估，這可信嗎？**

A：LLM 的 confidence 有 calibration 問題（常常過度自信或過度謙虛）。
不要直接用它做邏輯判斷——Ch04 的 judge 會做更可靠的驗證。
`confidence` 主要是讓人工審查時有個參考。

---

## 🧠 腦力激盪

> 你的領域哪些問題最容易觸發錯誤的 sufficient 判斷？
>
> 提示：
> - **False sufficient**：知識庫有相關文件，但回答的是錯誤面向
>   （例如：問「A 藥怎麼吃」，但 chunk 只有「A 藥的副作用」）
> - **False insufficient**：知識庫有答案，但 feature overlap 低
>   （例如：使用者用口語，knowledge base 用專業術語）
>
> 這些 edge case 會在 Ch05 用 golden case 量化。

---

## 🎯 本章里程碑

```
問一個你知識庫沒有的問題 → bot 回「我不確定」。
問一個你知識庫有的問題  → bot 回答裡看得出來有引用 chunk 的論點。
兩張截圖存在 WEEK3.md。
```

---

上一章 → [Ch 02b：進階檢索三技 — HyDE / 混合檢索 / Reranker](ch02b-advanced-retrieval.md)
下一章 → [Ch 04：自我審查](ch04-self-correction.md)
