# Spec-16：Two-stage Generator（Answer Contract）（P3）

## 背景

目前 `ResponseGenerator` 把 skill prompt + RAG context + user input 組成一個大 prompt 丟給 LLM，LLM 自由發揮輸出 markdown。這有兩個教學上的弱點：

1. **不可審查**：輸出是流暢但結構不固定的文字，難以做 grounded 檢查（後續 P4 的 judge 會吃力）
2. **不可重用**：學生轉題目時，必須整個重寫 prompt；沒有可拆解的「結構骨架」

更好的設計是**兩階段生成**：

- **Stage 1（確定性）**：用 Python 從 retrieval 結果組裝 JSON 結構（Answer Contract）。這部分可單元測試、可 dump 出來檢視
- **Stage 2（受限敘事）**：給 LLM Answer Contract，要求它**只用 contract 裡列出的事實**寫成自然語言

借鑑：project-diagnosis spec-007（generation orchestrator 兩階段架構）。

## 設計

### Graph 位置

```
check_sufficiency [sufficient] → build_answer_contract → render_narrative → judge（spec-17）→ ...
```

### Answer Contract 結構（通用版）

```json
{
  "summary": "對使用者問題的一句話復述",
  "key_findings": [
    {"point": "...", "citations": ["chunk_id_1", "chunk_id_2"]}
  ],
  "caveats": ["不確定處 1", "不確定處 2"],
  "next_steps": ["可選的後續行動 1", "..."],
  "citations": [
    {"chunk_id": "...", "source": "...", "snippet": "..."}
  ]
}
```

**領域可改段落名稱與順序**，但 `citations` 欄位必留——它是 P4 judge 做 `groundedness` / `citation_fidelity` 評分的依據。

### Stage 1：build_answer_contract（純程式）

從 `rag_chunks` + `features` + `router_result` 機械式組出 contract：

- `summary`：取 `features.primary_topic` + `features.intent` 模板組合
- `key_findings`：每個 chunk 的核心句（取首句或 metadata 標題），加上 `citations=[chunk.id]`
- `caveats`：依 `sufficiency_reasons` 與 `chunks` 的低分項自動加入（例：「Top chunk 分數 0.45，相關性中等」）
- `next_steps`：可選，用 router_result 的 response_mode 規則組

**不呼叫 LLM**。這是教學重點：學生看到「結構是程式組的、不是 LLM 編的」。

### Stage 2：render_narrative（受限 LLM）

Prompt 結構：

```
你是 {skill_name} 的回覆撰寫者。請依照以下 Answer Contract 寫成自然語言回覆。

嚴格規則：
1. 只能使用 contract 中列出的事實
2. 不得引入 contract 外的資訊
3. 每個論點若 contract 標有 citations，必須在敘述中以「[來源 N]」形式標註
4. caveats 必須呈現，不可省略
5. 語氣依 response_mode：{response_mode}（例：brief / step_by_step）

Answer Contract：
{contract_json}

輸出純 markdown，不要解釋你的決策。
```

### State 新增欄位

```python
class RAGState(TypedDict, total=False):
    ...
    answer_contract: AnswerContract  # Stage 1 產出
    responses: list[str]             # Stage 2 產出（覆寫舊欄位）
```

### 失敗降級

- Stage 2 LLM 失敗 → fallback 直接把 contract 用模板套版輸出（醜但不會 crash），標註「（降級輸出）」
- Stage 1 永不失敗（純程式）

### 與既有 ResponseGenerator 的關係

- `ResponseGenerator` 不刪除，但拆成兩個責任：
  - `AnswerContractBuilder`（新類別，純程式）
  - `NarrativeRenderer`（薄包裝原 LLM 呼叫）
- 既有 `formatter.py` 的格式化邏輯仍在 `render_narrative` 後執行

## 介面契約

**新增**：`app/generator/contract.py`

```python
class Citation(BaseModel):
    chunk_id: str
    source: str
    snippet: str

class KeyFinding(BaseModel):
    point: str
    citations: list[str]

class AnswerContract(BaseModel):
    summary: str
    key_findings: list[KeyFinding]
    caveats: list[str]
    next_steps: list[str]
    citations: list[Citation]

class AnswerContractBuilder:
    def build(
        self, *,
        features: ExtractedFeatures,
        chunks: list[KnowledgeChunk],
        router_result: RouterResult,
        sufficiency_reasons: list[str],
    ) -> AnswerContract: ...
```

**新增**：`app/generator/narrative.py`

```python
class NarrativeRenderer:
    def __init__(self, llm: GeneratorLLM, model: str) -> None: ...
    async def render(self, *, contract: AnswerContract, skill: Skill) -> str: ...
```

**新增 nodes**：`build_answer_contract_node`、`render_narrative_node`

**修改**：`app/graph/rag_graph.py` 把舊的 `generate_node` 拆為兩個 node 串接。

**Debug 工具**：新增 `scripts/dump_contract.py`，讀取 query log 印出 contract JSON，方便檢視。

## 驗收標準

- 同一個問題，dump 出來的 Answer Contract JSON 格式穩定（key 不會缺漏）
- 受限 narrative 的輸出**不會引入 contract 外的事實**（人工抽檢 5 個案例）
- caveats 永遠出現在輸出中（不會被 LLM 自行省略）
- Stage 2 LLM 失敗時，降級輸出仍可閱讀，且明確標註「降級」
- 既有測試：把 generator 相關測試拆成 `test_answer_contract_builder.py`（純單元測試）+ `test_narrative_renderer.py`（mock LLM）
