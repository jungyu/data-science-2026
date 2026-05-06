# Spec-19：三種 LangGraph 變體並陳 + 比較示範

## 背景

[`docs/RAG/LangGraph/ch06`](../../RAG/LangGraph/ch06-rag-vs-selfrag-vs-reflection.md) 把 RAG 演化分成三階段：

1. **基本 RAG**：查一次，答一次（線性）
2. **Self-RAG**：查完判斷夠不夠，必要時再查（單一迴圈）
3. **Reflection Agent**：多軸自評 + 條件分支（多分支迴圈）

P1 → P4 完成時，graph 內部其實會經歷這三個形態，但**每個 phase 的 task 都是「取代」前一版 graph**——學生跑完 P4 就只剩最複雜的版本，無法回頭跑簡單版做比對。

本 spec 調整為：每個關鍵 phase 完成時，**註冊一個新的 graph builder**，舊版保留。最終 `app/graph/variants/` 目錄有三個 builder 並存，env var 切換要用哪個。

## 設計

### 變體對照表（與 ch06 章節對齊）

| 變體 | builder | 對應 phase | 對應 ch06 模式 | Graph 結構 |
|---|---|---|---|---|
| `basic` | `build_basic_graph()` | P1 完成 | 基本 RAG | `route → retrieve → simple_generate → push` |
| `selfrag` | `build_selfrag_graph()` | P3 完成 | Self-RAG | `route → extract → expand → retrieve×N → fuse → sufficiency? → (clarify ∥ contract → narrative) → push` |
| `reflection` | `build_reflection_graph()` | P4 完成 | Reflection Agent | selfrag + `judge` 三向分流（pass / retry / force_push）|

P2（multi-seed）單獨不算一個變體——它是 selfrag 的內部結構升級，沒有「完整跑得起來、可單獨 demo」的形態。

### 共享層

三變體共用：

- **State schema**：`app/graph/state.py::RAGState`（用 `total=False`，較簡單變體忽略多出來的欄位）
- **Node 函式庫**：`app/graph/nodes.py` 的所有 node。每個變體在 builder 中組合不同的 node 子集
- **Service 注入**：`RuntimeServices` 提供所有 node 需要的依賴；變體只挑用得到的部分

### Builder 介面契約

```python
# app/graph/variants/__init__.py
from app.graph.variants.basic import build_basic_graph
from app.graph.variants.selfrag import build_selfrag_graph
from app.graph.variants.reflection import build_reflection_graph

VARIANT_BUILDERS = {
    "basic": build_basic_graph,
    "selfrag": build_selfrag_graph,
    "reflection": build_reflection_graph,
}
```

每個 builder 簽章一致：

```python
def build_basic_graph(services: RuntimeServices) -> CompiledGraph: ...
def build_selfrag_graph(services: RuntimeServices) -> CompiledGraph: ...
def build_reflection_graph(services: RuntimeServices) -> CompiledGraph: ...
```

### 啟動切換

```bash
# .env
GRAPH_VARIANT=reflection   # basic | selfrag | reflection
```

`Settings` 加：

```python
graph_variant: Literal["basic", "selfrag", "reflection"] = "reflection"
```

`get_runtime_services()` 在 build graph 時讀這個值：

```python
builder = VARIANT_BUILDERS[settings.graph_variant]
object.__setattr__(services, "rag_graph", builder(services))
```

### 比較 demo 腳本

新增 `scripts/demo_compare_variants.py`：對同一個 query，依序在三個變體上跑，輸出對比表。**不需要 LINE webhook、不寫 DB**——直接 print 結果。

預期輸出：

```
Query: "Next.js 14 SSR hydration mismatch 怎麼處理？"

[basic]
  flow: route → retrieve(1) → generate → push
  retrieved: 4 chunks
  response (first 200 chars): "Hydration mismatch 通常..."
  duration: 3.2s

[selfrag]
  flow: route → extract → expand(3 seeds) → retrieve×3 → fuse(max) → sufficient → contract → narrative
  retrieved: 7 unique chunks
  contract: {summary, 4 findings, 1 caveat, 4 citations}
  response (first 200 chars): "**摘要**：..."
  duration: 5.1s

[reflection]
  flow: selfrag + judge → pass
  judge: {ground:9, cite:8, format:8, uncert:7} → pass
  retry: 0
  response (first 200 chars): "**摘要**：..."
  duration: 7.4s

[diff]
  basic vs selfrag: +3 chunks, +citations, +caveats
  selfrag vs reflection: response 經 judge 通過，無重生成
```

### 不做什麼

- 不做 UI 對比工具（terminal 輸出夠教學用）
- 不做 batch evaluation（屬 P5 retrieval analytics）
- 不做變體間的自動 A/B 測試（學生可自行擴充）

## 介面契約

**新增**：`app/graph/variants/__init__.py`、`basic.py`、`selfrag.py`、`reflection.py`

**修改**：

- `app/config.py`：加 `graph_variant` 設定
- `app/dependencies.py::get_runtime_services()`：依 `graph_variant` 選 builder
- `app/graph/rag_graph.py`：保留作向後相容的薄包裝，內部呼叫 `VARIANT_BUILDERS["reflection"]`（或預設值）；標記為 deprecated 並指向 variants/

**新增**：`scripts/demo_compare_variants.py`、`docs/ai-agent/examples/variants-comparison.md`

**現有 spec/task 的影響**：

| Spec/Task | 變動 |
|---|---|
| spec-12 / task-12 | builder 命名為 `build_basic_graph`，放 `variants/basic.py` |
| spec-14 / task-14 | multi-seed 加在 selfrag builder 內，**basic 變體不動** |
| spec-15 / task-15 | sufficiency + clarify 加在 selfrag builder 內 |
| spec-16 / task-16 | two-stage generator 加在 selfrag builder 內；basic 變體繼續用 simple_generate_node |
| spec-17 / task-17 | judge + reflection 加在 reflection builder 內，selfrag 不動 |

每個 task 在「請輸出」段加一行：「將 builder 註冊進 `VARIANT_BUILDERS`，舊變體不刪」。

## 驗收標準

- 三個 variant 都能用 `GRAPH_VARIANT=xxx` 切換並正常跑通同一個問題
- `scripts/demo_compare_variants.py` 一鍵跑出對比輸出
- `docs/ai-agent/examples/variants-comparison.md` 至少 3 個案例（FAQ 級、技術問題、知識庫沒涵蓋）展示三變體的差異
- Variant 之間共用 `RAGState` 不會 schema 衝突（簡單變體的 final state 可缺欄位）
- 三 variant 的 graph 都能 `get_graph().draw_mermaid()` 畫出來貼在 doc 中
- README 對齊 ch06：「三種 RAG 對應到本專案的三變體」表格
