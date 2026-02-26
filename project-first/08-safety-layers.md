# 第八章：四層防護 — RAG 安全體系

## 學習目標

讀完本章，你將能夠：
- 將 Defense in Depth 概念應用到 RAG 系統的安全設計
- 區分四層防護在 RAG 中的具體職責
- 設計適合企業 RAG 系統的 HITL（人在環中）分級觸發機制
- 理解 RAG 幻覺防護層的「零破壞性輸出」原則

---

## 8.1 Defense in Depth：RAG 的縱深防禦

### RAG 面臨的三類威脅

不同於傳統軟體面對的是外部攻擊者，  
RAG 系統同時面對三類威脅：

**威脅一：知識污染（Knowledge Poisoning）**  
過時、錯誤或未授權的文件進入知識庫，導致 AI 引用錯誤資訊。

**威脅二：幻覺生成（Hallucination）**  
LLM 無法從文件中找到答案時，用訓練記憶「發明」答案。

**威脅三：越權存取（Unauthorized Access）**  
使用者透過 RAG 查詢到無權限的知識（如其他部門的機密文件）。

### RAG 的四層防護架構

```
┌──────────────────────────────────────────────────────────┐
│  Layer 4: 流程層 (Governance Gates YAML)                  │ ← 知識品質閘門
│  「這批文件的 Retrieval Hit@5 達標了嗎？ADR 有更新嗎？」  │
├──────────────────────────────────────────────────────────┤
│  Layer 3: 操作層 (Human Review Triggers)                  │ ← 人類確認閘門
│  「更換嵌入模型影響所有部門？必須人類確認。」              │
├──────────────────────────────────────────────────────────┤
│  Layer 2: 語意層 (Semantic Deny Rules)                    │ ← 知識意圖阻擋
│  「禁止跨 namespace 的 global 搜尋」                      │
├──────────────────────────────────────────────────────────┤
│  Layer 1: 技術層 (API Config + Invariants)               │ ← 硬性技術限制
│  「temperature 不得超過 0.3；不得使用 gpt-4o-mini」       │
└──────────────────────────────────────────────────────────┘
```

---

## 8.2 四層防護的具體實作

### Layer 1：技術層（API 設定 + 不變量）

```python
# 檔案：src/config/llm_config.py

class LLMConfig:
    """
    LLM 的硬性設定限制。
    這些值來自 Constitution，不允許在 runtime 動態修改。
    (Constitution INV-6、INV-7)
    """

    # 絕對不允許的模型（精簡模型不用於生產環境問答）
    FORBIDDEN_MODELS = frozenset([
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ])

    # 溫度上限（Constitution Principle II）
    MAX_TEMPERATURE = 0.3

    # 最大輸出 token（防止超長幻覺）
    MAX_TOKENS = 1000

    @classmethod
    def validate(cls, model: str, temperature: float, max_tokens: int):
        """硬性驗證：違反規則直接拋出例外，不執行 API 呼叫"""
        if model in cls.FORBIDDEN_MODELS:
            raise ConfigViolationError(
                f"模型 '{model}' 被 Constitution 禁止用於生產環境問答。"
                f"請使用 gpt-4o 或 gpt-4-turbo。"
            )
        if temperature > cls.MAX_TEMPERATURE:
            raise ConfigViolationError(
                f"temperature={temperature} 超過上限 {cls.MAX_TEMPERATURE}。"
                f"（Constitution Principle II：幻覺零容忍）"
            )
        if max_tokens > cls.MAX_TOKENS:
            raise ConfigViolationError(
                f"max_tokens={max_tokens} 超過上限 {cls.MAX_TOKENS}。"
            )
```

### Layer 2：語意層（知識存取的語意規則）

```markdown
# 檔案：.agent/rules/semantic-deny.md
# RAG 系統的語意禁止規則

## 知識存取規則

| ID | 規則 | 模組 |
|----|------|------|
| KA-1 | 禁止對向量 DB 執行不帶 namespace 過濾的全域搜尋 | 檢索器 |
| KA-2 | 禁止在 system prompt 中使用 「忽略以上指示」相關繞過詞彙 | 生成器 |
| KA-3 | 禁止攝取 status != "approved" 的文件 | 攝取器 |
| KA-4 | 禁止直接刪除向量 DB 中的 chunk（必須先 deprecate） | 所有寫入 |
| KA-5 | 禁止將不同部門的 namespace 合併到同一個查詢中（除非 Namespace Gate 允許） | 檢索器 |
| MCP-1 | MCP Server 禁止暴露原始向量（只能返回文字 chunks） | MCP Server |
| MCP-2 | 禁止 MCP Server 自行修改知識庫（只讀模式） | MCP Server |
```

### Layer 3：操作層（Human Review Triggers）

```markdown
# 檔案：.agent/rules/human-review-triggers.md
# RAG 系統的人類確認觸發機制

## LEVEL 1 — MUST STOP（絕對必須人類確認後才能繼續）

觸發條件：
- 更換嵌入模型（影響所有 namespace，需要全面 re-embed）
- 新增跨部門的 namespace 存取權限
- 修改 Constitution（任何版本升級）
- 清除超過 100 份文件（批次刪除）
- 更改 Retrieval Gate 的 MIN_SCORE 閾值
- 接入新的外部知識來源（Confluence、SharePoint 等）

處理方式：AI Agent 停止操作，向人類報告計畫，等待明確確認。

---

## LEVEL 2 — SHOULD CONFIRM（建議確認，session 內可授權）

觸發條件：
- 新增一個新的 namespace（單部門）
- 批次攝取超過 50 份文件
- 修改 system prompt 的核心內容
- 更新 Chunking 參數（target_size 或 overlap）
- 修改任何 MCP Server 的工具定義

---

## LEVEL 3 — NOTIFY AFTER（完成後通知，不需要事前確認）

觸發條件：
- 單份文件的常規更新攝取
- 廢棄過期文件（在授權的清理任務中）
- 更新 Retrieval Gate 的日誌格式
- 修改 Action Log 模板
```

### Layer 4：流程層（RAG 特有的治理閘門）

```yaml
# 檔案：.agent/skills/governance/rules/knowledge_quality_gate.yaml

name: Knowledge Quality Gate
description: >
  在新的知識批次上線前，驗證 Retrieval 品質達到標準。
  對應 Constitution Principle I（知識品質優先）。

trigger:
  - event: batch_ingest_completed
    condition: chunk_count > 50  # 大批次才觸發，小更新用 Lite 模式

checks:
  - id: QC-1
    name: Retrieval Hit@5
    description: 使用標準測試集驗證 Retrieval 準確率
    threshold: 0.80  # Hit@5 >= 80%
    action_on_fail: block

  - id: QC-2
    name: Metadata Completeness
    description: 所有 chunk 必須有完整的 metadata
    required_fields: [source, doc_id, chunk_index, last_updated, status, owner]
    action_on_fail: block

  - id: QC-3
    name: Namespace Isolation Test
    description: 驗證新 namespace 不會洩漏到其他 namespace 的查詢中
    action_on_fail: block

decision:
  all_pass: allow
  any_fail: block_and_notify_admin
```

---

## 8.3 HITL in RAG：人在環中的設計

### RAG 為什麼特別需要 HITL

RAG 系統的決策影響是「廣播式」的：

- 一個 bug 修改了 10 行程式碼，影響使用這個功能的 100 個用戶
- 一個錯誤的 RAG 更新，影響查詢這個知識域的所有用戶（可能是全公司）

更重要的是，用戶通常「信任 AI 的答案」，不會主動驗證。  
這讓知識錯誤的傳播速度比程式碼 bug 快得多。

### HITL 豁免機制

```python
# 檔案：src/governance/hitl_checker.py

class HITLChecker:
    """
    在執行高風險操作前，檢查是否需要人類確認。
    有三種豁免條件。
    """

    def should_proceed(
        self,
        operation: str,
        session_context: dict,
    ) -> tuple[bool, str]:
        """
        回傳 (是否可以繼續, 原因說明)
        """

        level = self._get_risk_level(operation)

        if level == 1:
            # LEVEL 1：無論如何都必須停止等待確認
            return False, (
                f"操作「{operation}」屬於 Level 1 高風險操作，"
                f"必須等待管理員確認後才能繼續。"
            )

        if level == 2:
            # LEVEL 2：有三種豁免條件

            # 豁免 1：Session 授權
            if operation in session_context.get("authorized_ops", []):
                return True, "Session 已授權此操作"

            # 豁免 2：Task Pack 核准
            if self._is_approved_in_task_pack(operation, session_context):
                return True, "Task Pack 已核准此操作"

            # 豁免 3：緊急修復模式
            if session_context.get("mode") == "urgent_fix":
                return True, "緊急修復模式，Level 2 操作自動授權"

            # 沒有豁免條件：建議確認
            return False, (
                f"操作「{operation}」屬於 Level 2 中風險操作，"
                f"建議確認後繼續。"
                f"如需授權，請在 session 開始時說明。"
            )

        # LEVEL 3：直接執行，完成後通知
        return True, "Level 3 操作，執行後將通知管理員"
```

---

## 8.4 幻覺防護層（Hallucination Shield）

### 問題：LLM 在知識不足時「自行填補」

```python
# ❌ 沒有幻覺防護的查詢系統
def answer_without_shield(question, chunks):
    # 直接把 chunks 給 LLM，希望它「自律」
    response = gpt4o.chat(
        system="你是企業知識庫助手",
        user=f"文件：{chunks}\n問題：{question}"
    )
    return response  # 若 chunks 不相關，LLM 可能用訓練記憶作答
```

```python
# ✅ 有幻覺防護的查詢系統

class HallucinationShield:
    """
    幻覺防護層：在生成答案後，驗證答案是否有足夠的文件支撐。
    
    核心原則（對應 WFGY 的「零破壞性」）：
    - Shield 永遠不修改 LLM 的原始輸出
    - 只能標記、評分和建議
    - 使用者看到原始答案 + Shield 的可信度評分
    """

    def validate_answer(
        self,
        question: str,
        answer: str,
        source_chunks: list[dict],
    ) -> dict:
        """
        驗證 LLM 的答案是否有文件支撐。

        Returns:
            {
                "answer": str,              # 原始答案（不修改）
                "reliability_score": float,  # 0.0 ~ 1.0
                "grounded": bool,           # 是否有文件支撐
                "warnings": list[str],      # 警告（如：答案中有文件未提及的聲明）
                "sources": list[str],       # 引用的文件 ID
            }
        """
        # 計算答案與文件的語意相似度
        answer_vector = self.embedder.embed(answer)
        chunk_vectors = [self.embedder.embed(c["text"]) for c in source_chunks]

        max_similarity = max(
            cosine_similarity(answer_vector, cv) for cv in chunk_vectors
        )

        # 檢查答案是否包含文件中未出現的關鍵數字/日期
        ungrounded_claims = self._detect_ungrounded_claims(answer, source_chunks)

        reliability_score = max_similarity * (1.0 - 0.2 * len(ungrounded_claims))
        reliability_score = max(0.0, min(1.0, reliability_score))

        warnings = []
        if ungrounded_claims:
            warnings.append(
                f"答案中有 {len(ungrounded_claims)} 個聲明無法在來源文件中找到依據"
            )
        if reliability_score < 0.6:
            warnings.append("答案可信度偏低，建議人工驗證")

        return {
            "answer": answer,  # 絕對不修改原始答案
            "reliability_score": round(reliability_score, 3),
            "grounded": reliability_score >= 0.7,
            "warnings": warnings,
            "sources": [c["doc_id"] for c in source_chunks],
        }
```

---

## 8.5 四層的互補關係

| 威脅類型 | L1 技術 | L2 語意 | L3 操作 | L4 流程 |
|---------|:-------:|:-------:|:-------:|:-------:|
| temperature=0.8 的幻覺請求 | 擋住 | — | — | — |
| 跨 namespace 全域搜尋 | — | 擋住 | — | — |
| 更換嵌入模型（影響全系統） | — | — | 擋住 | — |
| 大批次知識品質未達標就上線 | — | — | — | 擋住 |

> **四層缺一不可**：技術層只能擋硬性設定違規；語意層只能擋已知的不良模式；  
> 操作層靠人類判斷；流程層靠自動化驗證。  
> 只有四層一起運作，才能覆蓋 RAG 系統的主要風險。

---

## 練習

1. **分類練習**：以下操作應該由哪一層防護處理？
   - (a) 攝取一份 last_updated 超過 365 天的文件
   - (b) 在 retriever 中直接查詢 `namespace="*"`（萬用字元）
   - (c) 更新公司所有部門的知識庫（全域更換 Chunking 參數）
   - (d) 新批次的文件 Retrieval Hit@5 只有 62%，低於標準的 80%

2. **HITL 設計練習**：為一個「面向客戶的產品問答 RAG 系統」設計 LEVEL 1 觸發條件（至少 5 個）。想一想：哪些操作的錯誤代價最高？

3. **幻覺防護思考題**：`HallucinationShield` 的 `_detect_ungrounded_claims()` 應該怎麼設計？它需要偵測哪些類型的「未支撐聲明」？舉 3 個例子。

4. **Defense in Depth 設計**：如果你的 RAG 系統預算有限，只能實作其中 2 層，你會選哪 2 層？為什麼？

---

> **下一章**：[第九章：MCP Server 與 Skills 運營模式](09-mcp-server-and-skills.md)  
> 我們將學習如何用 MCP Server 標準化知識存取接口，以及如何設計 Skills 技能模組。
