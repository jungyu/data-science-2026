# 範例：把 Feature Extractor 換成醫療領域

> 對應 [spec-13](../specs/spec-13-feature-extractor.md) / [task-13](../tasks/task-13-feature-extractor.md)：示範 `FeatureExtractor` Protocol 的可換性。

## 為什麼換 rule-based

LLM-based feature extractor 在「使用者語意鬆散、表達多變」的場景表現好。但醫療助理場景有兩個特徵讓 rule-based **反而更合適**：

1. **詞彙表封閉**：症狀、藥名、檢查項目都有結構化字典
2. **延遲 / 成本敏感**：每則訊息省一次 LLM 呼叫
3. **可解釋性硬要求**：rule-based 抽取結果可逐條追溯到字典命中

## 領域 schema

繼承 base `ExtractedFeatures`，加領域欄位：

```python
# app/graph/feature_extractors/medical.py
from typing import Literal

from pydantic import Field

from app.graph.feature_extractor import ExtractedFeatures


class MedicalFeatures(ExtractedFeatures):
    symptoms: list[str] = Field(default_factory=list)
    duration_hint: str | None = None      # "三天"、"一週"...
    age_group: Literal["infant", "child", "adult", "elderly", "unknown"] = "unknown"
    severity_signal: Literal["mild", "moderate", "severe", "unknown"] = "unknown"
```

## Rule-based 實作骨架

```python
import re

from app.graph.feature_extractor import FeatureExtractor


# 領域字典（學生實際做時應改 load 自 JSON / DB）
SYMPTOMS = {
    "咳嗽", "發燒", "頭痛", "腹瀉", "盜汗", "疲倦", "胸悶",
    "呼吸困難", "心悸", "暈眩", "皮疹",
}

DURATION_PATTERNS = [
    re.compile(r"(\d+)\s*(天|日|小時|週|月)"),
    re.compile(r"持續\s*(\d+)\s*(天|日|週|月)"),
]

AGE_KEYWORDS = {
    "infant": ["嬰兒", "新生兒", "未滿一歲"],
    "child": ["小孩", "兒童", "孩子"],
    "elderly": ["長輩", "老人", "年長"],
}

SEVERITY_KEYWORDS = {
    "severe": ["很嚴重", "受不了", "暈倒", "無法呼吸"],
    "moderate": ["持續", "反覆", "影響生活"],
    "mild": ["有點", "輕微", "偶爾"],
}


class RuleBasedMedicalFeatureExtractor:
    """純 regex / keyword matching；零 LLM 依賴。"""

    async def extract(
        self, *, user_input: str, recent_history: str | None = None
    ) -> MedicalFeatures:
        text = user_input
        symptoms = sorted({s for s in SYMPTOMS if s in text})

        duration: str | None = None
        for p in DURATION_PATTERNS:
            m = p.search(text)
            if m:
                duration = m.group(0)
                break

        age = "unknown"
        for tag, kws in AGE_KEYWORDS.items():
            if any(k in text for k in kws):
                age = tag
                break

        severity = "unknown"
        for tag, kws in SEVERITY_KEYWORDS.items():
            if any(k in text for k in kws):
                severity = tag
                break

        return MedicalFeatures(
            primary_topic=symptoms[0] if symptoms else user_input[:50],
            qualifiers=[duration] if duration else [],
            intent="debug" if symptoms else "other",
            entities=symptoms,
            symptoms=symptoms,
            duration_hint=duration,
            age_group=age,
            severity_signal=severity,
            raw_query=user_input,
        )
```

## 接進 graph

修改 `app/dependencies.py::get_feature_extractor`：

```python
@lru_cache(maxsize=1)
def get_feature_extractor() -> FeatureExtractor:
    settings = get_settings()
    if settings.domain == "medical":
        from app.graph.feature_extractors.medical import RuleBasedMedicalFeatureExtractor
        return RuleBasedMedicalFeatureExtractor()
    # 預設：LLM-based
    llm = build_llm(settings, "router") if has_llm_configured(settings) else None
    return LLMFeatureExtractor(llm=llm)
```

`Settings` 加 `domain: str = "default"`，學生用 env var 切換。

## 預期行為差異

| 輸入 | LLM-based 抽取 | RuleBased 抽取 |
|------|---------------|----------------|
| 「我兒子咳嗽三天了，要不要看醫生？」 | `primary_topic="兒童咳嗽 3 天"`, `intent="decide"` | `symptoms=["咳嗽"]`, `duration_hint="三天"`, `age_group="child"`, `intent="debug"` |
| 「最近常常頭痛、會暈眩，影響生活」 | `primary_topic="頭痛暈眩"`, `intent="debug"` | `symptoms=["頭痛","暈眩"]`, `severity_signal="moderate"` |
| 「肚子怪怪的」（無關鍵詞）| `primary_topic="肚子怪怪的"`, `intent="other"` | `symptoms=[]`, `primary_topic="肚子怪怪的"`（fallback）|

Rule-based 對「**詞彙表內**」的輸入更精準（多了結構化欄位）；對「**詞彙表外**」的輸入則退化為 raw query fallback——這是 trade-off，不是缺陷。

## 驗證 transferability

學生轉到醫療領域後，依 [doc-01 §Tier 1](../guides/doc-01-transferability-guide.md#tier-1換領域留-line--supabase) 的 checklist：

- [ ] T1.3 Feature Extractor 已客製 → 用本範例為起點
- [ ] T1.4 golden.yaml 至少 10 個醫療領域 case
- [ ] T1.5 跑 `scripts/eval.py` 對 LLM-based vs RuleBased 兩個 extractor 比對 metric

預期觀察：

| Metric | LLM-based | RuleBased | 推論 |
|---|---|---|---|
| `chunk_recall@k` | 中 | 高（詞彙表內 case） | rule-based 在 high-precision 環境贏 |
| `latency_ms` | 高（含 LLM 呼叫）| 低（純 regex） | rule-based 顯著快 |
| `forbidden_phrase_rate` | 視 prompt 設計 | 0（不過 LLM） | rule-based 確定性高 |

學生應在自己領域決定取捨，不一定要二選一——可以做 hybrid：rule 優先，無命中時 fallback 到 LLM。

## 進階：Hybrid Extractor

```python
class HybridMedicalExtractor:
    def __init__(self, rule, llm_fallback):
        self._rule = rule
        self._llm = llm_fallback

    async def extract(self, **kwargs):
        result = await self._rule.extract(**kwargs)
        if not result.symptoms and result.intent == "other":
            # rule 沒抓到任何東西，交給 LLM
            return await self._llm.extract(**kwargs)
        return result
```

這個模式適用任何「可分箱輸入」的領域：法規條號、SKU、地名、人名、時間點。
