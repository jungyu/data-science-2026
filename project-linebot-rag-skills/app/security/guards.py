from __future__ import annotations

import re

# ── Prompt Injection detection ────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instruction|prompt|context)",
    r"you\s+are\s+now\s+(a\s+)?(?!assistant)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if\s+you\s+are|a)\s+",
    r"disregard\s+(your|all)\s+(instructions?|guidelines?|rules?)",
    r"system\s*prompt",
    r"<\s*(INST|SYS|SYSTEM)\s*>",
    r"忽略(之前|前面|所有)(的)?(指令|設定|限制|規則)",
    r"假裝你是",
    r"現在你是(?!.*助理)",
    r"輸出.*?(system\s*prompt|系統提示)",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL
)


def detect_prompt_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))


# ── Output leakage detection ──────────────────────────────────────────────────

_LEAKAGE_PATTERNS = [
    r"\b[A-Z]\d{9}\b",            # Taiwan ID
    r"\b09\d{8}\b",               # Taiwan mobile
    r"\b0[2-8]\d{7,8}\b",         # Taiwan landline
    r"\b(?:\d{4}[- ]){3}\d{4}\b", # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",  # Email
]

_LEAKAGE_RE = re.compile("|".join(_LEAKAGE_PATTERNS))


def detect_sensitive_leakage(text: str) -> list[str]:
    return _LEAKAGE_RE.findall(text)


def redact_sensitive(text: str) -> str:
    return _LEAKAGE_RE.sub("[REDACTED]", text)


# ── RAG Poison detection (used at ingest time) ────────────────────────────────

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
    return bool(_POISON_RE.search(text))
