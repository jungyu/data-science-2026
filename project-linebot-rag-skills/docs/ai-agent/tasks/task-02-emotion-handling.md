# task-02：實作 Emotion 應對策略

> 規格詳見 [spec-02](../specs/spec-02-emotion-handling.md)
>
> **✅ 已完成（commit `44b630d`）** — 實作記錄與驗收測試見 spec-02 頂部「實作狀態」段。
---

請修改 `app/generator/prompts.py`，讓 synthesis prompt 依 `emotion_state` 加入具體的行為指令。

## 需要修改的內容

**新增** `_emotion_instruction(emotion_state: str) -> str`：

| emotion_state | 回傳的指令字串 |
|--------------|--------------|
| `neutral` | `""` （空字串，無調整） |
| `curious` | 「使用者充滿好奇，語氣可以輕鬆一點，可在結尾給一個延伸閱讀方向。」 |
| `urgent` | 「使用者很趕，直接給最重要的一個步驟或答案，省略背景說明。」 |
| `confused` | 「使用者感到困惑，從最基本概念開始說明，避免假設先備知識，一次只解釋一件事。」 |
| `frustrated` | 「使用者感到挫折，先用一句話承認這個問題確實麻煩，再只給一個最小可行的下一步，不要給選項清單。」 |
| `anxious` | 「使用者感到焦慮，先用一句話讓他知道這是正常的，只給一個具體的小行動，整個回覆不超過 3 句，結尾加一句鼓勵。」 |
| `reflective` | 「使用者正在思考，不要急著給答案，先以問句引導，最後才給一個觀點。」 |

**優先順序規則**：`anxious` 和 `frustrated` 的長度限制（≤ 3 句）覆蓋 `response_mode` 的格式要求，但不覆蓋格式本身（仍可使用步驟，但只列第一步）。在 prompt 中把 emotion 指令放在 mode 指令之後，讓 LLM 以 emotion 優先。

**修改** `render_synthesis_prompt()`：在 prompt 中加入 `_emotion_instruction(emotion_state)` 的結果（緊接在 mode 指令之後）。

## 請輸出

1. 修改後的完整 `app/generator/prompts.py`（包含 task-01 的修改，不要覆蓋）
2. `tests/test_responder.py` 中新增測試：
   - `anxious` → prompt 包含「不超過 3 句」相關字
   - `frustrated` → prompt 包含「最小可行」相關字
   - `neutral` → prompt 不包含額外情緒指令

## 驗收指令

```bash
pytest tests/test_responder.py -v
```
