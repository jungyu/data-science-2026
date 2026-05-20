# 第 8 章：Reflection Node 深潛

> 整個 Agent 好不好，80% 決定在這一個 node。

## 為什麼這章特別重要？

Reflect node 是：

- 品質檢查器
- 路由判斷資料的產生器
- 幻覺煞車器
- 迴圈控制中樞

寫爛了，整個 Agent 變成「自信地胡說，然後系統還幫它放行」。

先釐清責任邊界：Reflect node 可以產生 `decision`，但**不直接跳到下一個節點**。真正的跳轉仍然交給 ch03 的 routing function。這個分工很重要：LLM 負責評估與建議，Graph 負責執行流程規則。

## 大忌：把 reflection 寫成「請你自己改進」

```txt
請檢查以上答案好不好，若不好請改進。
```

這 prompt 把三件事混在一起：
1. 評估
2. 決策
3. 重寫

結果模型開始自由發揮，吐出一段散文，系統根本沒辦法 routing。

## 正確拆法

Reflect node 只做兩件事：

### 1. 評估
- grounded？
- sufficient？
- relevance？
- coverage？
- hallucination_risk？

### 2. 決策（封閉集合）
- `rewrite_query`
- `retrieve_again`
- `finalize`
- `human_review`

## 四大原則

### 原則 1：Reflect 不負責重寫答案

它只判斷，不改答案。否則責任會爆炸。

### 原則 2：輸出必須是結構化 JSON

不要自然語言段落。Routing 吃結構，不吃作文。

### 原則 3：decision 必須是封閉集合

```
✅ "rewrite_query"
❌ "我覺得可以再找看看"
❌ "try_again"
```

### 原則 4：評估維度要明確

最少包含：
- `grounded` *(bool)*：答案是否被檢索內容支持
- `sufficient` *(bool)*：證據是否足夠
- `relevance_score` *(0–1)*：是否對準問題
- `coverage_score` *(0–1)*：是否漏核心面向
- `hallucination_risk` *(0–1)*：是否過度推論

> **為什麼有的是 boolean、有的是 score？**
> Boolean 用於**硬路由判斷**——`grounded=false` 就絕對不能 finalize，決策乾脆。Score 用於**保留信心資訊**——同樣是「夠不夠」，0.82 和 0.51 訊號不同，hard guard 可以根據 threshold 升級到 human_review。
>
> **`grounded` 和 `hallucination_risk` 怎麼分？**
> 一體兩面：grounded 問「**有沒有出處**」，hallucination_risk 問「**有沒有無中生有 / 過度推論**」。
> 失敗模式不同：`grounded=true` 但 `hallucination_risk=0.7` 通常是「文件有寫但被誇大解讀」；`grounded=false` 則是完全沒出處。兩個一起記，路由規則才細膩。

## Decision 判官表

### `rewrite_query` — 方向錯了

問題理解錯、搜尋方向偏、retriever 一直找錯類型。

**例子**：使用者問「浮數脈代表什麼？」，系統 rewrite 成「脈搏快 心率偏高 原因」，方向太西醫化。

> ❗ 不是 `retrieve_again`，因為再查也只會在錯方向上越查越多。

### `retrieve_again` — 方向對但證據不足

查詢方向 OK，但找到的文件太少或局部。

**例子**：問「浮數脈如何對應外感風熱」，找到「浮脈」「數脈」但沒有完整的「風熱病機」。

### `finalize` — 可以了

答案有文件支持、沒明顯幻覺、對準問題、關鍵面向完整。

> ⚠️ **標準要保守**。生產系統最常見問題不是「答得太短」，是「自信地答錯」。

### `human_review` — 找人

高風險領域、文件矛盾、問題歧義太高、接近 max_attempts 但仍不穩。

> 高風險領域不要省這個。它不是浪費，是系統安全閥。

## 正式版 Prompt（System）

```txt
You are a strict reflection and routing node inside a LangGraph-based RAG workflow.

You are not an answer generator.
You are not a rewriting assistant.
You are not allowed to add outside knowledge.

Your task is to evaluate the current draft answer using only:
1. the user question
2. the rewritten query
3. the retrieved documents
4. the current draft answer

You must assess:
- groundedness
- sufficiency
- relevance
- coverage
- hallucination risk

You must return exactly one routing decision from:
- rewrite_query
- retrieve_again
- finalize
- human_review

Decision rules:
- choose rewrite_query when the retrieval direction is wrong or the query framing is poor
- choose retrieve_again when the retrieval direction is correct but evidence is insufficient
- choose finalize only when the answer is grounded, relevant, and sufficiently supported
- choose human_review when the case is ambiguous, high-risk, or should not be finalized automatically

Hard constraints:
- if the answer contains unsupported claims, grounded must be false
- if grounded is false, decision must not be finalize
- if major required aspects are missing, sufficient must be false
- if the query direction is wrong, prefer rewrite_query over retrieve_again
- if ambiguity remains in a high-risk case, prefer human_review

Return valid JSON only.
```

## 正式版 Prompt（User）

```txt
USER QUESTION:
{{ user_query }}

NORMALIZED QUERY:
{{ normalized_query }}

REWRITTEN QUERY:
{{ rewritten_query }}

RETRIEVED DOCUMENTS:
{{ retrieved_docs }}

CURRENT DRAFT ANSWER:
{{ draft_answer }}

ATTEMPT COUNT:
{{ attempt_count }}

MAX ATTEMPTS:
{{ max_attempts }}

Return JSON with this exact schema:
{
  "grounded": boolean,
  "sufficient": boolean,
  "relevance_score": number,
  "coverage_score": number,
  "hallucination_risk": number,
  "missing_topics": string[],
  "reasoning": string,
  "decision": "rewrite_query" | "retrieve_again" | "finalize" | "human_review"
}
```

> 💡 **為什麼 `attempt_count` / `max_attempts` 也丟給 LLM？**
> 讓 reflection 知道「這是第幾次嘗試了、還剩幾次」。接近 max_attempts 時，LLM 自然會更傾向 `finalize` 或 `human_review` 而不是無限 `retrieve_again`——避免生產環境陷入死迴圈、燒錢、超時。Hard guard 也會用這個欄位做最後一道防線。

## 輸出 Schema 範例

```json
{
  "grounded": true,
  "sufficient": false,
  "relevance_score": 0.82,
  "coverage_score": 0.56,
  "hallucination_risk": 0.22,
  "missing_topics": ["病機說明", "與浮數脈相關的辨證分歧"],
  "reasoning": "答案與問題相關且大部分有根據，但證據不足以涵蓋所需的辨證解釋。",
  "decision": "retrieve_again"
}
```

> 💡 **`missing_topics` 為什麼是關鍵欄位？**
> 它是 reflection → 下一輪 loop 的**橋樑**。當 `decision = retrieve_again` 或 `rewrite_query` 時，下一個節點可以直接拿 `missing_topics` 改寫查詢——「原問題 + 補『病機說明、辨證分歧』」就比盲目「再查一次」精準得多。
> **沒這個欄位的後果**：下一輪只會重複上一輪的查詢，浪費 token，永遠收斂不了。

## 進階：兩階段 Reflect

更穩的做法是把 Judge 和 Route 分開呼叫：

### Phase 1: Judge（只評估）
```json
{
  "grounded": false,
  "sufficient": false,
  "relevance_score": 0.61,
  "hallucination_risk": 0.68,
  ...
}
```

### Phase 2: Route（只決策）
```json
{ "decision": "retrieve_again" }
```

**優點**
- 比較穩
- 易於測試
- Judge 與 Route 可以分開替換模型（例如 Judge 用大模型、Route 用小模型）

**缺點**
- 多一次 LLM call

**骨架**：

```python
def reflect_node(state):
    judge = call_judge_llm(state)              # Phase 1：只評估，不決策
    route = call_route_llm(state, judge)       # Phase 2：基於 judge 結果決策
    return {
        "reflection": {**judge, **route},
        "attempt_count": state["attempt_count"] + 1,
    }
```

如果你重視治理（高風險領域、需要可審計），這種拆法值得。

## Hard Guard（一定要加）

不要完全信任 LLM 自己判——這呼應 [ch06](ch06-rag-vs-selfrag-vs-reflection.md) 的「**信規則不信 LLM 自評**」。Hard guard 是寫在 code 裡的規則引擎，攔截 LLM 想放行但不該放行的 case：

```python
def reflect_answer(state):
    parsed = call_reflection_llm(state)
    attempt = state["attempt_count"] + 1
    max_attempts = state["max_attempts"]

    # Guard 1：沒根據就不能 finalize
    if not parsed["grounded"] and parsed["decision"] == "finalize":
        parsed["decision"] = "human_review"

    # Guard 2：超過嘗試上限——強制收斂，不讓它無限重試燒錢
    if attempt >= max_attempts and parsed["decision"] in ("rewrite_query", "retrieve_again"):
        parsed["decision"] = "human_review"

    # Guard 3：高風險領域 + 幻覺風險偏高 → 直接送人
    if parsed["hallucination_risk"] > 0.6 and state.get("is_high_risk_domain"):
        parsed["decision"] = "human_review"

    # Guard 4：信心普遍偏低（LLM 卻硬要 finalize）→ 升級
    if (parsed["relevance_score"] < 0.6 or parsed["coverage_score"] < 0.5) \
            and parsed["decision"] == "finalize":
        parsed["decision"] = "human_review"

    return {"reflection": parsed, "attempt_count": attempt}
```

> 🛡️ **Hard guard 的設計哲學**：LLM 給的是「**評估與建議**」，最終放行決策由規則引擎做。每加一條 guard 就把一類「LLM 偏樂觀」的失敗模式擋下來。生產上線後，每次 incident 都應該轉成一條新的 guard。

## 接線到 LangGraph：從 decision 到條件邊

reflection 輸出有了，怎麼把它接到圖上？用 `add_conditional_edges`：

```python
def route_after_reflect(state):
    """純函式：讀 reflection.decision 決定下一個節點。
    這裡不打 LLM——決策成本在 reflect_node 一次付清。"""
    return state["reflection"]["decision"]

builder.add_conditional_edges(
    "reflect",                    # 從哪個節點分岔
    route_after_reflect,          # 怎麼決定方向
    {
        "rewrite_query":   "rewrite_query",   # decision → 對應的 node id
        "retrieve_again":  "retrieve",
        "human_review":    "human_review",
        "finalize":        "finalize",
    },
)
```

幾個關鍵：

- **路由函式不打 LLM**——它只是讀 state 裡算好的 decision。LLM 成本只付一次
- **dict 的 key 必須涵蓋所有 decision 值**——這就是為什麼原則 3 要封閉集合：缺一個 key，圖在生產環境跑到一半就 KeyError
- **key = decision 字串**，**value = 圖上的 node id**（兩者不一定同名，例如 `retrieve_again` → `retrieve`）

> 🔗 完整圖怎麼編譯、START / END 怎麼接、`human_review` 節點怎麼掛 `interrupt_before`——在 [ch09 實戰程式碼](ch09-langgraph-in-action.md)。

## 高風險領域版本

中醫 / 法規 / 命理建議在 system prompt 加：

```txt
You are a strict reflection gate for a high-risk domain assistant.

In high-risk cases:
- be conservative
- do not allow unsupported inference
- do not finalize weak answers
- prefer human_review when ambiguity remains

If the draft includes advice, interpretation, classification, diagnosis, or recommendation that is not directly supported by the retrieved evidence, mark grounded = false.
```

## 五大常見錯誤

1. **讓 Reflect 順便改答案** → 責任爆炸
2. **沒有封閉 decision set** → routing 崩
3. **沒有 hard guard** → 模型常在證據不足時硬 finalize
4. **只問「好不好」** → 標準飄
5. **retrieved_docs 丟太亂** → reflect 也判錯，要先 format 整齊

## 🔧 真實實作對照：[`app/judge/scorer.py`](../../../app/judge/scorer.py) + [`app/graph/nodes.py`](../../../app/graph/nodes.py)

本書範例專案的 reflection node 比教學版更精緻，值得對照看「production grade」長什麼樣。

### 1. Schema 用 Pydantic + 內建 `passes()` 規則

```python
# app/judge/scorer.py:29-52
class JudgeScore(BaseModel):
    groundedness: int = Field(..., ge=0, le=10)
    citation_fidelity: int = Field(..., ge=0, le=10)
    format_completeness: int = Field(..., ge=0, le=10)
    uncertainty_honesty: int = Field(..., ge=0, le=10)
    issues: list[str] = Field(default_factory=list)

    @property
    def mean(self) -> float:
        return (self.groundedness + self.citation_fidelity
                + self.format_completeness + self.uncertainty_honesty) / 4

    def passes(self, *, min_axis: int = 6, min_mean: float = 7.0) -> bool:
        worst = min(self.groundedness, self.citation_fidelity,
                    self.format_completeness, self.uncertainty_honesty)
        return worst >= min_axis and self.mean >= min_mean
```

對照本章三件事：
- **4 軸結構化評分**（呼應原則 4）：但維度跟教學版不同——不是 `grounded/sufficient/relevance/coverage/hallucination`，而是 **`groundedness` / `citation_fidelity` / `format_completeness` / `uncertainty_honesty`**。這四軸針對的是「**生成的 narrative 是否誠實對待 retrieval 結果**」，比教學版偏向「**retrieval 是否夠用**」（後者另外用 [`SufficiencyChecker`](../../../app/graph/sufficiency.py) 處理）。
- **`Field(..., ge=0, le=10)`**：LLM 偶爾會回 `groundedness: 15`，Pydantic 直接 raise validation error，比手寫 if-check 乾淨
- **`passes()` 把硬閾值規則寫進 schema 旁**：`worst >= min_axis AND mean >= min_mean` 是雙重門檻（防「3 軸滿分掩護 1 軸超爛」），對應本章 Hard Guard Guard 4「信心普遍偏低就不能放行」

### 2. Judge node 帶 graceful degrade + skill skip list

```python
# app/graph/nodes.py:300-341（節錄）
SKIP_JUDGE_SKILLS: set[str] = {"general_chat", "emotional_calibration"}

async def judge_node(state: RAGState, services: Any) -> dict[str, Any]:
    settings = services.settings
    if not getattr(settings, "judge_enabled", True):
        return {"judge_score": None, "judge_feedback": []}

    skill = state.get("skill")
    if skill is not None and skill.skill_id in SKIP_JUDGE_SKILLS:
        return {"judge_score": None, "judge_feedback": []}    # ① 特定 skill 跳過 judge

    router_result = state["router_result"]
    if not router_result.is_rag_required:
        return {"judge_score": None, "judge_feedback": []}    # ② 不需 RAG 的回覆免 judge

    score = await services.judge.judge(...)
    if score is None:                                          # ③ LLM 失敗 → degrade 為 pass
        return {"judge_score": None, "judge_feedback": []}

    passed = score.passes(min_axis=settings.judge_min_axis, min_mean=settings.judge_min_mean)
    feedback = [] if passed else list(score.issues)
    return {"judge_score": score, "judge_feedback": feedback}
```

三個本章沒涵蓋的 production 設計：

- **① Skill skip list**：`general_chat`、`emotional_calibration` 這類沒檢索結果可審的 skill 直接跳過。**判官只審該審的東西**，避免在沒上下文的對話上強做評估
- **② RAG 不需要時跳過**：route 階段已經判定不需 RAG → 無 chunks 可比對 grounding，跳過。**前置條件不滿足時誠實 no-op**
- **③ LLM 失敗 → fail-open（degrade as pass）**：跟教學版 fail-closed（→ human_review）相反！為什麼？因為這個 LINE bot 是即時對話，judge 失敗就阻塞會讓使用者等到天荒地老。**選 fail-open 還是 fail-closed 看領域**——對話 bot 求即時、醫療法規求安全

### 3. 「Hard guard 規則 + LLM 評估」分工

教學版 Hard Guard 是事後在 Python code 改寫 `decision`；真實版把這拆得更乾淨：

| 角色 | 在哪 | 做什麼 |
|------|------|--------|
| **LLM 評估** | `GroundednessJudge.judge()` | 給 4 個分數 + issues list |
| **硬閾值規則** | `JudgeScore.passes()` | 純函式，可單測，不打 LLM |
| **流程治理** | `make_route_after_judge()` ([ch03 對照](ch03-conditional-edges.md#-真實實作對照三種複雜度的路由函式)) | retry 上限、HITL 分流 |

**三層全部是純函式 / 純規則，只有「打分」一步用 LLM**——這就是本章「Reflect 不負責改答案」的極致實踐。

> 🎯 **教學版 vs 真實版的取捨**：教學版把 hard guard 寫在同一個函式內好教學；真實版把「打分 / 閾值 / 路由」三件事拆三層，是為了「**每一層都可獨立單測 + 獨立替換 LLM model**」。學成後升級到真實版分層即可。

## 文件格式化建議

別把 docs 塞成一坨 JSON。整理成：

```txt
[Doc 1]
source: tcm-knowledge-base
score: 0.88
content: 浮脈主表，數脈主熱...

[Doc 2]
source: clinical-cases
score: 0.81
content: 外感風熱證的脈象特徵...
```

> 💡 **Brain Power**
> 為什麼要把 score 也放進 prompt？模型能用這個資訊嗎？

<details>
<summary>解答</summary>

能。模型看到 score 偏低時會更謹慎，不容易把弱證據當強證據。這在 hallucination_risk 評估上很關鍵。
</details>

## 一句話收斂

> Reflect node 不是要讓模型更會說，而是要讓系統知道「現在不該亂說」。

---

**下一章**：[實戰：完整 LangGraph 程式碼](ch09-langgraph-in-action.md)
