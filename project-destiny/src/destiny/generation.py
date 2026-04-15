"""Generation Orchestrator (Spec-007) — grounded, structured output via Claude。

設計重點：
1. System block 採 prompt caching：跨請求固定，省下重複 tokens。
2. Context 分三段：命盤、規則判定、檢索證據——明確區分「判定」「引用」「解釋」。
3. 不走 function calling，直接要求結構化 markdown 區段；由呼叫端用 regex 或手動解析。
4. LLM 只得引用傳入的 atom_code；自創引用視為幻覺。
"""

from __future__ import annotations

from dataclasses import dataclass

from anthropic import Anthropic

from destiny.config import Settings
from destiny.models import BaziChart, RuleOutput
from destiny.retrieval import RetrievalHit

_SYSTEM_PROMPT = """你是嚴格依據命理文獻的八字分析助理。

絕對規則：
1. 只能依據使用者訊息中【相關文獻】列出的 atom_code 進行引用；不得引用未列出的古文。
2. 區分「規則判定」「文獻引述」「解釋說明」三類內容，不可混用。
3. 證據不足時，必須在「不確定處」明確指出，不可自行補完。
4. 引用文獻時必須使用提供的原文原字，不得改寫古文。
5. 《子平真詮》為最高權威骨架，引用時應優先置前。

輸出格式（嚴格遵守六個區段，皆不可省略，不可加入其他區段）：

## 命盤結構摘要
[四柱、日主、月令、季節的客觀摘要]

## 核心判斷
[根據規則判定，說明格局、強弱、調候方向]

## 依據文獻
[逐條列出引用：引用格式為「《書名》篇章：原文」，並標註 atom_code]

## 規則說明
[說明規則引擎判定結果及其成立條件]

## 綜合解釋
[整合規則與文獻，給出可讀的完整解釋]

## 不確定處
[明示哪些判斷信心較低、證據不足或需要更多資訊，此區段永不可為空]
"""


@dataclass
class GenerationResult:
    output_text: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int


def _format_chart(chart: BaziChart) -> str:
    p = chart.four_pillars
    return (
        f"- 四柱：年 {p['year'].stem}{p['year'].branch} / "
        f"月 {p['month'].stem}{p['month'].branch} / "
        f"日 {p['day'].stem}{p['day'].branch} / "
        f"時 {p['hour'].stem}{p['hour'].branch}\n"
        f"- 日主：{chart.day_master}\n"
        f"- 月令：{chart.month_commander}\n"
        f"- 季節：{chart.season}\n"
        f"- 真太陽時：{'已套用' if chart.true_solar_time_applied else '未套用'}"
    )


def _format_rules(rules: RuleOutput) -> str:
    sa = rules.strength_assessment
    patterns = "、".join(
        f"{p.pattern}(信心={p.confidence})" for p in rules.candidate_patterns
    ) or "無"
    return (
        f"- 身強弱：{sa.day_master_strength}（信心={sa.confidence}）\n"
        f"- 候選格局：{patterns}\n"
        f"- 調候需求：{'、'.join(rules.seasonal_adjustment_needed) or '無明顯需求'}\n"
        f"- 風險旗標：{'、'.join(rules.risk_flags) or '無'}"
    )


def _format_hits(hits: list[RetrievalHit]) -> str:
    if not hits:
        return "（無召回結果）"
    lines: list[str] = []
    for i, h in enumerate(hits, 1):
        title = f"「{h.title}」" if h.title else ""
        interp = f"\n  現代語意：{h.modern_interpretation}" if h.modern_interpretation else ""
        lines.append(
            f"{i}. [atom_code={h.atom_code}] 《{h.source_book}》{title}（final={h.final_score:.3f}）\n"
            f"  原文：{h.original_text}{interp}"
        )
    return "\n".join(lines)


def generate_analysis(
    settings: Settings,
    chart: BaziChart,
    rules: RuleOutput,
    hits: list[RetrievalHit],
    anthropic_api_key: str | None = None,
) -> GenerationResult:
    """呼叫 Claude 產生 grounded 解盤輸出。"""
    client = Anthropic(api_key=anthropic_api_key)  # 省略則讀 ANTHROPIC_API_KEY env

    user_content = (
        "【命盤資料】\n" + _format_chart(chart) + "\n\n"
        "【規則判定結果】\n" + _format_rules(rules) + "\n\n"
        "【相關文獻】\n" + _format_hits(hits) + "\n\n"
        "請依照 system 規定的六個區段輸出解盤分析。"
    )

    resp = client.messages.create(
        model=settings.chat_model,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # 5 分鐘 TTL 快取
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    text_parts = [block.text for block in resp.content if block.type == "text"]
    usage = resp.usage

    return GenerationResult(
        output_text="".join(text_parts),
        model=resp.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
    )
