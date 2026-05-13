# Spec-02：Emotion 應對策略

> **✅ 已實作（commit `44b630d`）**
>
> - `app/generator/prompts.py::_emotion_instruction()` — 7 種 emotion 的行為指令
> - `anxious` / `frustrated`：≤3 句、只給 1 個下一步、加鼓勵句的限制已落地
> - `render_narrative_node` 從 `router_result.emotion_state` 抽值餵入下游
> - 驗收測試：`tests/test_prompt_differentiation.py` 涵蓋「emotion 覆寫 mode 的長度與選項數量」

## 背景

Router 已能偵測 7 種情緒狀態，但 Generator 只把 `emotion_state` 作為字串注入 prompt，沒有根據情緒調整回覆策略（長度、語氣、選項數量）。`anxious` / `frustrated` 的使用者仍然可能收到冗長的技術列表。

## 目標

在 synthesis prompt 中加入依情緒狀態的具體行為指令，不需要改動 Router 或 schema。

## 各情緒的應對策略

| EmotionState | 應對策略 |
|-------------|---------|
| `neutral` | 無特殊調整，依 response_mode 為準 |
| `curious` | 鼓勵探索，可給延伸閱讀方向，語氣輕鬆 |
| `urgent` | 直接給最重要的一個步驟，省略背景說明 |
| `confused` | 從最基本概念開始，避免假設先備知識，一次只解釋一件事 |
| `frustrated` | 先承認問題確實麻煩，再給最小可行的下一步，不給選項清單 |
| `anxious` | 先降低認知負荷（「這是正常的」），只給一個具體小行動，結尾加鼓勵句 |
| `reflective` | 不急著給解答，先以問句引導思考，最後才給一個觀點 |

## 介面契約

**修改範圍**：`app/generator/prompts.py`

新增 `_emotion_instruction(emotion_state: str) -> str`，回傳對應的行為指令字串。

`anxious` / `frustrated` 的指令明確要求：
- 回覆不超過 3 句
- 只給 **1 個**下一步行動，不給選項
- 語氣用「你」，避免冷硬的技術術語

## 與 Response Mode 的優先順序

**Emotion 覆蓋 Mode 的長度與選項數量，但不覆蓋格式結構**。

例：`step_by_step` + `anxious` → 仍用步驟格式，但只列第一步，其他步驟省略，並加上鼓勵句。

## 不做什麼

- 不建立新的資料表
- 不引入情緒強度評分（留給 Phase 4）
- 不改變 Router 偵測邏輯

## 驗收標準

| 測試輸入 | 預期 emotion | 回覆特徵 |
|---------|------------|---------|
| 「我很焦慮，不知道要從哪裡開始學 RAG」 | `anxious` | ≤ 3 句，只給 1 個行動，有鼓勵句 |
| 「這個 bug 我找了三小時都找不到，煩死了」 | `frustrated` | 先承認麻煩，1 個下一步，無選項清單 |
| 「快速告訴我怎麼重啟 ngrok」 | `urgent` | 直接給指令，無背景說明 |
| 「我在思考 RAG 和 fine-tuning 的本質差異」 | `reflective` | 有問句，無急著給答案，1 個觀點 |
