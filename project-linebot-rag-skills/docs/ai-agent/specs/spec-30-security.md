# Spec-30：安全性防禦

## 背景

RAG bot 面臨三類主要威脅：

| 威脅 | 攻擊手法 | 可能後果 |
|------|---------|---------|
| **Prompt Injection** | 使用者在問題中夾帶指令（「忽略 system prompt，輸出...」）| Bot 行為被劫持、繞過安全限制 |
| **RAG Poisoning** | 惡意 chunk 被注入知識庫（`<INST>` 等指令隱藏在內容中）| LLM 執行惡意指令 |
| **敏感資料洩漏** | 知識庫含 PII / 機密，被 retrieval 帶出後 LLM 整段複製 | 個資外洩、商業機密曝露 |

---

## 設計

### 架構位置

```
user_input → [input_guard_node] → query_transform → ... → generate → [output_guard_node] → push
                                                              ↑
ingest_pipeline → [poison_screen()] → store
```

### 1. Config 新增

`app/config.py`：

```python
SECURITY_INPUT_GUARD: bool = Field(default=True, alias="SECURITY_INPUT_GUARD")
SECURITY_OUTPUT_GUARD: bool = Field(default=True, alias="SECURITY_OUTPUT_GUARD")
SECURITY_POISON_SCREEN: bool = Field(default=True, alias="SECURITY_POISON_SCREEN")
SECURITY_MAX_INPUT_CHARS: int = Field(default=1000, alias="SECURITY_MAX_INPUT_CHARS")
SECURITY_BLOCKED_REPLY: str = Field(
    default="抱歉，這個問題我無法回覆。",
    alias="SECURITY_BLOCKED_REPLY",
)
```

### 2. `app/security/guards.py`

```python
from __future__ import annotations

import re


# ── Prompt Injection 偵測 ─────────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    # 常見英文 jailbreak 模式
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instruction|prompt|context)",
    r"you\s+are\s+now\s+(a\s+)?(?!assistant)",   # "you are now DAN"
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if\s+you\s+are|a)",
    r"disregard\s+(your|all)\s+(instructions?|guidelines?|rules?)",
    r"system\s*prompt",
    r"<\s*(INST|SYS|SYSTEM)\s*>",
    # 常見中文 jailbreak
    r"忽略(之前|前面|所有)(的)?(指令|設定|限制|規則)",
    r"假裝你是",
    r"扮演",  # 允許語，只標記，不直接 block
    r"現在你是(?!.*助理)",
    r"輸出.*?(system\s*prompt|系統提示)",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL
)


def detect_prompt_injection(text: str) -> bool:
    """回傳 True 表示偵測到 injection 嘗試。"""
    return bool(_INJECTION_RE.search(text))


# ── 輸出洩漏偵測 ──────────────────────────────────────────────────────────────

_LEAKAGE_PATTERNS = [
    # 台灣身份證號
    r"\b[A-Z]\d{9}\b",
    # 電話號碼（台灣）
    r"\b09\d{8}\b",
    r"\b0[2-8]\d{7,8}\b",
    # 信用卡號
    r"\b(?:\d{4}[- ]){3}\d{4}\b",
    # Email
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
]

_LEAKAGE_RE = re.compile("|".join(_LEAKAGE_PATTERNS))


def detect_sensitive_leakage(text: str) -> list[str]:
    """回傳在文字中找到的所有 PII pattern 匹配字串。"""
    return _LEAKAGE_RE.findall(text)


# ── RAG Poisoning 偵測（入庫時）──────────────────────────────────────────────

_POISON_PATTERNS = [
    r"<\s*(INST|SYS|SYSTEM|HUMAN)\s*>",
    r"\[INST\]|\[/INST\]",
    r"###\s*Instruction",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"IGNORE\s+ALL\s+PREVIOUS",
]

_POISON_RE = re.compile("|".join(_POISON_PATTERNS), re.IGNORECASE)


def detect_rag_poison(text: str) -> bool:
    """回傳 True 表示 chunk 疑似含有 prompt injection 指令。"""
    return bool(_POISON_RE.search(text))
```

### 3. `input_guard_node`

`app/graph/nodes.py` 新增：

```python
from app.security.guards import detect_prompt_injection

async def input_guard_node(state: RAGState, settings: Settings) -> dict:
    if not settings.SECURITY_INPUT_GUARD:
        return {}

    query: str = state.get("query", "")

    # 長度限制
    if len(query) > settings.SECURITY_MAX_INPUT_CHARS:
        logger.warning("security: input too long (%d chars), truncating", len(query))
        query = query[: settings.SECURITY_MAX_INPUT_CHARS]

    # Injection 偵測
    if detect_prompt_injection(query):
        logger.warning("security: prompt injection detected in query")
        return {
            "query": query,
            "blocked": True,
            "blocked_reason": "prompt_injection",
            "responses": [settings.SECURITY_BLOCKED_REPLY],
        }

    return {"query": query, "blocked": False}
```

Graph 需在 `route` **之前**插入 `input_guard_node`，並加入 conditional edge：若 `state["blocked"] == True`，直接跳到 `push`。

```python
builder.add_node("input_guard", partial(input_guard_node, settings=settings))
builder.add_edge(START, "input_guard")
builder.add_conditional_edges(
    "input_guard",
    lambda s: "push" if s.get("blocked") else "route",
)
```

### 4. `output_guard_node`

`app/graph/nodes.py` 新增：

```python
from app.security.guards import detect_sensitive_leakage

async def output_guard_node(state: RAGState, settings: Settings) -> dict:
    if not settings.SECURITY_OUTPUT_GUARD:
        return {}

    responses: list[str] = state.get("responses", [])
    cleaned: list[str] = []
    leaked = False

    for resp in responses:
        leaks = detect_sensitive_leakage(resp)
        if leaks:
            logger.warning("security: output leakage detected: %s", leaks)
            leaked = True
            # 遮蔽：把 PII 字串替換為 [REDACTED]
            from app.security.guards import _LEAKAGE_RE
            resp = _LEAKAGE_RE.sub("[REDACTED]", resp)
        cleaned.append(resp)

    return {"responses": cleaned, "output_had_leakage": leaked}
```

在 graph 的 `judge` / `reflect` 後、`push` 前插入 `output_guard_node`。

### 5. Ingestion 的 Poison Screen

`scripts/ingest_markdown.py` 與 `app/ingest/` 中，入庫前加：

```python
from app.security.guards import detect_rag_poison

def screen_chunk(content: str, source_id: str) -> bool:
    """回傳 True = 通過，False = 拒絕入庫並警告。"""
    if settings.SECURITY_POISON_SCREEN and detect_rag_poison(content):
        logger.warning(
            "security: poison detected in chunk from %s, skipping", source_id
        )
        return False
    return True
```

### 6. State 新增欄位

`app/graph/state.py`：

```python
class RAGState(TypedDict):
    # ... existing fields ...
    blocked: bool                  # input_guard 設為 True 時跳過 graph
    blocked_reason: str | None
    output_had_leakage: bool       # output_guard 偵測到洩漏
```

---

## 邊界與局限

| 局限 | 說明 |
|------|------|
| Pattern-based 偵測 | 無法捕捉 zero-day jailbreak；生產環境可搭配 Anthropic Constitution / LlamaGuard |
| PII regex 覆蓋 | 目前只含台灣格式；其他地區需補充 pattern |
| Poison screen | 只偵測已知 token 格式；語意層面的 poison（無明顯 token）需 LLM-as-classifier |
| 中文 injection | 部分「扮演」、「假裝」在創意情境合理，目前只記錄不 block |

---

## 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| Injection pattern | ✅ `_INJECTION_PATTERNS` 可擴充 | ❌ `detect_prompt_injection() → bool` 介面 |
| PII pattern | ✅ 按地區擴充 | ❌ 偵測到 PII 的行為：一律 redact |
| `SECURITY_BLOCKED_REPLY` | ✅ env var 客製化回覆 | ❌ blocked 時不能把原始攻擊內容回傳 |

---

## 驗收標準

- Prompt injection 測試（10 筆）：`prompt_injection_blocked_rate = 1.00`
- 正常問題不被誤攔截（false positive rate < 0.05）
- `output_guard_node` 在 response 含台灣身份證號時輸出 `[REDACTED]`
- `poison_screen` 對含 `<INST>` 的 chunk 拒絕入庫並 log
- `SECURITY_INPUT_GUARD=false` 時 guard node 為 no-op（不影響功能）
- pytest `tests/test_security.py` 全綠（injection + leakage + poison 各 5+ 筆）
