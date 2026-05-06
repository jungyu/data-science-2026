# Spec-23：Channel Adapter Layer

## 背景

目前 graph 與 LINE 緊耦合：

- `RAGState` 直接含 `line_user_id`
- `push_node` 寫死 `services.line_client.push_text`
- `recent_history` 來源於 `messages_repo.build_recent_history(line_user_id)`，schema 綁 LINE 欄位
- HITL（spec-21）`thread_id` 用 `f"line-{user_id}-{event_id}"` 命名
- `responder.format_for_line` 切段邏輯按 LINE 5000 char 上限

學生若想做「web RAG / Slack bot / 純 API 服務 / 多 channel 共用知識庫」（即所謂「專業 RAG 服務」最常見形態），必須改 graph state、改 push、改 history、改 formatter——四處連動。roadmap §「給學生」承諾「只動 4 處」在這個情境下不成立。

本 spec 把所有 channel-specific 關注點抽成 **Adapter** 介面，graph 與 channel 解耦。提供 `LineChannel`（既有行為打包）+ `HttpChannel`（新增，給 web UI / API）兩個範例實作，學生新增 channel 時照著做即可。

## 設計

### Channel Adapter 邊界

| 屬於 channel 的關注點 | 屬於 graph core 的關注點 |
|---|---|
| 簽章驗證 / webhook 解析 | 路由、檢索、生成、評分 |
| 訊息切段（LINE 5000 / Slack 40k / Web 不切）| 文本長度沒有上限 |
| 推送（push API / HTTP response / WebSocket）| 不關心怎麼送出 |
| Recipient 識別（line_user_id / slack_user / session_id）| 用通用 `external_user_id` |
| 歷史對話讀取（按 channel 的儲存方式）| 拿到 message list 即可 |
| Streaming 機制（SSE / Push API 不支援）| 提供 chunk yield，不強制 |

### `RAGState` schema 通用化

修改 `app/graph/state.py`：

```python
class ChannelInput(BaseModel):
    channel: str                    # "line" | "http" | "slack" | ...
    external_user_id: str           # 不再寫死 line_user_id
    external_message_id: str
    raw_text: str
    metadata: dict = {}             # channel-specific 補充欄位


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    timestamp: datetime


class RAGState(TypedDict, total=False):
    user_input: str
    channel: str
    external_user_id: str
    external_message_id: str
    recent_history: list[HistoryMessage]   # 改為 list 而非字串
    # ...其餘 graph 內部欄位不變
```

`line_user_id` 不再出現在 state；舊欄位保留別名 `line_user_id` 在 LINE adapter 內部使用，graph 不感知。

### `OutputChannel` Protocol

新增 `app/channels/base.py`：

```python
class OutputChannel(Protocol):
    name: str  # "line" | "http" | ...

    # —— 入口側
    async def parse_request(self, request: Request) -> list[ChannelInput]: ...
    def build_thread_id(self, inp: ChannelInput) -> str: ...
    async def load_recent_history(
        self, *, external_user_id: str, limit: int = 5
    ) -> list[HistoryMessage]: ...

    # —— 出口側
    def format(self, markdown: str) -> list[str]: ...
    async def push(self, *, recipient_id: str, messages: list[str]) -> None: ...

    # —— Streaming（可選，default 不實作）
    async def stream(self, *, recipient_id: str, chunks: AsyncIterator[str]) -> None: ...
```

### 三個具體 adapter

| Adapter | 用途 | 實作 |
|---|---|---|
| `LineChannel` | 既有行為打包 | 把 `app/line/*` 的邏輯搬進來，行為等價 |
| `HttpChannel` | Web UI / API / 學生 demo | FastAPI 同步請求 → 回 JSON `{"responses": [...]}` |
| `StubChannel` | 測試用 | `push` 寫進 list；`load_recent_history` 回固定值 |

`SlackChannel` 不在本 spec 範圍——但 `OutputChannel` 介面足以讓學生加。

### Push node 改寫

```python
async def push_node(state: RAGState, services: RuntimeServices):
    channel = services.channels[state["channel"]]
    formatted = channel.format("\n\n".join(state["responses"]))
    await channel.push(
        recipient_id=state["external_user_id"],
        messages=formatted,
    )
    return {}
```

`responder.format_for_line` 不再被 graph 呼叫；遷移成 `LineChannel.format` 內部使用。

### Web entry point

新增 `app/api/chat.py`：

```python
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    responses: list[str]
    citations: list[Citation] | None = None
    sufficiency: str | None = None
    judge_score: dict | None = None


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest, services: RuntimeServices = Depends(get_runtime_services)
) -> ChatResponse:
    channel = services.channels["http"]
    inp = ChannelInput(
        channel="http",
        external_user_id=req.user_id,
        external_message_id=req.session_id or _new_id(),
        raw_text=req.message,
    )
    history = await channel.load_recent_history(external_user_id=req.user_id)
    initial_state: RAGState = {
        "user_input": req.message,
        "channel": "http",
        "external_user_id": req.user_id,
        "external_message_id": inp.external_message_id,
        "recent_history": history,
    }
    config = {"configurable": {"thread_id": channel.build_thread_id(inp)}}
    final = await services.rag_graph.ainvoke(initial_state, config=config)
    return ChatResponse(
        responses=final.get("responses", []),
        citations=final.get("answer_contract").citations if final.get("answer_contract") else None,
        sufficiency=final.get("sufficiency"),
        judge_score=final.get("judge_score").model_dump() if final.get("judge_score") else None,
    )
```

`HttpChannel.push()` 是 no-op（response 直接回 JSON），但 `load_recent_history` / `format` 仍要實作。

### 多 channel 共用 graph

`RuntimeServices` 持有 channel registry：

```python
@dataclass(frozen=True)
class RuntimeServices:
    channels: dict[str, OutputChannel]
    # ...其餘
```

入口（webhook / chat endpoint）依 channel 名取 adapter，graph 完全不感知 channel 種類。

### 與既有 spec 的相容性

| Spec | 衝突 / 調整 |
|---|---|
| spec-12 ~ spec-19 | state 欄位重命名（`line_user_id` → `external_user_id`），node 改用通用欄位 |
| spec-21 HITL | `thread_id` 命名改為 `f"{channel}-{user_id}-{message_id}"`；`review_queue.py` 列表加 channel column |
| spec-22 observability | trace `payload` 加 channel 欄位 |
| spec-20 evaluation | runner 用 `StubChannel`，不再用 `U_eval_*` 字串前綴 hack |

修改面雖廣但都是機械性 rename + 委派；不破壞功能。

### 不做什麼

- 不實作 SlackChannel / DiscordChannel（學生練手）
- 不做 channel 之間的訊息互通（同一 user 在 LINE 與 Web 對話可看到對方歷史）——複雜且不教學
- 不做 streaming（spec-26 範圍）

## 介面契約

**新增**：

| 檔案 | 用途 |
|---|---|
| `app/channels/__init__.py` | registry：`CHANNELS = {"line": LineChannel(...), "http": HttpChannel(...)}` |
| `app/channels/base.py` | `OutputChannel` Protocol、`ChannelInput` / `HistoryMessage` schema |
| `app/channels/line.py` | 既有 `app/line/` 邏輯重新封裝 |
| `app/channels/http.py` | Web / API adapter |
| `app/channels/stub.py` | 測試 / eval / demo 用 |
| `app/api/chat.py` | `/api/chat` endpoint |

**修改**：

- `app/graph/state.py`：`line_user_id` → `external_user_id`、`recent_history` 改 list
- `app/graph/nodes.py::push_node`：委派給 channel
- `app/dependencies.py`：注入 `channels` registry
- `app/main.py`：掛上新 `chat` router
- `app/line/webhook.py`：薄 wrapper，內部走 `LineChannel.parse_request`

**移除（或改為向後相容 alias）**：

- `app/generator/responder.py::format_for_line` → 移到 `LineChannel.format`

**新增 dependency**：無（HTTP 已有 FastAPI）

**Settings 新增**：

```python
enabled_channels: list[str] = ["line", "http"]
```

## 驗收標準

- LINE 端對端：同一則訊息，重構前後回覆 byte-for-byte 一致
- HTTP 端對端：`POST /api/chat {"user_id":"u1","message":"什麼是 RAG"}` 能回 JSON，內容與 LINE 相同問題的回覆語意一致
- 兩個 channel 在同一份 graph 上跑，`scripts/demo_compare_variants.py` 用 `StubChannel` 不需動 graph 程式
- `python scripts/eval.py` 改用 `StubChannel`，移除 `U_eval_*` 前綴 hack
- 移除 `RAGState.line_user_id` 後，全 codebase grep 不到 `line_user_id` 出現在 graph / nodes 內（僅應在 `app/channels/line.py` 內出現）
- HITL `thread_id` 命名格式測試：LINE 與 HTTP 兩個 channel 對同 user_id 的請求**不會撞 thread**
- README 加「新增 channel」的範例：student 寫 `SlackChannel` 只需動 `app/channels/slack.py` 一個檔
- 既有測試套件無回歸；新增 `tests/test_channels/` 三個 adapter 各一份單元測試
