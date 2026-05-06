# Ch 03：替換點 3 — Feature Extractor

> 核心檔案：[`app/graph/feature_extractor.py`](../../app/graph/feature_extractor.py)

---

## 3-1  預設的 LLM-based Extractor 夠用嗎？

大多數情況下，**不需要動 Feature Extractor**——預設的 LLM-based 版本對開放領域問題就夠了。

**需要換的情況**：

| 情況 | 症狀 | 解法 |
|------|------|------|
| 詞彙封閉領域 | 法條號碼、藥品名稱、CVE 編號 | Rule-based（快 10×，零成本） |
| 效能敏感 | 每個 query 都多一次 LLM call 太貴 | Rule-based 或 Hybrid |
| 中英混合 | 使用者問中文，KB 是英文 | 在 Extractor 加翻譯邏輯 |

---

## 3-2  預設實作：什麼都不用改

[`app/graph/feature_extractor.py`](../../app/graph/feature_extractor.py) 已有完整的 LLM-based 實作，
`selfrag` 和 `reflection` variant 直接用。

輸入 → 輸出示範：

```python
# 輸入
user_input = "FastAPI 0.100 的 dependency injection 怎麼處理 async database connection？"

# LLMFeatureExtractor 輸出（ExtractedFeatures）
ExtractedFeatures(
    primary_topic = "FastAPI dependency injection",
    qualifiers    = ["async database connection", "version 0.100"],
    intent        = "how_to",
    entities      = ["FastAPI", "dependency injection", "async", "database"],
    raw_query     = "FastAPI 0.100 的 dependency injection..."
)
```

這些 entities 在 Sufficiency Check（L3 Ch03）裡用來計算 `feature_overlap`。

---

## 3-3  Rule-based：適合封閉詞彙領域

如果你的領域有固定的關鍵詞集合，rule-based 更快更便宜：

**例：勞基法 bot**

```python
# app/graph/feature_extractor.py 底部加入（或建新檔案）

LABOR_LAW_ARTICLES = {
    "第一條", "第二條", "第三條",   # ... 直到第一百條
    "第24條", "第38條", "第84-1條",  # 常用法條
}
LABOR_LAW_TOPICS = {
    "工時", "加班費", "特休", "特別休假", "資遣費",
    "育嬰留停", "職災", "勞健保", "退休金",
}

class LaborLawExtractor:
    async def extract(self, *, user_input: str, recent_history=None) -> ExtractedFeatures:
        articles = [a for a in LABOR_LAW_ARTICLES if a in user_input]
        topics   = [t for t in LABOR_LAW_TOPICS   if t in user_input]
        entities = articles + topics

        return ExtractedFeatures(
            primary_topic = topics[0] if topics else (articles[0] if articles else user_input[:50]),
            qualifiers    = articles,         # 法條號碼當限定條件
            intent        = "concept",
            entities      = entities,
            raw_query     = user_input,
        )
```

---

**例：藥物資訊 bot**

```python
DRUG_NAMES = {
    "阿斯匹靈", "普拿疼", "布洛芬", "克流感", "安眠藥",
    "Aspirin", "Ibuprofen", "Acetaminophen", "Oseltamivir",
}
SYMPTOMS = {"頭痛", "發燒", "咳嗽", "腹痛", "過敏", "失眠"}

class DrugInfoExtractor:
    async def extract(self, *, user_input: str, recent_history=None) -> ExtractedFeatures:
        drugs    = [d for d in DRUG_NAMES if d.lower() in user_input.lower()]
        symptoms = [s for s in SYMPTOMS   if s in user_input]
        entities = drugs + symptoms

        return ExtractedFeatures(
            primary_topic = drugs[0] if drugs else (symptoms[0] if symptoms else user_input[:50]),
            qualifiers    = symptoms,
            intent        = "how_to" if any(k in user_input for k in ["怎麼吃", "劑量", "用法"]) else "concept",
            entities      = entities,
            raw_query     = user_input,
        )
```

---

## 3-4  Hybrid：兩全其美

如果你的領域有固定詞彙，但也有開放型問題：

```python
class HybridExtractor:
    def __init__(self, rule_extractor, llm_extractor):
        self._rule = rule_extractor
        self._llm  = llm_extractor

    async def extract(self, *, user_input: str, **kwargs) -> ExtractedFeatures:
        result = await self._rule.extract(user_input=user_input, **kwargs)
        if not result.entities:           # rule 沒抓到任何詞彙
            return await self._llm.extract(user_input=user_input, **kwargs)
        return result
```

組裝：
```python
extractor = HybridExtractor(
    rule_extractor=DrugInfoExtractor(),
    llm_extractor=LLMFeatureExtractor(llm),   # 現有的預設實作
)
```

---

## 3-5  把你的 Extractor 接進 graph

在 [`app/dependencies.py`](../../app/dependencies.py) 找到 extractor 的初始化位置，換掉：

```python
# 原本（LLM-based，不需要改的情況）
feature_extractor = LLMFeatureExtractor(llm=llm)

# 換成你的 rule-based
from app.graph.feature_extractor import LaborLawExtractor
feature_extractor = LaborLawExtractor()

# 或 hybrid
feature_extractor = HybridExtractor(
    rule_extractor=LaborLawExtractor(),
    llm_extractor=LLMFeatureExtractor(llm=llm),
)
```

---

## 3-6  驗證：親眼看 entities 是否正確

```python
import asyncio
from app.graph.feature_extractor import LaborLawExtractor

async def main():
    ex = LaborLawExtractor()

    cases = [
        "第38條特休假怎麼算？",
        "工作滿一年可以有幾天休假？",           # 沒有法條號碼，靠 topics
        "公司可以扣我加班費嗎？",               # topics: 加班費
        "今天天氣怎麼樣？",                      # 沒有任何詞彙 → entities = []
    ]
    for q in cases:
        f = await ex.extract(user_input=q)
        print(f"Q: {q}")
        print(f"   entities: {f.entities}")
        print(f"   topic:    {f.primary_topic}\n")

asyncio.run(main())
```

預期輸出：
```
Q: 第38條特休假怎麼算？
   entities: ['第38條', '特休']
   topic:    特休

Q: 工作滿一年可以有幾天休假？
   entities: ['特休']
   topic:    特休

Q: 今天天氣怎麼樣？
   entities: []
   topic:    今天天氣怎麼樣
```

最後一個 case（entities 空）在 Hybrid 模式下會 fallback 到 LLM extractor。

---

## Eval Gate 3

```
✅ 5 個你領域的真實問題，entities 正確抓到關鍵詞
✅ 1 個和你領域無關的問題，entities = []（或 hybrid fallback 到 LLM）
```

下一章 → [Ch 04：選你的表達層](ch04-channel.md)
