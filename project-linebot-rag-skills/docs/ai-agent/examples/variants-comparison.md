# 三種 LangGraph 變體對照（對應 ch06）

> 本檔對應 [spec-19](../specs/spec-19-graph-variants.md) / [task-19](../tasks/task-19-graph-variants.md)。
> 三變體的 mermaid 圖由 `scripts/dump_graph_mermaid.py` 產出。

## 對照表

| 變體 | ch06 模式 | 對應 phase | mermaid 圖 | 適用場景 |
|------|-----------|-----------|-----------|----------|
| `basic` | §1 基本 RAG | P1 完成 | [graph-basic.mermaid](./graph-basic.mermaid) | FAQ、簡單問答 |
| `selfrag` | §2 Self-RAG | P3 完成 | [graph-selfrag.mermaid](./graph-selfrag.mermaid) | 知識庫查詢、技術問答 |
| `reflection` | §3 Reflection Agent | P4 完成 | [graph-reflection.mermaid](./graph-reflection.mermaid) | 高風險領域、需可審計輸出 |

切換：

```bash
GRAPH_VARIANT=basic ./scripts/run_local.sh
GRAPH_VARIANT=selfrag ./scripts/run_local.sh
GRAPH_VARIANT=reflection ./scripts/run_local.sh   # 預設
```

## 三變體跑同一輸入的差異（教學示範案例）

> 這些是學生實際跑 `python scripts/demo_compare_variants.py "<query>"` 後**預期看到**的觀察。
> 實際數字會因 LLM 抖動 ±5 分內波動，模式不會變。

### 案例 1：知識庫充分覆蓋的問題

Query: `"什麼是 RAG？"`

| | basic | selfrag | reflection |
|---|---|---|---|
| chunks | 4 | 6 | 6 |
| seeds | 1（單 seed）| 3（多 seed）| 3 |
| sufficiency | (n/a) | sufficient | sufficient |
| judge | (n/a) | (n/a) | pass |
| retry | 0 | 0 | 0 |
| 回覆風格 | 流水帳，無引用 | 帶 `[來源 N]` | 同 selfrag，多一道 4 軸審查 |
| latency 量級 | 1× | 1.5–2× | 2–3× |

→ 三者都答得出來。**Self-RAG 開始變得「可信」**（multi-seed + citation）。Reflection 多花 ~50% 成本換一道審查保障。

### 案例 2：複合條件問題

Query: `"我用 Next.js 14 做 SSR，hydration mismatch 怎麼處理？"`

| | basic | selfrag | reflection |
|---|---|---|---|
| chunks | 3（單 query embedding 易稀釋）| 7（multi-seed 命中各條件）| 7 |
| 回覆切題度 | 中 | 高 | 高 |
| 引用 | 無 | `[來源 1] [來源 2]` | 同 selfrag |

→ **Multi-seed 在多條件問題上的價值最明顯**。basic 容易給「廣但淺」的答案。

### 案例 3：知識庫沒涵蓋的問題

Query: `"怎麼用 LangGraph 接 Kubernetes Operator？"`

| | basic | selfrag | reflection |
|---|---|---|---|
| chunks | 0 | 0 | 0 |
| sufficiency | (n/a) | **insufficient** | **insufficient** |
| 回覆 | 「目前知識庫沒有...」+ 強行生成（可能 hallucinate） | 走 clarify 分支，產生 2~3 個具體追問 | 同 selfrag |

→ **Self-RAG 開始有真正價值**：誠實追問比強行生成有用得多。
→ Reflection 在 insufficient 路徑上**沒走 judge**（資料不足無從審），與 selfrag 行為一致。

### 案例 4：易誘發 hallucination 的問題（測試 grounding）

Query: `"請列出 RAG 系統的所有評估指標"`（知識庫只有部分）

| | basic | selfrag | reflection |
|---|---|---|---|
| 杜撰風險 | 高（LLM 自由發揮） | 中（contract 約束 + caveat） | **低**（judge 4 軸驗 grounding） |
| 失敗時回覆 | 完整但部分錯 | 不完整 + 標記不確定 | retry 後仍不確定 → ⚠️ 品質警告 |

→ **Reflection 的 judge 在這類場景才看得出價值**。低風險題目用 selfrag 即可。

## 觀察重點 — 學生該記下的三件事

1. **複雜度 vs 品質 trade-off 不是線性**
   - basic → selfrag：品質 jump（multi-seed + sufficiency + grounded generation）
   - selfrag → reflection：品質 incremental（多一層自審），但 latency / cost 顯著增加
2. **看 ch06 §「該用哪個」三問題決定**
   - 答錯有沒有後果？沒後果用 basic
   - 知識庫詞彙跟使用者語言落差大？大，用 selfrag 起跳
   - 高風險領域？直接 reflection
3. **變體切換**只改 env var，不重 build，不動 graph 程式碼。這是 spec-19 設計的硬要求

## 跑法

```bash
# 安裝（含三 variant）
python -m pip install -e ".[dev]"

# 比較同一個 query 在三變體下的行為（不會真的推 LINE）
python scripts/demo_compare_variants.py "什麼是 RAG？"
python scripts/demo_compare_variants.py "Next.js 14 SSR hydration mismatch"
python scripts/demo_compare_variants.py "LangGraph 怎麼接 Kubernetes Operator？"

# 重新產生三變體 mermaid 圖（拓撲變更時跑）
python scripts/dump_graph_mermaid.py
```
