# task-line-webhook · LINE Webhook 實作

> **使用時機**：從零實作 webhook 模組，或新增訊息類型支援時使用。

---

請在 `app/line/` 目錄下實作 LINE Messaging API 的 webhook 接收與 push 回覆模組。

## 目標目錄結構

```
app/line/
├── webhook.py   # FastAPI router + process_text_event()
├── client.py    # LineClient（signature 驗證 + push_text）
└── schemas.py   # LineWebhookPayload, LineEvent, LineMessage, LineSource
```

## schemas.py 規格

```python
class LineSource(BaseModel):
    type: str
    userId: str | None = None

    @property
    def user_id(self) -> str | None:
        return self.userId

class LineMessage(BaseModel):
    id: str | None = None
    type: str
    text: str | None = None

class LineEvent(BaseModel):
    type: str
    replyToken: str | None = None
    source: LineSource
    timestamp: int | None = None
    message: LineMessage | None = None

    @property
    def is_text_message(self) -> bool:
        return self.type == "message" and self.message is not None and self.message.type == "text"

class LineWebhookPayload(BaseModel):
    destination: str | None = None
    events: list[LineEvent] = Field(default_factory=list)
```

## webhook.py 規格

**Endpoint：**

```python
POST /api/line/webhook
→ 驗證 x-line-signature（HMAC-SHA256，用 LINE_CHANNEL_SECRET）
→ 失敗：raise HTTPException(status_code=400)
→ 成功：for each text event → background_tasks.add_task(process_text_event)
→ 立即回傳 {"ok": True}（不等背景任務）
```

**process_text_event() 流程：**

```
1. save inbound message（失敗不中斷）
2. build_recent_history（失敗不中斷）
3. router.route_message()
4. skill_registry.get(target_skill)
5. if is_rag_required: retriever.retrieve()
6. responder.generate_response()  ← 此步驟的 except 必須加 logger.exception()
7. line_client.push_text()
8. finally: save outbound message
```

**日誌規範（必要）：**

```python
import logging
logger = logging.getLogger(__name__)

# generate_response 的 except block
except Exception:
    logger.exception("generate_response failed")   # 印出完整 traceback
    responses = ["系統暫時無法完成此請求，請稍後再試。"]
```

若沒有 `logger.exception()`，例外會被靜默吞掉，只能看到 fallback 訊息，完全無法除錯。

## client.py 規格

```python
class LineClient:
    def validate_signature(self, body: bytes, signature: str | None) -> bool:
        # HMAC-SHA256(body, LINE_CHANNEL_SECRET)
        # signature 是 base64 編碼的結果
        # 比對方式用 hmac.compare_digest()

    async def push_text(self, user_id: str, messages: list[str]) -> None:
        # POST https://api.line.me/v2/bot/message/push
        # Authorization: Bearer LINE_CHANNEL_ACCESS_TOKEN
        # 每則訊息獨立發送（或批次），type=text
```

## app/main.py 規格

```python
from fastapi import FastAPI
from app.line.webhook import router as line_router

def create_app() -> FastAPI:
    app = FastAPI(title="project-linebot-rag-skills")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(line_router)
    return app

app = create_app()
```

## 請輸出

1. `schemas.py` 完整程式碼
2. `client.py` 完整程式碼（含 `validate_signature` 與 `push_text`）
3. `webhook.py` 完整程式碼（含 `logger.exception` 在 generate_response except block）
4. `app/main.py` 完整程式碼
5. `tests/test_line_webhook.py` 測試案例，覆蓋：
   - valid signature → 200 OK
   - invalid signature → 400
   - 非文字訊息（貼圖、圖片）→ 忽略，200 OK
   - generate_response 拋出例外 → fallback 訊息，不影響 push 流程

## 驗收指令

```bash
pytest tests/test_line_webhook.py -v

# 啟動後 health check
./scripts/run_local.sh &
curl http://127.0.0.1:8000/health
# 期望：{"status":"ok"}
```
