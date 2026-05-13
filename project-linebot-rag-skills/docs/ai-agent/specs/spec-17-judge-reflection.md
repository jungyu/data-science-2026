# Spec-17：LLM-as-Judge + Reflection 迴圈（P4）

> **✅ 已實作；修補 SKIP_JUDGE_SKILLS 對齊 SkillId（commit `2387555`）**
>
> - `SKIP_JUDGE_SKILLS` 從錯誤的 `"small_talk"` 改回 `"general_chat"`（與 `app/router/schemas.py::SkillId` 對齊）
> - 過去寫錯導致閒聊在 production 一律被 judge 評分、必拿低分、觸發品質警告
> - 測試 fixture 同步調整（`test_judge_skipped_for_general_chat_skill`、`_StubRouter` 預設改 `tech_architect`）
> - 取代 [spec-11](./spec-11-reflection.md) 的單一 reflection_score 設計

## 背景

P3 完成後 Generator 是兩階段（Answer Contract + Narrative），輸出結構穩定。本 phase 加入**自我審查**：另一個 LLM 呼叫（最好換廠商或換模型）對 narrative 做**結構化多軸評分**，分數不足時把評語回灌到 narrative renderer 重新生成。

借鑑：project-destiny `src/destiny/judge.py`（Layer D, ADR-008）。本 spec 直接採用其 4 軸評分結構，並加上 LangGraph 迴圈控制。

> 此 spec **取代** [spec-11 Reflection](./spec-11-reflection.md) 的單一分數設計。Self-RAG 的 query 改寫重試需求在 P2（multi-seed）+ P3（sufficiency）已被覆蓋，因此 [spec-10](./spec-10-selfrag.md) 不再需要對應實作。

## 設計

### Graph 位置

```
render_narrative → judge
                    ├─ pass               → push
                    ├─ fail & retry < N   → render_narrative（帶 judge feedback）
                    └─ fail & retry >= N  → push（強制送出，標註「品質警告」）
```

### Judge 4 軸（沿用 destiny）

| 軸 | 0–10 評分 | 說明 |
|---|---|---|
| `groundedness` | 結論是否都能對應到 Answer Contract 的 citations |
| `citation_fidelity` | 引用文字是否與 chunk snippet 一致（無杜撰）|
| `format_completeness` | response_mode 規定的段落 / 結構是否齊全 |
| `uncertainty_honesty` | caveats 是否誠實呈現，不誇大確定性 |

通過門檻：每軸 ≥ 6 **且** 平均 ≥ 7（皆可由 config 調整）。

### Judge Prompt 結構（嚴格 JSON 輸出）

```
你是嚴格的 RAG 輸出審查員。
你會收到：(a) 助理產出的回覆 markdown；(b) 該次的 Answer Contract（含 citations）。

依以下 4 軸打分（0~10），輸出 JSON：
- groundedness: 結論是否都有 contract 中的依據
- citation_fidelity: 引用文字是否與 contract.citations[].snippet 逐字相符
- format_completeness: 是否符合 response_mode={mode} 的格式要求
- uncertainty_honesty: caveats 是否完整呈現

格式（嚴格 JSON，無前後文）：
{
  "groundedness": 0,
  "citation_fidelity": 0,
  "format_completeness": 0,
  "uncertainty_honesty": 0,
  "issues": ["具體問題敘述，最多 5 條"]
}
```

### Reflection 重生成

Judge 不通過時，把 `issues` 串成 feedback 加進 narrative renderer 的 prompt：

```
（前一次的問題）
{issues}

請改善以上問題後重新輸出 markdown。其餘規則不變。
```

`render_narrative_node` 偵測 state 中有 `judge_feedback` 時，自動把這段附加到 prompt 末尾。

### 迴圈上限

- `MAX_REFLECTION_RETRIES`（預設 1，硬上限 2）
- 達上限仍 fail → 強制 push，但在訊息開頭加「⚠️ 品質警告：本次回覆未通過自審」（讓使用者知道）
- log 一定要記 retry 次數與每次的 judge 分數

### 不啟用 judge 的情境

- `router_result.skill_name in {"small_talk", "emotional_calibration"}` → 跳過 judge（情緒回應與閒聊不適合 grounded 評分）
- `sufficiency == "insufficient"` → 已走 clarify 分支，不會到 judge

### 模型建議

- Judge 模型 **建議與 Generator 不同廠商**（避免同模型自我合理化）
- 若只有單一廠商 API key，至少用更小但更嚴格的模型（temperature 0）
- 介面允許 judge 注入獨立的 `LLM` 實例

### State 新增欄位

```python
class RAGState(TypedDict, total=False):
    ...
    judge_score: JudgeScore
    judge_feedback: list[str]      # issues
    reflection_retry: int          # 0 / 1 / 2
    judge_warning_prefix: bool     # 是否在輸出前加品質警告
```

## 介面契約

**新增**：`app/judge/__init__.py`、`app/judge/scorer.py`

```python
class JudgeScore(BaseModel):
    groundedness: int
    citation_fidelity: int
    format_completeness: int
    uncertainty_honesty: int
    issues: list[str]

    @property
    def mean(self) -> float: ...

    def passes(self, *, min_axis: int = 6, min_mean: float = 7.0) -> bool: ...

class GroundednessJudge:
    def __init__(self, llm: JudgeLLM, model: str) -> None: ...
    async def judge(
        self, *, narrative: str, contract: AnswerContract, response_mode: str
    ) -> JudgeScore: ...
```

**新增 node**：`judge_node`，並設定 `add_conditional_edges` 處理三向分流（pass / retry / force_push）。

**修改**：
- `app/graph/state.py` 加入 judge 相關欄位
- `app/generator/narrative.py` 的 `render()` 接受可選 `feedback: list[str]` 參數
- `app/dependencies.py` 注入 `GroundednessJudge`

**Config 新增**：
- `JUDGE_ENABLED`（bool，預設 true）
- `JUDGE_MODEL`、`JUDGE_PROVIDER`（可獨立於主 generator）
- `MAX_REFLECTION_RETRIES`（int, 預設 1）
- `JUDGE_MIN_AXIS`、`JUDGE_MIN_MEAN`

## 驗收標準

- 刻意用品質差的 prompt 觸發低分 → log 顯示 `judge fail → reflect → render again`，最終分數提升或達 retry 上限
- 正常品質回覆 → log 顯示 `judge pass`，不重生成
- judge LLM 失敗 → fallback 視為 pass（不阻塞輸出），log warning
- retry 上限到達 → 訊息開頭出現「⚠️ 品質警告」前綴
- `small_talk` skill 不觸發 judge
- judge 與 generator 用不同 model 時，無 import / 設定衝突

## 教學配套

- 在 `docs/ai-agent/examples/` 加一份「judge 評分案例集」：3 個 pass、3 個 fail、3 個 retry 後 pass，並附上每次的 prompt + 評分 JSON
- README 加一段「為什麼要 judge」與「為什麼軸要這 4 個」
