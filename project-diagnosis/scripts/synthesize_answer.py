#!/usr/bin/env python3
"""
Evidence-grounded answer synthesis (Whitepaper §9 Stage 2).

Takes the JSON Answer Contract produced by answer_query.py (A~G sections
plus rule flags) and calls Claude to generate a natural-language Markdown
answer that stays strictly within the provided evidence.

Used as a module from answer_query.py, or standalone for testing:

    echo '{"A_symptom_summary": {...}, ...}' | \
      python scripts/synthesize_answer.py

Environment variables:
  ANTHROPIC_API_KEY         - required (falls back to passthrough text when absent)
  ANTHROPIC_MODEL           - optional (default: claude-sonnet-4-5)
  SYNTHESIS_MAX_TOKENS      - optional (default: 1500)
  SYNTHESIS_TEMPERATURE     - optional (default: 0.2)

Design notes:
  - Temperature intentionally low (0.2) to suppress stylistic embellishment
  - Prompt template externalised at prompts/synthesize_answer.txt
  - Never raises on API failure: returns `None` so answer_query.py can fall
    back to JSON-only output
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger("synthesize_answer")

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "synthesize_answer.txt"


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

@dataclass(frozen=True)
class SynthesisSettings:
    api_key: str
    model: str
    max_tokens: int
    temperature: float


def load_synthesis_settings() -> SynthesisSettings | None:
    api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        return None

    return SynthesisSettings(
        api_key=api_key,
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5").strip(),
        max_tokens=int(os.getenv("SYNTHESIS_MAX_TOKENS", "1500")),
        temperature=float(os.getenv("SYNTHESIS_TEMPERATURE", "0.2")),
    )


# ---------------------------------------------------------
# Prompt
# ---------------------------------------------------------

def build_prompt(answer_contract: dict[str, Any]) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    payload = json.dumps(answer_contract, ensure_ascii=False, indent=2)
    return template.replace("{payload}", payload)


# ---------------------------------------------------------
# LLM call
# ---------------------------------------------------------

def synthesize(
    answer_contract: dict[str, Any],
    settings: SynthesisSettings | None = None,
) -> str | None:
    """Generate a natural-language answer from the assembled evidence.

    Returns None when the API key is absent or the call fails, so the caller
    can decide whether to degrade to JSON-only output.
    """
    settings = settings or load_synthesis_settings()
    if settings is None:
        logger.info("ANTHROPIC_API_KEY not set; skipping synthesis.")
        return None

    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("anthropic package not installed; skipping synthesis.")
        return None

    prompt = build_prompt(answer_contract)

    try:
        client = Anthropic(api_key=settings.api_key)
        response = client.messages.create(
            model=settings.model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            system=(
                "你是一位嚴謹的中醫知識檢索助手。嚴格依據提供的證據作答，"
                "不得補充輸入資料以外的內容。"
            ),
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        logger.warning("Claude synthesis failed: %s", exc)
        return None

    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    text = "\n".join(parts).strip()
    return text or None


# ---------------------------------------------------------
# CLI entrypoint (useful for debugging the prompt)
# ---------------------------------------------------------

def _main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    raw = sys.stdin.read().strip()
    if not raw:
        print("Usage: cat answer-contract.json | synthesize_answer.py", file=sys.stderr)
        return 2

    try:
        contract = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON on stdin: {exc}", file=sys.stderr)
        return 2

    result = synthesize(contract)
    if result is None:
        print("Synthesis skipped or failed; see logs.", file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
