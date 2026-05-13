# Spec-01：Response Mode 差異化

> **✅ 已實作（commit `44b630d`）**
>
> - `app/generator/prompts.py::_mode_instruction()` — 6 種 mode 的明確格式指令
> - `SYNTHESIS_PROMPT` 重寫成分節式，把 mode 指令插入 prompt
> - `app/generator/narrative.py` 同步加入 mode 指令，讓 selfrag/reflection 變體也差異化
> - 驗收測試：`tests/test_prompt_differentiation.py`（13 cases）

## 背景

Router 已輸出 6 種 `response_mode`，但 Generator 的 `render_synthesis_prompt()` 只是把 mode 名稱貼入 prompt 字串，沒有任何對應的生成策略。使用者無論問什麼，回覆格式實際上沒有差異。

## 目標

讓每種 `response_mode` 對應明確的回覆格式規則，透過改寫 synthesis prompt 模板實現，**不需要引入新的外部依賴**。

## 各 Mode 的格式規則

| Mode | 規則 |
|------|------|
| `brief` | 3 句以內，不用條列，不加標題 |
| `structured` | 必須有條列（`1.` / `-`），複雜問題加 `##` 小節 |
| `step_by_step` | 嚴格按序號步驟，每步驟一行，最後加「完成後確認：xxx」 |
| `decision_support` | 先列「選項 A / B」，再給「建議選 X，因為 Y」，最後加風險提示 |
| `debugging` | 先給「可能原因（1/2/3）」，再給「驗證方式」，最後給「修法」 |
| `reflection` | 不列選項，不給步驟，以問句或感受回應，最後才給一個小建議 |

## 介面契約

**修改範圍**：`app/generator/prompts.py` 的 `render_synthesis_prompt()`

```python
def render_synthesis_prompt(
    skill_name: str,
    skill_system_prompt: str,
    user_input: str,
    recent_history: str,
    emotion_state: str,
    response_mode: str,      # 已有，但需真正依此調整 prompt
    rag_context: str,
) -> str
```

**新增**：一個 `_mode_instruction(response_mode: str) -> str` 私有函式，回傳對應的格式指令字串，插入 prompt 的適當位置。

## 不做什麼

- 不改變 Router 的邏輯
- 不改變 Generator LLM 的呼叫方式
- 不新增資料表或設定

## 驗收標準

| 測試輸入 | 預期 mode | 預期回覆特徵 |
|---------|---------|------------|
| 「如何設定 pgvector？」 | `structured` | 有條列項目 |
| 「幫我一步一步設定 ngrok」 | `step_by_step` | 有 `1.` `2.` `3.` 序號 |
| 「我有點焦慮，不知道該怎麼辦」 | `reflection` | 無條列，有問句，回覆短 |
| 「TypeScript 還是 Python，我該選哪個？」 | `decision_support` | 有選項比較，有明確建議 |
