# 04 · LINE 整合設計（Planning Prompt）

> **使用時機**：修改 webhook 處理邏輯、新增訊息類型支援、調整 push 格式時使用。

---

你是資深 Python 工程師。`app/line/` 是這個 LINE Bot 的 webhook 與 push 模組，已完整實作並可正常運作。

## 現行實作（已完成）

**架構：**

```
app/line/
├── webhook.py   # POST /api/line/webhook + process_text_event()
├── client.py    # LineClient（signature 驗證 + push_text）
└── schemas.py   # LineWebhookPayload, LineEvent, LineMessage, LineSource
```

**Webhook 處理流程：**

```python
@router.post("/webhook")
async def line_webhook(request, background_tasks, services):
    body = await request.body()
    signature = request.headers.get("x-line-signature")
    if not services.line_client.validate_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid LINE signature")

    payload = LineWebhookPayload.model_validate_json(body)
    for event in payload.events:
        if event.is_text_message and event.source.user_id:
            background_tasks.add_task(process_text_event, event, services)
    return {"ok": True}   # 立即回 200，不等待背景任務
```

**process_text_event() 的關鍵設計：**

1. 每個步驟獨立 try/except，單一步驟失敗不中斷整個流程
2. `generate_response` 的 except block **必須** 有 `logger.exception()`，否則例外靜默吞掉，只看到 fallback 訊息，無法除錯
3. Push API 呼叫後的 save_message 在 `finally` 確保一定執行
4. LINE 訊息長度上限 4500 字元，`split_for_line()` 負責切割

**已知限制：**

- 目前只處理文字訊息（`message.type == "text"`），圖片、貼圖、語音均忽略
- 每則訊息獨立路由，不維護 session 狀態（short recent history 由 line_messages 資料表提供）
- Background task 沒有 retry 機制，失敗直接丟棄

## 請評估以下 LINE 整合變更：

{在此填入你要修改的目標，例如：「新增圖片訊息支援（OCR）」或「改善錯誤訊息的呈現方式」}

請輸出：
1. 需要修改的檔案與具體改動
2. 對 webhook 回應時間的影響（LINE 有 5 秒限制）
3. 錯誤處理策略（哪些錯誤要讓用戶看到，哪些靜默處理）
4. 日誌記錄建議（至少需要 logger.exception 在所有 generate_response 的 except block）
5. 測試案例（至少覆蓋：valid signature、invalid signature、非文字訊息、generate_response 丟出例外時的 fallback）

**必要規範：**
- 所有 except block 加 `logger.exception("描述性訊息")`，不允許靜默吞掉例外
- Webhook handler 本身必須在 5 秒內回傳，繁重處理一律放 background task
