# task-01：實作 Response Mode 差異化

> 規格詳見 [spec-01](../specs/spec-01-response-mode.md)
>
> **✅ 已完成（commit `44b630d`）** — 實作記錄與驗收測試見 spec-01 頂部「實作狀態」段。

---

請修改 `app/generator/prompts.py`，讓 `render_synthesis_prompt()` 依 `response_mode` 輸出不同的格式指令。

## 現行程式碼位置

`app/generator/prompts.py`：`render_synthesis_prompt()` 函式。

## 需要修改的內容

**新增** `_mode_instruction(response_mode: str) -> str`：

| response_mode | 回傳的指令字串（插入 prompt） |
|---------------|--------------------------|
| `brief` | 「回覆請控制在 3 句以內，不使用條列或標題。」 |
| `structured` | 「回覆請使用條列格式（1. / 2. 或 - ），複雜問題可加 ## 小節標題。」 |
| `step_by_step` | 「回覆請以嚴格序號步驟呈現（1. 2. 3.），每步驟一行，最後加上『完成後確認：』說明驗證方式。」 |
| `decision_support` | 「回覆請先列出選項（選項 A / 選項 B），說明各自優缺點，再明確給出建議選哪個及原因，最後列出主要風險。」 |
| `debugging` | 「回覆請先列出可能原因（不超過 3 個），再給出各原因的驗證方式，最後給出修法。」 |
| `reflection` | 「回覆請不要給清單或步驟，先以問句回應，引導使用者自我思考，最後才給一個觀點或小建議。」 |

**修改** `render_synthesis_prompt()`：在 system prompt 區塊插入 `_mode_instruction(response_mode)` 的結果。

## 請輸出

1. 修改後的完整 `app/generator/prompts.py`
2. `tests/test_responder.py` 中新增 6 個測試，各覆蓋一種 mode，確認 prompt 字串包含對應的格式指令關鍵字

## 驗收指令

```bash
pytest tests/test_responder.py -v
```
