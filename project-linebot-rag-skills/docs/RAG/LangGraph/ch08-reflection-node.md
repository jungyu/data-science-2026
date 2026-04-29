# 第 8 章：Reflection Node 深潛

> 整個 Agent 好不好，80% 決定在這一個 node。

## 為什麼這章特別重要？

Reflect node 是：

- 品質檢查器
- 路由決策器
- 幻覺煞車器
- 迴圈控制中樞

寫爛了，整個 Agent 變成「自信地胡說，然後系統還幫它放行」。

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
- `grounded`：答案是否被檢索內容支持
- `sufficient`：證據是否足夠
- `relevance_score`：是否對準問題
- `coverage_score`：是否漏核心面向
- `hallucination_risk`：是否過度推論

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
- Judge 與 Route 可以分開替換模型

**缺點**
- 多一次 LLM call

如果你重視治理，這種拆法值得。

## Hard Guard（一定要加）

不要完全信任 LLM 自己判：

```python
def reflect_answer(state):
    parsed = call_reflection_llm(state)

    # 硬性規則：不被支持就不能 finalize
    if not parsed["grounded"] and parsed["decision"] == "finalize":
        parsed["decision"] = "human_review"

    return {"reflection": parsed, "attempt_count": state["attempt_count"] + 1}
```

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
