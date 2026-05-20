# Ch 04：替換點 4 — 表達層（Channel）

> 核心檔案：[`app/channels/base.py`](../../app/channels/base.py)、
> [`app/channels/line.py`](../../app/channels/line.py)、
> [`app/channels/http.py`](../../app/channels/http.py)
>
> 🔗 **延伸閱讀**：本章聚焦在「**怎麼替你的領域接 channel**」。需要 production 細節（webhook 簽章驗證、`process_channel_input` 統一入口、Stub channel 測試流程、HITL interrupt 偵測、ngrok / cloudflared tunnel 部署、完整 Telegram 範例）請參考 [Lesson 5 Ch 03：Channel 抽象與 LINE Webhook](../Lesson_5_Production/ch03-channel-webhook.md)。

---

## 4-1  Channel 是什麼？

[`app/channels/base.py`](../../app/channels/base.py) 定義的 `OutputChannel` Protocol：

```python
class OutputChannel(Protocol):
    name: str

    def build_thread_id(self, inp: ChannelInput) -> str: ...
    async def load_recent_history(self, *, external_user_id: str, ...) -> str: ...
    def format(self, markdown: str) -> list[str]: ...       # Markdown → 格式化訊息
    async def push(self, *, recipient_id: str, messages: list[str]) -> None: ...
```

Graph 只呼叫這四個方法，不知道背後是 LINE、Telegram、還是 Next.js。

---

## 4-2  三個已有的實作，怎麼選？

| Channel | 檔案 | 適合 |
|---------|------|------|
| LINE | `app/channels/line.py` | 真實 bot，給 LINE 使用者 |
| HTTP | `app/channels/http.py` | REST API，接 Web 前端或 curl 測試 |
| Stub | `app/channels/stub.py` | 自動化測試，不真的送訊息 |

**`.env` 設定**（切換不需要改程式碼）：

```bash
CHANNEL=line    # 用 LINE
CHANNEL=http    # 用 HTTP API（/api/chat endpoint）
```

---

## 4-3  選項 A：LINE Bot（最快上線）

**需要準備**：
1. [LINE Developers Console](https://developers.line.biz) → 建 Messaging API channel
2. 拿到 `LINE_CHANNEL_ACCESS_TOKEN` 和 `LINE_CHANNEL_SECRET`
3. 設定 Webhook URL（用 ngrok 取得公開 URL）

```bash
# .env
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_CHANNEL_SECRET=your_secret
CHANNEL=line

# 啟動 ngrok
ngrok http 8000

# 把 ngrok URL 填入 LINE Developers Console 的 Webhook URL
# https://xxxx.ngrok-free.app/webhook
```

測試：用 LINE app 加 bot 為好友，傳送任何訊息，看 log：

```
INFO  channel=line  user_id=U_abc123  routing → your_skill_id
```

---

## 4-4  選項 B：HTTP API 接 Web 前端（Next.js + Tailwind）

HTTP Channel 已有實作（[`app/channels/http.py`](../../app/channels/http.py)）。
`/api/chat` endpoint（[`app/api/chat.py`](../../app/api/chat.py)）直接可用：

```bash
# 測試 HTTP channel
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "FastAPI 的 dependency injection 怎麼用？", "user_id": "web_user_001"}' \
  | python -m json.tool

# 回應
{
  "messages": [
    "根據官方文件，FastAPI 的 Depends() 函式讓你定義可重複使用的依賴...",
  ],
  "skill_used": "fastapi_guide",
  "chunks_retrieved": 3
}
```

**Next.js 前端範例**（最小可行版本）：

```tsx
// app/page.tsx
"use client";
import { useState } from "react";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<string[]>([]);

  async function send() {
    const res = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: input, user_id: "web_user" }),
    });
    const data = await res.json();
    setMessages(prev => [...prev, `你：${input}`, `Bot：${data.messages[0]}`]);
    setInput("");
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="space-y-2 mb-4 h-96 overflow-y-auto border rounded p-4">
        {messages.map((m, i) => <p key={i}>{m}</p>)}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded px-3 py-2"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
          placeholder="問你的 bot..."
        />
        <button className="bg-blue-500 text-white px-4 py-2 rounded" onClick={send}>
          送出
        </button>
      </div>
    </div>
  );
}
```

---

## 4-5  選項 C：Telegram Bot

> 📘 完整 Telegram channel + webhook + `dependencies.py` 註冊 + FastAPI 掛載
> 範例見 [Lesson 5 Ch 03 §Step 6](../Lesson_5_Production/ch03-channel-webhook.md#step-6-加自己的-channeltelegram-範例)。
> 下方是最小可行版本，給 Lesson 4 速戰用：

Telegram 目前沒有內建 adapter，但加一個只需要實作四個方法：

```python
# app/channels/telegram.py
import httpx
from app.channels.base import ChannelInput, OutputChannel

TELEGRAM_API = "https://api.telegram.org/bot{token}"

class TelegramChannel:
    name = "telegram"

    def __init__(self, token: str):
        self._token = token
        self._base  = TELEGRAM_API.format(token=token)

    def build_thread_id(self, inp: ChannelInput) -> str:
        return f"telegram:{inp.external_user_id}"

    async def load_recent_history(self, *, external_user_id: str, limit: int = 5) -> str:
        return ""   # 簡化版：不載入歷史

    def format(self, markdown: str) -> list[str]:
        # Telegram 支援 Markdown，但有 4096 字元限制
        chunks = []
        while len(markdown) > 4096:
            chunks.append(markdown[:4096])
            markdown = markdown[4096:]
        chunks.append(markdown)
        return chunks

    async def push(self, *, recipient_id: str, messages: list[str]) -> None:
        async with httpx.AsyncClient() as client:
            for msg in messages:
                await client.post(
                    f"{self._base}/sendMessage",
                    json={"chat_id": recipient_id, "text": msg, "parse_mode": "Markdown"},
                )
```

接進 `app/dependencies.py`：

```python
if settings.channel == "telegram":
    channel = TelegramChannel(token=settings.telegram_bot_token)
```

Telegram webhook 設定：

```bash
# 向 Telegram 登記你的 webhook URL
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://xxxx.ngrok-free.app/webhook/telegram"
```

---

## Eval Gate 4

```
選一個 channel（line / http / telegram），確認：
✅ 問一個和你 skill 相關的問題，收到有意義的回覆
✅ log 顯示 channel=<你的 channel>  routing → <你的 skill_id>
```

> 💡 不想架 LINE / Telegram 也能驗收：跑 [`scripts/test_with_stub.py`](../../scripts/test_with_stub.py) 透過 stub channel 灌訊息進 graph，看 stdout 的 push 內容。

下一章 → [Ch 05：Eval Gate 驗收](ch05-eval-gate.md)

---

## 接下來

讀完 Lesson 4 ch05 後若要把整套系統推上 production，建議按順序看 **[Lesson 5：Production 化](../Lesson_5_Production/README.md)**：channel 細節在 [Ch 03](../Lesson_5_Production/ch03-channel-webhook.md)、HITL 進階流程在 [Ch 08](../Lesson_5_Production/ch08-judge-hitl.md)、觀測 / 安全 / cost / 部署清單在 [Ch 09](../Lesson_5_Production/ch09-observability-security.md) 與 [Ch 10](../Lesson_5_Production/ch10-deployment-pitfalls.md)。
