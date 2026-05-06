# Ch 02：Multi-seed 檢索

> **本章對應**：[task-13](../ai-agent/tasks/task-13-feature-extractor.md)（Feature Extractor）+
> [task-14](../ai-agent/tasks/task-14-multi-seed-retrieval.md)（Multi-seed + RRF Fusion）
>
> **本章目標**：讓 bot 能正確處理「包含多個條件」的複合問題。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ 複合條件問題比 basic variant 多命中 ≥ 30% 的 chunk   ║
║  ✅ 能切換三種 fusion 策略並觀察差異                     ║
║  ✅ 能解釋 RRF 為什麼比單一 embedding 更適合複合查詢     ║
╚══════════════════════════════════════════════════════════╝
```

---

## 2-1  問題：單一 embedding 會稀釋語意

試著問你的 bot（用 basic variant）：

```
「Next.js 14 搭配 Server Components，在 Vercel 部署時，
  hydration 問題怎麼處理？」
```

你可能發現它只回答了 hydration，沒有提到 Vercel 部署的細節。

**為什麼？**

你的查詢被壓縮成一個 512 維的向量。這個向量試圖「同時表達」：
- Next.js 14 的版本特性
- Server Components 的渲染機制
- Vercel 部署的環境設定
- hydration error 的排查方式

四個方向加在一起，每個方向都被稀釋了。
向量距離計算時，沒有一個方向夠突出，檢索到的是「四不像」的 chunk。

---

## 2-2  解法：Feature Extractor + 多路展開

```
使用者輸入
   ↓
[Feature Extractor]  ← 把問題結構化抽取
   ↓
primary_topic: "Next.js 14 hydration"
qualifiers: ["Server Components", "Vercel 部署"]
entities: ["Next.js", "hydration", "SSR"]
   ↓
[expand_seeds]       ← 展開為多條查詢種子
   ↓
seed_1: "Next.js 14 hydration error"
seed_2: "Server Components rendering"
seed_3: "Vercel SSR deployment"
   ↓
並行向量搜尋（三條 seed 同時跑）
   ↓
hits_1: [A, B, C]
hits_2: [B, D, E]
hits_3: [A, F, G]
   ↓
[fuse_scores]        ← 合併三份結果
   ↓
final: [A★★, B★★, D, F, C, E, G]  （A、B 在多條 seed 都命中，排前面）
```

A 和 B 在多條 seed 裡都出現 → 代表它們跨越多個條件，最相關。

---

## 2-3  Feature Extractor：把問題結構化

### LLM-based 版本（預設）

```python
# app/graph/feature_extractor.py（簡化版）
class LLMFeatureExtractor:
    async def extract(self, user_input: str, ...) -> ExtractedFeatures:
        # 一次 LLM 呼叫，結構化輸出
        prompt = """
        從使用者的問題中抽取：
        - primary_topic: 核心主題（一個短語）
        - qualifiers: 限定條件（清單）
        - intent: "debug" | "explain" | "howto" | "compare" | "other"
        - entities: 具體的技術名詞 / 版本號
        - raw_query: 原始問題
        
        問題：{user_input}
        """
        return ExtractedFeatures(...)
```

**輸出範例**：

```python
ExtractedFeatures(
    primary_topic="Next.js 14 hydration error",
    qualifiers=["Server Components", "Vercel 部署"],
    intent="debug",
    entities=["Next.js", "Server Components", "hydration", "Vercel"],
    raw_query="Next.js 14 搭配 Server Components，在 Vercel 部署時，hydration 問題怎麼處理？",
)
```

### Rule-based 版本（高效能領域）

對於「詞彙表封閉」的領域（醫療症狀、法條號碼、程式語言名稱），
可以用 rule-based 替代 LLM（快 10 倍、零額外成本）：

```python
SYMPTOMS = {"咳嗽", "發燒", "頭痛", "腹瀉", ...}
DRUG_NAMES = {"普拿疼", "布洛芬", "Aspirin", ...}

class MedicalFeatureExtractor:
    async def extract(self, user_input: str, ...) -> MedicalFeatures:
        symptoms = [s for s in SYMPTOMS if s in user_input]
        drugs = [d for d in DRUG_NAMES if d.lower() in user_input.lower()]
        return MedicalFeatures(
            primary_topic=symptoms[0] if symptoms else user_input[:50],
            entities=symptoms + drugs,
            symptoms=symptoms,
            drug_names=drugs,
        )
```

完整範例見 [feature-extractor-medical.md](../ai-agent/examples/feature-extractor-medical.md)。

---

> 💡 **Hybrid 策略：兩全其美**
>
> 先跑 rule-based，如果沒有命中任何詞彙，fallback 到 LLM：
>
> ```python
> class HybridExtractor:
>     async def extract(self, user_input, **kwargs):
>         result = await self._rule.extract(user_input, **kwargs)
>         if not result.entities:       # rule 沒抓到東西
>             return await self._llm.extract(user_input, **kwargs)
>         return result
> ```
>
> 這是醫療、法規等領域的最佳實踐：
> 詞彙表內的輸入走快速 rule，詞彙表外的輸入走完整 LLM。

---

## 2-4  Multi-seed Fan-out / Fan-in

### LangGraph 怎麼做並行

傳統寫法（循序）：

```python
results = []
for seed in seeds:
    chunks = await retriever.retrieve(seed)
    results.append(chunks)
```

LangGraph 的並行寫法：

```python
# state 裡宣告「可累積」的欄位（對照 app/graph/state.py）
from operator import add
from typing import Annotated

class RAGState(TypedDict, total=False):
    # 普通欄位：後寫覆蓋前寫（last-write-wins）
    user_input:    str
    router_result: RouterResult

    # fan-out 欄位：每個並行節點寫入，LangGraph 用 add 合併
    hits_per_seed: Annotated[list[list[KnowledgeChunk]], add]
    #                        ↑                           ↑
    #                      型別               reducer = operator.add
    #                                         (即 list1 + list2 + list3 …)

    # Send API 需要的 per-seed 欄位
    seed:       str   # 當前 seed 查詢字串
    seed_index: int   # 對應第幾條 seed（用於 debug）
```

> **為什麼普通欄位不行？**
>
> 假設三個 `retrieve_one_seed` 並行跑，都想寫 `state["hits"]`。
> LangGraph 預設 **後寫覆蓋前寫**——三個節點最後只剩最後一個寫的結果。
>
> 加上 `Annotated[..., add]` 之後，LangGraph 看到「這個欄位有 reducer」，
> 就把每個節點的輸出 **append 進去**（`list1 + list2 + list3`），
> 所有 seed 的結果都保留。
>
> ```
> 沒有 reducer：node_A 寫 [chunk1, chunk2]，node_B 寫 [chunk3]
>   → state["hits"] = [chunk3]   ← node_A 的結果消失了
>
> 有 add reducer：
>   → state["hits"] = [chunk1, chunk2, chunk3]   ← 全部保留
> ```

```python
# 用 Send API 動態產生並行節點（對照 app/graph/variants/selfrag.py）
def expand_seeds(state: RAGState) -> list[Send]:
    return [
        Send("retrieve_one_seed", {"seed": s, "seed_index": i})
        for i, s in enumerate(state["expanded_seeds"])
    ]

# graph 建構：expand 節點執行後，Send 產生多個 retrieve_one_seed 實例
g.add_conditional_edges("expand", expand_seeds, ["retrieve_one_seed"])
```

LangGraph 自動並行執行所有 `retrieve_one_seed` 節點，
等全部完成後 fan-in——把各節點的 `hits_per_seed` 用 `add` 合併，
再進 fusion 節點做排名。

---

## 2-5  Score Fusion：三種策略

### Max Fusion

```
seed_1 hits: [A(0.92), B(0.85), C(0.71)]
seed_2 hits: [B(0.88), D(0.79), E(0.62)]
seed_3 hits: [A(0.90), F(0.77), G(0.65)]

max score per chunk:
  A: max(0.92, 0.90) = 0.92  ← 排第 1
  B: max(0.85, 0.88) = 0.88  ← 排第 2
  D: 0.79                    ← 排第 3
```

適合：任一條 seed 命中即可（廣撒網）

---

### Mean Fusion

```
mean score per chunk:
  A: (0.92 + 0.90) / 2 = 0.91  ← 排第 1
  B: (0.85 + 0.88) / 2 = 0.865 ← 排第 2
  D: 0.79 / 1 = 0.79            ← 排第 3
```

適合：偏好多路共識（多條 seed 都覺得好的 chunk）

---

### RRF（Reciprocal Rank Fusion）

```python
# RRF 看排名，不看分數
# k=60 是 RRF 原始論文（Cormack et al. 2009）的推薦值：
# - k 太小（如 10）→ 第 1 名分數遠高於第 2 名，排名 1 的 chunk 「壟斷」結果
# - k 太大（如 1000）→ 分數差異極小，排名 1 和排名 5 幾乎一樣
# - k=60 在大多數資訊檢索任務中是穩定的「平滑點」
def rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (rank + k)

seed_1 ranks: A=1, B=2, C=3
seed_2 ranks: B=1, D=2, E=3
seed_3 ranks: A=1, F=2, G=3

rrf scores:
  A: 1/(1+60) + 1/(1+60) = 0.0328   ← 排第 1（兩條 seed 都排名第 1）
  B: 1/(2+60) + 1/(1+60) = 0.0322   ← 排第 2
  D: 1/(2+60) = 0.0161               ← 排第 3
```

適合：大多數場景，因為鈍化了「極端高分」的影響，結果最穩定。

---

```
╔══════════════════════════════════════════════════╗
║  三種 Fusion 策略速查                            ║
║                                                  ║
║  Max  → 任一 seed 命中就好，廣度優先             ║
║  Mean → 多數 seed 都認可，共識優先               ║
║  RRF  → 排名比分數重要，最穩定（推薦預設）       ║
╚══════════════════════════════════════════════════╝
```

切換方式（不需改程式碼）：

```bash
FUSION_STRATEGY=rrf   ./scripts/run_local.sh   # 預設
FUSION_STRATEGY=max   ./scripts/run_local.sh
FUSION_STRATEGY=mean  ./scripts/run_local.sh
```

---

## 2-6  Graph 加入 Feature Extractor 和 Multi-seed

修改 `app/graph/rag_graph.py`，在 `route` 和 `retrieve` 之間插入新節點：

```python
def build_selfrag_graph(services: RuntimeServices):
    g = StateGraph(RAGState)

    g.add_node("route",            partial(route_node, services=services))
    g.add_node("extract_features", partial(extract_features_node, services=services))
    g.add_node("expand_seeds",     expand_seeds_node)
    g.add_node("retrieve_one_seed", partial(retrieve_seed_node, services=services))
    g.add_node("fuse_scores",      fuse_scores_node)
    g.add_node("generate",         partial(generate_node, services=services))
    g.add_node("push",             partial(push_node, services=services))

    g.add_edge(START,               "route")
    g.add_edge("route",             "extract_features")
    g.add_edge("extract_features",  "expand_seeds")
    g.add_conditional_edges("expand_seeds", expand_seeds, ["retrieve_one_seed"])
    g.add_edge("retrieve_one_seed", "fuse_scores")
    g.add_edge("fuse_scores",       "generate")
    g.add_edge("generate",          "push")
    g.add_edge("push",              END)

    return g.compile()
```

Mermaid 圖：

```
start → route → extract_features → expand_seeds
                                        ↓ ↓ ↓（並行）
                               seed_1  seed_2  seed_3
                                    \    |    /
                                   fuse_scores → generate → push → end
```

---

## 2-7  實際觀察差異

```bash
python scripts/demo_compare_variants.py \
  --query "Next.js 14 搭配 Server Components，Vercel 部署時 hydration 問題怎麼處理？" \
  --variants basic selfrag
```

預期輸出：

```
=== basic variant ===
Seeds:   1 (原始 query)
Hits:    [chunk_hydration_001, chunk_ssr_002, chunk_nextjs_003]
Top hit: "Next.js hydration error: what it means..."

=== selfrag variant ===
Seeds:   3
  seed_1 "Next.js 14 hydration error": 5 hits
  seed_2 "Server Components rendering": 4 hits
  seed_3 "Vercel SSR deployment": 3 hits
RRF fusion:
  chunk_ssr_002: 0.0328 (appeared in seed_1 + seed_3)
  chunk_vercel_004: 0.0322 (seed_2 + seed_3)
  chunk_hydration_001: 0.0161 (seed_1 only)
```

selfrag 多撈到了 Vercel 部署相關的 chunk，basic 沒有。

---

## ✏️ 本章任務

1. 完成 task-13（Feature Extractor 接進 graph）
2. 完成 task-14（Multi-seed fan-out + RRF fusion）
3. 對你領域的一個複合條件問題，記錄：
   - basic variant：幾個 chunk、top-1 是什麼
   - selfrag variant：展開幾條 seed、各命中幾個 chunk、fusion 後 top-1 是什麼
4. 切換三種 fusion 策略，觀察 top-3 chunk 的變化
5. 把觀察記在 `WEEK2.md`

---

## 📝 沒有蠢問題

**Q：Feature Extractor 的 LLM 呼叫會增加多少成本？**

A：用 `gpt-4.1-mini`，一次 feature extraction 約 $0.0001–0.0003。
每天 100 則訊息 = $0.01–0.03，通常可以接受。
如果成本敏感，改用 rule-based 或 hybrid 策略，見 2-3 節。

**Q：Seeds 展開越多越好嗎？**

A：不一定。Seeds 越多，latency 也越高（多次 embedding + 多次 vector search）。
通常 2–5 條 seed 是甜蜜點；超過 5 條邊際效益遞減。
Ch05 會用 eval 量化這個 trade-off。

**Q：我的領域問題通常比較簡單（單一條件），需要 multi-seed 嗎？**

A：Single-topic 問題走 multi-seed 只是多跑一次 embedding（約 +50ms），
而且 `expand_seeds` 會自動偵測到只有一條 seed。
建議統一走 selfrag，Ch04 的 judge 能進一步過濾品質。

---

## 🧠 腦力激盪

> 你的領域更適合哪種 fusion 策略？
>
> 提示：如果你的知識庫有「同一件事在多份文件重複說明」（例如：藥品仿單 × 3 份），
> Max 策略會把高分 chunk 排前面，但三份都說同一件事——資訊其實沒有增加。
>
> 如果知識庫的每份文件說的是不同面向（A 說原理、B 說操作、C 說案例），
> RRF 能讓三個面向的 chunk 都有機會進入最終排名。

---

## 🎯 本章里程碑

```
能向別人解釋：
「為什麼複合條件問題上 selfrag 比 basic 命中率高，
  而且不只是命中率，chunk 涵蓋的面向也更廣。」
```

---

上一章 → [Ch 01：Graph 起步](ch01-graph-basics.md)
下一章 → [Ch 02b：進階檢索三技 — HyDE / 混合檢索 / Reranker](ch02b-advanced-retrieval.md)
