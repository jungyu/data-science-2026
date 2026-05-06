# Ch 04：自我審查

> **本章對應**：[task-17](../ai-agent/tasks/task-17-judge-reflection.md)（Judge + Reflection Loop）
>
> **本章目標**：讓 bot 在送出回答之前，先用另一個 LLM 審查自己說的話。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ 4 軸 Judge 能給出結構化評分                          ║
║  ✅ 低分回答自動重試，直到夠好或達到上限                 ║
║  ✅ 三個 graph 變體並排執行，觀察 reflection 的效果      ║
╚══════════════════════════════════════════════════════════╝
```

---

## 4-1  問題：bot 不知道自己說得好不好

Ch03 解決了「知識庫沒有答案時不亂答」。
但如果知識庫有答案，bot 的回答是否真的：
1. 有根據 chunks 說話（不是亂加料）？
2. 引用的 chunk 確實說了這件事？
3. 格式清楚（不是一大坨字）？
4. 不確定的地方有明確說明？

目前版本：不知道。送出去就送出去了。

---

## 4-2  解法：在推送前加一個 Judge 節點

```
generate
    ↓
[judge]  ← 新節點，另一個 LLM 扮演審查員
    ↓
分數夠？           分數不夠？
  ↓                    ↓
push             [reflect]  ← 新節點，重新生成
                     ↓
                   judge   ← 重試（最多 HARD_MAX 次）
                     ↓
                  ...最終一定會 push（超過上限就送出）
```

---

## 4-3  四軸評分：Judge 看什麼

```python
class JudgeScore(BaseModel):
    groundedness:        float  # 0.0–1.0  每個論點是否有 chunk 支撐
    citation_fidelity:   float  # 0.0–1.0  引用的 chunk 確實說了這件事
    format_clarity:      float  # 0.0–1.0  回答格式是否清楚易讀
    uncertainty_honesty: float  # 0.0–1.0  不確定的部分是否誠實標出

    # overall = 加權平均（預設權重，可在 settings 調整）
    # groundedness × 0.40 + citation_fidelity × 0.30
    #   + format_clarity × 0.15 + uncertainty_honesty × 0.15
    # groundedness 佔最高比重，因為幻覺是最嚴重的失分
    overall:             float

    pass_threshold:      bool   # overall >= settings.judge_pass_threshold（預設 0.7）
    feedback:            str    # 給 reflect 節點的改進建議（「論點 2 缺少引用…」）
```

---

### 各軸的意義

**groundedness（接地性）**

```
回答說：「Next.js 14 的 hydration error 通常在 dev mode 才出現」
chunks 裡：沒有這句話  → groundedness 低

回答說：「根據文件，hydration error 出現在 Server/Client 邊界」
chunks 裡：chunk_001 說了這件事  → groundedness 高
```

**citation_fidelity（引用忠實度）**

```
回答引用了 chunk_003
chunk_003 的內容：「App Router 的路由基於 file system」
回答卻說「chunk_003 說 hydration 和路由有關」  → citation_fidelity 低
（chunk_003 根本沒提 hydration）
```

**format_clarity（格式清晰度）**

```
差：「Next.js14的hydration問題在ServerComponents渲染時如果...（500字一段）」
好：「**hydration 問題** 有幾個常見原因：\n1. ...\n2. ...\n3. ...」
```

**uncertainty_honesty（不確定誠實度）**

```
AnswerContract.uncertainty = "不確定 Vercel 的具體設定"
回答卻說：「Vercel 設定只需要一行 config 就能解決」  → 低分
回答說：「Vercel 設定的部分我不太確定，建議直接查官方文件」  → 高分
```

---

## 4-4  Judge Prompt 設計

```python
JUDGE_PROMPT = """
你是一個嚴格的品質審查員。評估以下 AI 回答的品質。

評分標準（各項 0.0–1.0）：
- groundedness：每個論點都有 chunk 支撐嗎？有就 1.0，多一項沒有就扣 0.2
- citation_fidelity：引用的 chunk 確實說了被引用的內容嗎？
- format_clarity：適合 LINE 對話的格式嗎（適當分行、重點清楚）？
- uncertainty_honesty：contract 的 uncertainty 在回答中有誠實說明嗎？

使用者問題：{user_input}
Answer Contract：{contract}
AI 回答：{narrative}
Chunks（可供核對）：{context}

輸出 JudgeScore JSON，包含各項分數、overall（加權平均）、
pass_threshold（overall >= {threshold}）、feedback（改進建議）。
"""
```

> 💡 **Judge 用哪個 LLM？**
>
> 可以用比 generator 便宜的 LLM 做 judge（例如 gpt-4.1-mini）。
> 因為 judge 只需要「比對 + 評分」，不需要「創作」。
> 用比 generator 更強的 LLM 做 judge 通常沒有必要。

---

## 4-5  Reflection 節點：給 feedback，重新生成

```python
REFLECT_PROMPT = """
你的上一個回答被審查員退件，原因如下：

{feedback}

原始回答：
{previous_narrative}

請根據審查意見，重新生成一個更好的回答。
記得：只使用 answer_points 裡的論點，不要加料。

論點：{answer_points}
不確定的部分：{uncertainty}
"""

async def reflect_node(state: RAGState, services: RuntimeServices) -> dict:
    feedback = state["judge_score"].feedback
    previous = state["responses"][-1]   # 上一次的回答
    
    new_narrative = await services.generator.reflect(
        previous_narrative=previous,
        feedback=feedback,
        contract=state["answer_contract"],
    )
    
    # 把新回答 append 到 responses，保留歷程
    return {"responses": state["responses"] + [new_narrative]}
```

---

## 4-6  HARD_MAX：防止無限迴圈

Judge + Reflect 可能永遠不滿意。加一個硬上限：

```python
HARD_MAX = 2  # 最多重試 2 次（加上第一次，最多生成 3 次）
# 為什麼是 2？
#   第 1 次 reflect：overall 通常提升 0.10–0.15（有明確 feedback 可改）
#   第 2 次 reflect：提升縮小到 0.03–0.05（邊際遞減）
#   第 3 次及以後：幾乎沒有提升，但 latency 再翻一倍
# → 2 是「改善有感 vs latency 可接受」的甜蜜點
# → 若 2 次後仍不過，問題通常出在 KB 或 prompt，多跑幾次解決不了
```

實際函式簽名（`app/graph/nodes.py`）：

```python
def make_route_after_judge(
    max_retries: int,
    *,
    hitl_enabled: bool = False,   # Ch07 的 HITL 觸發用這個 flag
) -> Callable[[RAGState], str]:
    """工廠函式：回傳一個可以被 add_conditional_edges 使用的 routing 函式。"""

    def route_after_judge(state: RAGState) -> str:
        score       = state["judge_score"]
        retry_count = state.get("reflection_retry", 0)
        effective_max = min(max(max_retries, 0), HARD_MAX)   # 安全夾緊

        if score.pass_threshold:
            return "push"

        if retry_count >= effective_max:
            # 超過上限：若啟用 HITL，轉人工審查；否則直接送出
            return "human_review" if hitl_enabled else "push"

        return "reflect"

    return route_after_judge

# 組裝 graph
route_fn = make_route_after_judge(max_retries=2, hitl_enabled=settings.hitl_enabled)
g.add_conditional_edges(
    "judge",
    route_fn,
    {"push": "push", "reflect": "reflect", "human_review": "human_review"},
)
g.add_edge("reflect", "judge")    # reflect 完再回 judge
```

---

## 4-7  三個 Graph 變體並排

現在你有三個版本的 graph：

```
GRAPH_VARIANT=basic      → route → retrieve → generate → push
GRAPH_VARIANT=selfrag    → ... + extract_features + expand_seeds + sufficiency + two-stage
GRAPH_VARIANT=reflection → selfrag + judge + reflect loop
```

切換方式（改 `.env` 或環境變數）：

```bash
GRAPH_VARIANT=basic      ./scripts/run_local.sh
GRAPH_VARIANT=selfrag    ./scripts/run_local.sh
GRAPH_VARIANT=reflection ./scripts/run_local.sh
```

---

### 三個變體的差異

```
╔══════════════════════════════════════════════════════════╗
║  變體對比速查                                            ║
║                                                          ║
║  basic:      快（~1 LLM call），無自我審查               ║
║  selfrag:    中（~3-5 LLM calls），有誠實追問            ║
║  reflection: 慢（~5-9 LLM calls），有品質保證            ║
╚══════════════════════════════════════════════════════════╝
```

---

## 4-8  Graph 建構：reflection 版

```python
def build_reflection_graph(services: RuntimeServices):
    g = StateGraph(RAGState)

    # 前段和 selfrag 相同
    g.add_node("route",             partial(route_node,            services=services))
    g.add_node("extract_features",  partial(extract_features_node, services=services))
    g.add_node("expand_seeds",      expand_seeds_node)
    g.add_node("retrieve_one_seed", partial(retrieve_seed_node,    services=services))
    g.add_node("fuse_scores",       fuse_scores_node)
    g.add_node("sufficiency_check", partial(sufficiency_node,      services=services))
    g.add_node("clarify",           partial(clarify_node,          services=services))
    g.add_node("generate",          partial(generate_node,         services=services))

    # reflection 新增節點
    g.add_node("judge",   partial(judge_node,   services=services))
    g.add_node("reflect", partial(reflect_node, services=services))
    g.add_node("push",    partial(push_node,    services=services))

    g.add_edge(START,               "route")
    g.add_edge("route",             "extract_features")
    g.add_edge("extract_features",  "expand_seeds")
    g.add_conditional_edges("expand_seeds", expand_seeds, ["retrieve_one_seed"])
    g.add_edge("retrieve_one_seed", "fuse_scores")
    g.add_edge("fuse_scores",       "sufficiency_check")
    g.add_conditional_edges(
        "sufficiency_check",
        route_after_sufficiency,
        {"generate": "generate", "clarify": "clarify"},
    )
    g.add_edge("generate", "judge")
    g.add_conditional_edges(
        "judge",
        route_after_judge,
        {"push": "push", "reflect": "reflect"},
    )
    g.add_edge("reflect", "judge")   # ← 形成迴圈
    g.add_edge("clarify", "push")
    g.add_edge("push",    END)

    return g.compile()
```

---

## 4-9  觀察 reflection 的效果

```bash
python scripts/demo_compare_variants.py \
  --query "Next.js 14 在 Vercel 部署時，hydration error 的根本原因是什麼？" \
  --variants basic selfrag reflection
```

預期輸出（簡化）：

```
=== basic ===
LLM calls: 2
Judge: N/A
Response: "hydration 是..." （可能加料）

=== selfrag ===
LLM calls: 4
Judge: N/A
Response: "根據三條 seed 的結果，..." （更精確）

=== reflection ===
LLM calls: 6
Judge attempt 1: overall=0.71 → reflect
Judge attempt 2: overall=0.88 → pass
Response: 改善後的版本
```

---

## ✏️ 本章任務

1. 完成 task-17（`judge_node` + `reflect_node` + `route_after_judge` 接進 graph）
2. 跑通三個變體：basic / selfrag / reflection
3. 用同一個問題測試三個變體，記錄 LLM calls 次數和回答品質差異
4. 調整 `JUDGE_PASS_THRESHOLD`（預設 0.75），觀察進入 reflect 的頻率變化
5. 在 `WEEK4.md` 記錄：你的領域需要幾軸評分？有沒有需要加入的 domain-specific 軸？

---

## 📝 沒有蠢問題

**Q：Judge 用 LLM 評分，這不是「讓 LLM 評估自己的輸出」嗎？會不會偏袒自己？**

A：是的，這是 LLM-as-Judge 的已知限制。
緩解方法：
1. 用不同 provider（例如 generator 用 OpenAI，judge 用 Claude）
2. 把 judge prompt 設計得非常具體（「groundedness 是 chunk 命中率，不是語感」）
3. Ch05 的 golden case eval 是人工驗證的真實標準

**Q：HARD_MAX=2 夠嗎？第三次如果還是很爛怎麼辦？**

A：取決於你願意付多少錢和等多久。
HARD_MAX=2 是甜蜜點：超過 2 次重試，邊際改善通常很小，但 latency 翻倍。
如果某類問題總是需要 3 次，考慮改善 sufficiency check 或 chunk 品質，
而不是增加重試次數。

**Q：四軸中哪一軸最重要？**

A：取決於領域。醫療/法規：groundedness 最重要（不能幻覺）。
一般問答：format_clarity 最重要（使用者讀不懂等於沒用）。
你可以在 `JudgeScore.overall` 的加權中調整各軸比重。
Ch05 的 metric 分析會幫你量化。

---

## 🧠 腦力激盪

> 你的領域是否需要第五軸？
>
> 例如：
> - **醫療**：`safety`（有沒有說出「一定沒問題，請放心服用」這類不負責任的話）
> - **法規**：`jurisdiction`（答案適用的法域是否正確）
> - **程式教學**：`runnability`（程式碼能不能執行）
>
> capstone 加分項目之一就是加入 domain-specific 評分軸。
> 見 `docs/ai-agent/examples/capstone-medical-distinction.md` 的 `MedicalJudgeScore`。

---

## 🎯 本章里程碑

```
三個變體都能跑。
用同一個問題，截下三份不同的回答。
reflection 版本的回答品質明顯比 basic 好（或相近但有審查過程）。
存在 WEEK4.md。
```

---

上一章 → [Ch 03：誠實追問 + 兩段式生成](ch03-sufficiency-generation.md)
下一章 → [Ch 05：量化 + 觀測](ch05-evaluation.md)
