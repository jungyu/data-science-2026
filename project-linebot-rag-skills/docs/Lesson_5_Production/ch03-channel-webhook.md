# Ch 03：Channel 抽象與 LINE Webhook

> 核心檔案：[`app/channels/`](../../app/channels/)、[`app/line/`](../../app/line/)
>
> Variant 適用性：**全部三個** — 任何 variant 都需要對外的入口

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 認識 `OutputChannel` Protocol：所有 channel 的契約 |
| 2 | 讀懂 `LineChannel`：簽章驗證 + webhook 解析 + push |
| 3 | 讀懂 `HttpChannel` / `StubChannel`：另外兩個進入點 |
| 4 | 看 `process_channel_input` 怎麼把所有 channel 統一成 graph 入口 |
| 5 | 跑一個 stub channel 跑通整個 graph（不需 LINE） |
| 6 | ✏️ 加自己的 channel（Telegram 範例） |
| 7 | 實務：用 ngrok / tunnel 把 LINE webhook 接到本機 |

---

## Step 1：認識 `OutputChannel` Protocol

打開 [`app/channels/base.py`](../../app/channels/base.py)，39 行：

```python
class ChannelInput(BaseModel):
    channel: str               # 'line' / 'http' / 'stub' / ...
    external_user_id: str      # LINE userId / HTTP session id
    external_message_id: str   # LINE message id / HTTP request id
    raw_text: str
    metadata: dict = Field(default_factory=dict)


class OutputChannel(Protocol):
    name: str

    def build_thread_id(self, inp: ChannelInput) -> str: ...
    async def load_recent_history(self, *, external_user_id: str, limit: int = 5) -> str: ...
    def format(self, markdown: str) -> list[str]: ...
    async def push(self, *, recipient_id: str, messages: list[str]) -> None: ...
```

任何 channel 都要實作這四個方法：

| 方法 | 做什麼 |
|------|--------|
| `build_thread_id` | 給 checkpointer / HITL 用的識別字串 |
| `load_recent_history` | 取最近 N 則對話組成 prompt 段落 |
| `format` | 把最終 markdown 切段（LINE 5000 字、Slack mrkdwn、web 完整） |
| `push` | 推送（LINE push API / HTTP response / 寫入 list） |

graph 不直接呼叫 LINE，而是 `services.channels[name].push(...)`——這層抽象讓同一個 graph 能服務多個入口。

---

## Step 2：讀懂 `LineChannel`

打開 [`app/channels/line.py`](../../app/channels/line.py)。72 行做了三件事：parse / format / push。

### 2-1 `parse_request`：webhook 進來怎麼解析

```python
async def parse_request(self, request: Request) -> tuple[bytes, list[ChannelInput]]:
    body = await request.body()
    sig = request.headers.get("x-line-signature")

    # 第一道防線：簽章驗證
    if not self._client.validate_signature(body, sig):
        raise HTTPException(status_code=400, detail="Invalid LINE signature")

    # 解析 LINE webhook payload（可能多個 event）
    payload = LineWebhookPayload.model_validate_json(body)
    out: list[ChannelInput] = []
    for ev in payload.events:
        if ev.is_text_message and ev.source.user_id and ev.message and ev.message.text:
            out.append(ChannelInput(
                channel="line",
                external_user_id=ev.source.user_id,
                external_message_id=ev.message.id,
                raw_text=ev.message.text,
            ))
    return body, out
```

注意它**只處理 text message**——`is_text_message` filter 把貼圖、語音、image 等 event 跳過。

### 2-2 簽章驗證怎麼算

打開 [`app/line/client.py`](../../app/line/client.py)：

```python
def validate_signature(self, body: bytes, signature: str | None) -> bool:
    if not signature or not self._settings.line_channel_secret:
        return False
    digest = hmac.new(
        self._settings.line_channel_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(signature, expected)
```

LINE Messaging API 規範：對 webhook body 做 HMAC-SHA256，secret 是 channel secret，結果 base64 後跟 `x-line-signature` 標頭比對。`hmac.compare_digest` 是防 timing attack 的常數時間比對。

### 2-3 `build_thread_id` / `load_recent_history`

```python
def build_thread_id(self, inp: ChannelInput) -> str:
    return f"line-{inp.external_user_id}-{inp.external_message_id}"

async def load_recent_history(self, *, external_user_id: str, limit: int = 5) -> str:
    try:
        return await self._messages_repo.build_recent_history(external_user_id, limit=limit)
    except Exception:
        return "No recent conversation."
```

thread_id 格式 `{channel}-{user_id}-{message_id}`——保證跨 channel 不衝突，且能反查屬於誰的對話。

`load_recent_history` 失敗時降級回 `"No recent conversation."`，不阻斷 graph。

### 2-4 `format` / `push`

```python
def format(self, markdown: str) -> list[str]:
    return split_for_line(markdown, max_chars=self._settings.line_max_message_chars)

async def push(self, *, recipient_id: str, messages: list[str]) -> None:
    await self._client.push_text(recipient_id, messages)
```

`split_for_line` 在 [`app/generator/formatter.py`](../../app/generator/formatter.py)（[Ch 07](ch07-sufficiency-generation.md) 詳述），主要處理 LINE 5000 字上限。

`push_text` 一次最多 5 則訊息（LINE API 限制），看 client 的 `messages[:5]` 截斷。

### 2-5 ✏️ 改成你的需求：調 LINE 訊息上限

`.env`：

```bash
LINE_MAX_MESSAGE_CHARS=4500  # 預留 buffer，避免邊界 case
```

或如果你的訊息常超 5 則：

```python
# app/line/client.py:33
"messages": [{"type": "text", "text": m} for m in messages[:10]],  # 5 → 10
```

但要注意 LINE API push 上限是 5。要送更多訊息得呼叫多次 `push_text`。

---

## Step 3：讀懂 `HttpChannel` / `StubChannel`

### 3-1 `HttpChannel`：給 Web UI / API / demo

[`app/channels/http.py`](../../app/channels/http.py)，40 行：

```python
class HttpChannel:
    name = "http"

    def build_thread_id(self, inp: ChannelInput) -> str:
        return f"http-{inp.external_user_id}-{inp.external_message_id}"

    async def load_recent_history(self, *, external_user_id, limit=5) -> str:
        return "No recent conversation."   # 預設無歷史

    def format(self, markdown: str) -> list[str]:
        return [markdown]                  # web 不切段

    async def push(self, *, recipient_id, messages) -> None:
        return                             # HTTP 同步回應，no-op
```

跟 LINE 的差別：

- **`push` 是 no-op**——HTTP endpoint 直接從 `final_state["responses"]` 取結果回傳，不需要 push
- **`format` 不切段**——web 端可以完整 markdown 渲染
- **`load_recent_history` 預設空**——HTTP 假設無狀態；要有 cross-session 對話自己加

### 3-2 `StubChannel`：給測試 / eval

[`app/channels/stub.py`](../../app/channels/stub.py)，29 行：

```python
class StubChannel:
    name = "stub"

    def __init__(self) -> None:
        self.pushed: list[tuple[str, list[str]]] = []   # ← push 寫進這個 list

    def build_thread_id(self, inp): return f"stub-{inp.external_user_id}-{inp.external_message_id}"
    async def load_recent_history(self, *, external_user_id, limit=5): return ""
    def format(self, markdown): return [markdown]

    async def push(self, *, recipient_id, messages) -> None:
        self.pushed.append((recipient_id, list(messages)))
```

關鍵：`push` 不去外面世界，**寫進 `self.pushed`**。測試可以 assert：

```python
assert ("U_test123", ["expected response"]) in stub_channel.pushed
```

[Ch 08 §HITL 測試](ch08-judge-hitl.md) 與 [Ch 09 §eval](ch09-observability-security.md) 都會用到。

---

## Step 4：`process_channel_input` 統一入口

打開 [`app/line/webhook.py:30-129`](../../app/line/webhook.py#L30-L129)。雖然檔案在 `line/` 底下，但這個函式**對所有 channel 通用**（task-23 把它變 channel-agnostic）。

### 4-1 完整流程

```python
async def process_channel_input(inp, services: RuntimeServices) -> None:
    # 1. 找對應 channel adapter
    channel = services.channels.get(inp.channel)

    # 2. inbound 落庫（DB 欄位仍叫 line_user_id，跨 channel 共用）
    await services.messages_repo.save_message(
        line_user_id=inp.external_user_id,
        direction="inbound",
        message_text=inp.raw_text,
    )

    # 3. 撈歷史
    recent_history = await channel.load_recent_history(
        external_user_id=inp.external_user_id
    )

    # 4. 組初始 state
    initial_state = {
        "user_input": inp.raw_text,
        "channel": inp.channel,
        "external_user_id": inp.external_user_id,
        "external_message_id": inp.external_message_id,
        "recent_history": recent_history,
        "dry_run": inp.external_user_id.startswith(("U_demo", "U_eval")),
    }

    # 5. 啟動 tracer（如果有）
    tracer = services.tracer_registry.start(...) if services.tracer_registry else None

    # 6. 跑 graph（帶 thread_id 給 checkpointer + HITL）
    thread_id = channel.build_thread_id(inp)
    graph_config = {"configurable": {"thread_id": thread_id}}
    final_state = await services.rag_graph.ainvoke(initial_state, config=graph_config)

    # 7. 檢查是否被 HITL interrupt
    if await _is_interrupted(services.rag_graph, graph_config):
        await services.messages_repo.mark_pending_review(
            thread_id=thread_id, line_user_id=inp.external_user_id
        )
        return

    # 8. outbound 落庫
    await services.messages_repo.save_message(
        line_user_id=inp.external_user_id,
        direction="outbound",
        message_text="\n\n".join(final_state.get("responses", [])),
        ...
    )
```

### 4-2 幾個關鍵設計

**`dry_run` 機制**：

```python
"dry_run": inp.external_user_id.startswith(("U_demo", "U_eval")),
```

`U_demo*` / `U_eval*` 開頭的 user_id 會啟動 dry run mode——graph 內某些節點會跳過 push、跳過落庫等。讓 demo / eval 不會污染真實資料。

**`thread_id` 是 LangGraph 的關鍵**：

```python
graph_config = {"configurable": {"thread_id": thread_id}}
final_state = await services.rag_graph.ainvoke(initial_state, config=graph_config)
```

沒有 `thread_id`，checkpointer 不會持久化、interrupt + resume 也不會運作。每個 channel 的 `build_thread_id` 都要保證唯一性。

**HITL interrupt 檢測**：

```python
async def _is_interrupted(graph, config: dict) -> bool:
    try:
        snapshot = await graph.aget_state(config)
    except Exception:
        return False
    return bool(getattr(snapshot, "next", ()))
```

LangGraph 中斷時 `aget_state(config).next` 會回傳 pending 節點名稱 tuple。檢測到 → 標 pending review、不推送。完整 HITL 流程在 [Ch 08](ch08-judge-hitl.md)。

### 4-3 ✏️ 改成你的需求：關閉 dry_run

`U_demo` / `U_eval` 是預設 magic prefix。如果你的真實 user_id 剛好撞到，可以改：

```python
# app/line/webhook.py:59
"dry_run": user_id.startswith(("__DEMO__", "__EVAL__")),
```

或從 settings 拉：

```python
# config.py 加
dry_run_user_prefixes: tuple[str, ...] = ("U_demo", "U_eval")

# webhook.py
"dry_run": any(user_id.startswith(p) for p in settings.dry_run_user_prefixes),
```

---

## Step 5：用 stub channel 跑通整個 graph（不用 LINE）

很多時候你想在沒架 LINE 的情況下測 graph，stub channel 就是為這個設計的。

### 5-1 寫一個最小 driver

```python
# scripts/test_with_stub.py
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    settings = Settings()
    services = await build_runtime_services(settings)

    inp = ChannelInput(
        channel="stub",
        external_user_id="U_test_001",
        external_message_id="msg_001",
        raw_text="你好，介紹一下你自己",
    )

    await process_channel_input(inp, services)

    stub = services.channels["stub"]
    for recipient, messages in stub.pushed:
        print(f"[push to {recipient}]")
        for m in messages:
            print(m)
            print("---")

asyncio.run(main())
```

### 5-2 跑

```bash
poetry run python scripts/test_with_stub.py
```

預期看到 graph 跑完，stub channel 的 `pushed` 列表裡有 bot 的回應。

### 5-3 ✏️ 改成你的需求：跑一個 golden case suite

```python
# scripts/run_golden.py
import asyncio, yaml
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    settings = Settings()
    services = await build_runtime_services(settings)

    with open("tests/cases/golden.yaml") as f:
        cases = yaml.safe_load(f)

    for case in cases:
        stub = services.channels["stub"]
        stub.pushed.clear()

        inp = ChannelInput(
            channel="stub",
            external_user_id=f"U_eval_{case['id']}",   # ← 觸發 dry_run
            external_message_id=case["id"],
            raw_text=case["query"],
        )
        await process_channel_input(inp, services)

        actual = "\n\n".join(stub.pushed[0][1]) if stub.pushed else ""
        if case["must_contain"] in actual:
            print(f"✅ {case['id']}")
        else:
            print(f"❌ {case['id']} — actual: {actual[:100]}")

asyncio.run(main())
```

CI 跑一遍就能驗收所有 golden case。

---

## Step 6：✏️ 加自己的 channel（Telegram 範例）

### 6-1 建立 `TelegramChannel`

```python
# app/channels/telegram.py
from typing import Any
import httpx
from app.channels.base import ChannelInput
from app.config import Settings


class TelegramChannel:
    name = "telegram"

    def __init__(self, settings: Settings, messages_repo: Any) -> None:
        self._settings = settings
        self._messages_repo = messages_repo
        self._bot_token = settings.telegram_bot_token

    def build_thread_id(self, inp: ChannelInput) -> str:
        return f"tg-{inp.external_user_id}-{inp.external_message_id}"

    async def load_recent_history(self, *, external_user_id, limit=5) -> str:
        try:
            return await self._messages_repo.build_recent_history(external_user_id, limit=limit)
        except Exception:
            return "No recent conversation."

    def format(self, markdown: str) -> list[str]:
        # Telegram 上限 4096，留 buffer
        return [markdown[i:i+3500] for i in range(0, len(markdown), 3500)]

    async def push(self, *, recipient_id: str, messages: list[str]) -> None:
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=15.0) as client:
            for m in messages:
                await client.post(url, json={
                    "chat_id": recipient_id,
                    "text": m,
                    "parse_mode": "Markdown",
                })
```

### 6-2 寫一個 webhook endpoint

```python
# app/telegram/webhook.py
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from app.channels.base import ChannelInput
from app.dependencies import RuntimeServices, get_runtime_services
from app.line.webhook import process_channel_input   # ← 復用！

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    services: RuntimeServices = Depends(get_runtime_services),
):
    body = await request.json()
    msg = body.get("message", {})
    text = msg.get("text")
    if not text:
        return {"ok": True}

    inp = ChannelInput(
        channel="telegram",
        external_user_id=str(msg["from"]["id"]),
        external_message_id=str(msg["message_id"]),
        raw_text=text,
    )
    background_tasks.add_task(process_channel_input, inp, services)
    return {"ok": True}
```

### 6-3 註冊到 dependencies

```python
# app/dependencies.py，在 build_runtime_services 內
from app.channels.telegram import TelegramChannel

channels["telegram"] = TelegramChannel(settings, messages_repo)
```

### 6-4 掛上 FastAPI

```python
# app/main.py
from app.telegram.webhook import router as tg_router

app.include_router(tg_router)
```

### 6-5 驗收

```bash
# 啟動
poetry run uvicorn app.main:app --reload

# 用 ngrok 暴露
ngrok http 8000

# Telegram BotFather 設 webhook：
# https://[ngrok-url]/api/telegram/webhook
```

Telegram 訊息進來 → 走同一份 graph → 從 Telegram channel push。**graph 一行沒改**。

這就是 channel 抽象的價值。

---

## Step 7：實務 — 用 ngrok 把 LINE webhook 接到本機

LINE 必須 HTTPS webhook，本機 dev 用 ngrok / cloudflared 之類的 tunnel。

### 7-1 用 ngrok

```bash
# 啟動服務
poetry run uvicorn app.main:app --reload

# 另一個 terminal 開 tunnel
ngrok http 8000
# → 給你 https://[xxxx].ngrok-free.app
```

### 7-2 用 cloudflared（無需登入）

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8000
# → 給你 https://[xxxx].trycloudflare.com
```

### 7-3 設到 LINE Developer Console

1. 進 [LINE Developers](https://developers.line.biz/) → 你的 channel
2. Messaging API → Webhook URL：填 `https://[xxxx].ngrok-free.app/api/line/webhook`
3. 點「Verify」應該回 200
4. 開啟 Use webhook、關閉 Auto-reply messages

### 7-4 ✏️ 改成你的需求：production 部署不用 tunnel

production 直接部署到 Cloud Run / Fly.io / Railway 等，拿到固定 HTTPS URL，填進 LINE 就好。完整部署流程在 [Ch 10](ch10-deployment-pitfalls.md)。

> 💡 完整 tunnel 設定見 [`docs/tunnel.md`](../tunnel.md)。

---

## 🎯 本章驗收

### Step 1：stub channel 跑通最小 case

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    services = await build_runtime_services(Settings())
    inp = ChannelInput(channel="stub", external_user_id="U_demo_1",
                       external_message_id="msg_1", raw_text="你好")
    await process_channel_input(inp, services)
    stub = services.channels["stub"]
    print("pushed:", stub.pushed)

asyncio.run(main())
'
```

預期：印出 `pushed: [("U_demo_1", ["..."])]`，至少一則回應。

### Step 2：HTTP channel 拿到 final_state

寫一個 HTTP endpoint：

```python
# 可加到 app/main.py 末尾或建新 router
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.channels.base import ChannelInput
from app.dependencies import RuntimeServices, get_runtime_services
from app.line.webhook import process_channel_input

class HttpChatRequest(BaseModel):
    user_id: str
    text: str

http_router = APIRouter()

@http_router.post("/api/http/chat")
async def http_chat(req: HttpChatRequest, services: RuntimeServices = Depends(get_runtime_services)):
    inp = ChannelInput(
        channel="http",
        external_user_id=req.user_id,
        external_message_id=f"http-{req.user_id}",
        raw_text=req.text,
    )
    # ⚠️ 注意：process_channel_input 跑完不會回 final_state，
    # 要直接 invoke graph 或自己 patch process_channel_input 回傳 state
    # 這裡示意，實作見 ch09 §eval driver
    await process_channel_input(inp, services)
    return {"ok": True}
```

跑 curl 試：

```bash
curl -X POST http://localhost:8000/api/http/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "U_demo_2", "text": "hello"}'
```

預期 200 OK。

### Step 3：LINE webhook 簽章驗證

不打 LINE 也能驗：

```bash
poetry run python -c '
from app.config import Settings
from app.line.client import LineMessagingClient
import hmac, hashlib, base64

c = LineMessagingClient(Settings())

body = b"test body"
sig = base64.b64encode(
    hmac.new(
        Settings().line_channel_secret.encode("utf-8"),
        body, hashlib.sha256
    ).digest()
).decode("utf-8")

print("valid:", c.validate_signature(body, sig))
print("invalid:", c.validate_signature(body, "wrong_signature"))
'
```

預期：`valid: True` / `invalid: False`。

### Step 4：（選擇性）ngrok + LINE real-world

跑 [Step 7](#step-7實務-用-ngrok-把-line-webhook-接到本機)，在 LINE 上跟 bot 對話成功。

---

## 下一章

[Ch 04：Intent Router 與 Skills 註冊](ch04-router-skills.md) — graph 第一步：把進來的訊息分類到對的 skill，決定要不要 RAG。
