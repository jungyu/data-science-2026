"""Layer D: LLM-as-judge（Spec-009）— 評估 grounded generation 品質。

策略：用獨立 Claude 呼叫，以「審查員」角色對輸出做四項結構化打分：

    1. groundedness    — 結論是否都有依據
    2. citation_fidelity — 引用文字是否與提供的 atom 原文一致
    3. format_completeness — 六個區段是否齊全
    4. uncertainty_honesty — 不確定處是否誠實標示

輸出 JSON；caller 根據分數做彙總與通過閾值判定。

注意：judge 與 generation 使用同一 provider 可能有偏差風險；
本版先求可跑，日後可替換為另一廠商模型或人工審查。
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from anthropic import Anthropic

from destiny.config import Settings
from destiny.retrieval import RetrievalHit

_SYSTEM = """你是嚴格的命理 RAG 輸出審查員。
你會收到：(a) 命理助理產出的解盤文字；(b) 該次可用的文獻 atom 清單（含 atom_code 與原文）。

你的任務是依以下四項維度打分 (0-10)，並輸出 JSON。

1. groundedness — 解盤的每個主要結論是否都能對應到提供的 atom；自行創造結論扣分。
2. citation_fidelity — 引用古文是否逐字來自提供的 atom；改寫或杜撰扣分。
3. format_completeness — 是否包含以下六個區段：
   命盤結構摘要 / 核心判斷 / 依據文獻 / 規則說明 / 綜合解釋 / 不確定處
4. uncertainty_honesty — 「不確定處」區段是否誠實標示限制；若空泛或寫「無」扣分。

輸出格式（嚴格 JSON，無 markdown fence、無前後文）：
{
  "groundedness": 0-10,
  "citation_fidelity": 0-10,
  "format_completeness": 0-10,
  "uncertainty_honesty": 0-10,
  "issues": ["具體問題敘述，最多 5 條"]
}
"""


@dataclass
class JudgeScore:
    groundedness: int
    citation_fidelity: int
    format_completeness: int
    uncertainty_honesty: int
    issues: list[str]

    @property
    def mean(self) -> float:
        return (
            self.groundedness
            + self.citation_fidelity
            + self.format_completeness
            + self.uncertainty_honesty
        ) / 4.0

    @property
    def passed(self) -> bool:
        """Phase 1 通過閾值：所有項 ≥6 且 groundedness ≥7。"""
        return (
            self.groundedness >= 7
            and self.citation_fidelity >= 6
            and self.format_completeness >= 6
            and self.uncertainty_honesty >= 6
        )


def _format_atoms(hits: list[RetrievalHit]) -> str:
    lines = []
    for h in hits:
        lines.append(f"[{h.atom_code}] 《{h.source_book}》: {h.original_text}")
    return "\n".join(lines) or "(無)"


def judge_output(
    settings: Settings,
    output_text: str,
    hits: list[RetrievalHit],
) -> JudgeScore:
    client = Anthropic()
    user_content = (
        "【助理輸出】\n" + output_text + "\n\n"
        "【可用文獻 atom】\n" + _format_atoms(hits) + "\n\n"
        "請依規定輸出 JSON。"
    )
    resp = client.messages.create(
        model=settings.chat_model,
        max_tokens=800,
        system=[{"type": "text", "text": _SYSTEM,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]

    data = json.loads(text)
    return JudgeScore(
        groundedness=int(data.get("groundedness", 0)),
        citation_fidelity=int(data.get("citation_fidelity", 0)),
        format_completeness=int(data.get("format_completeness", 0)),
        uncertainty_honesty=int(data.get("uncertainty_honesty", 0)),
        issues=list(data.get("issues", [])),
    )
