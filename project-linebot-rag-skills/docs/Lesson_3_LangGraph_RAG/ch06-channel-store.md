# Ch 06：解耦 channel + store

> **本章對應**：[task-21](../ai-agent/tasks/task-21-channel-adapter.md)（Channel Adapter）+
> [task-22](../ai-agent/tasks/task-22-store-adapter.md)（Knowledge Store Adapter）
>
> **本章目標**：讓你能「換掉 LINE」或「換掉 Supabase」而不需要改 graph 的核心邏輯。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ 換成 HTTP channel，graph 不需要改                    ║
║  ✅ 換成 sqlite-vec，graph 不需要改                      ║
║  ✅ 能解釋 Protocol 模式為什麼比繼承更好                 ║
╚══════════════════════════════════════════════════════════╝
```

---

## 6-1  問題：改個小東西，到處都要動

假設你現在想把 LINE Bot 換成 Telegram Bot。

目前的程式碼把 LINE 的呼叫寫死在多個地方：

```python
# webhook.py
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import ApiClient, MessagingApi

# push_node
await services.line_client.push_text(user_id, responses)

# generate_node（錯誤時）
await services.line_client.push_text(user_id, ["系統錯誤，請稍後再試"])
```

換成 Telegram 就要找出所有 `line_client` 的地方，一個一個改。

**同樣的問題出現在 vector DB：**

```python
# retriever.py
from app.storage.supabase_client import get_supabase_client

result = supabase.rpc("match_private_knowledge", {...})
```

換成 Pinecone 或 sqlite-vec，又要改一堆地方。

---

## 6-2  解法：Protocol 模式（依賴倒置）

**核心思想**：graph 依賴「介面」，不依賴「實作」。

```
之前（依賴實作）：
  graph → LINE client

之後（依賴介面）：
  graph → ChannelAdapter（介面）
              ↑                ↑
         LINE Adapter    HTTP Adapter（測試用 / REST API 用）
```

Python 用 `Protocol` 來定義介面（不需要 `abstract class`，更輕量）：

```python
# app/channels/base.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class ChannelAdapter(Protocol):
    async def push_text(self, user_id: str, messages: list[str]) -> None: ...
    async def push_image(self, user_id: str, image_url: str) -> None: ...
    async def get_profile(self, user_id: str) -> dict: ...
```

> 💡 **Protocol vs ABC（抽象基底類別）**
>
> `ABC` 需要 `class LINE(AbstractAdapter)` 明確繼承。
> `Protocol` 不需要——只要你的類別有這些方法，它就「符合介面」。
> 這叫做 **structural subtyping**（結構子型別），Python 3.8+ 內建。
> 換第三方 SDK 時，你不需要動 SDK 的程式碼。

---

## 6-3  三個 Channel Adapter 實作

### LINE Adapter

```python
# app/channels/line_adapter.py
from linebot.v3.messaging import ApiClient, MessagingApi, TextMessage, PushMessageRequest

class LineChannelAdapter:
    def __init__(self, access_token: str):
        self._client = MessagingApi(ApiClient(...))
    
    async def push_text(self, user_id: str, messages: list[str]) -> None:
        for text in messages:
            await self._client.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=text)],
                )
            )
    
    async def push_image(self, user_id: str, image_url: str) -> None:
        ...  # 實作略
    
    async def get_profile(self, user_id: str) -> dict:
        profile = await self._client.get_profile(user_id)
        return {"display_name": profile.display_name}
```

---

### HTTP Adapter（REST API / 測試用）

```python
# app/channels/http_adapter.py
class HttpChannelAdapter:
    """把訊息存到 state，讓 /api/chat endpoint 直接回傳"""
    
    def __init__(self):
        self._outbox: list[dict] = []
    
    async def push_text(self, user_id: str, messages: list[str]) -> None:
        self._outbox.extend({"type": "text", "text": m} for m in messages)
    
    async def push_image(self, user_id: str, image_url: str) -> None:
        self._outbox.append({"type": "image", "url": image_url})
    
    async def get_profile(self, user_id: str) -> dict:
        return {"display_name": "HTTP User"}
    
    def flush(self) -> list[dict]:
        msgs, self._outbox = self._outbox, []
        return msgs
```

HTTP endpoint 用法：

```python
# app/api/chat.py
@router.post("/api/chat")
async def chat(body: ChatRequest, services: RuntimeServices = Depends(get_services)):
    adapter = HttpChannelAdapter()
    services = services.with_channel(adapter)   # 臨時替換 channel
    
    await services.rag_graph.ainvoke({
        "user_input":    body.message,
        "line_user_id":  body.user_id or "http_user",
        "recent_history": "",
    })
    
    return {"messages": adapter.flush()}
```

---

### Stub Adapter（自動化測試用）

```python
# app/channels/stub_adapter.py
class StubChannelAdapter:
    """不發送任何訊息，只收集輸出，供測試斷言用"""
    
    def __init__(self):
        self.sent: list[str] = []
    
    async def push_text(self, user_id: str, messages: list[str]) -> None:
        self.sent.extend(messages)
    
    async def push_image(self, user_id: str, image_url: str) -> None:
        pass
    
    async def get_profile(self, user_id: str) -> dict:
        return {"display_name": "Test User"}
```

測試寫起來很乾淨：

```python
async def test_rag_sends_response():
    stub = StubChannelAdapter()
    services = make_test_services(channel=stub)
    
    await services.rag_graph.ainvoke({
        "user_input":   "什麼是 App Router？",
        "line_user_id": "user_001",
    })
    
    assert len(stub.sent) == 1
    assert "App Router" in stub.sent[0]
```

---

## 6-4  Knowledge Store Adapter

同樣的模式，應用在 vector DB：

```python
# app/storage/base.py
from typing import Protocol
from app.rag.schemas import KnowledgeChunk

class KnowledgeStoreAdapter(Protocol):
    async def similarity_search(
        self,
        embedding: list[float],
        categories: list[str],
        top_k: int,
    ) -> list[KnowledgeChunk]: ...
    
    async def upsert_chunk(self, chunk: KnowledgeChunk) -> None: ...
    
    async def delete_by_source(self, source_url: str) -> int: ...
```

---

### Supabase 實作

```python
# app/storage/stores/supabase_store.py
class SupabaseKnowledgeStore:
    def __init__(self, client, table: str = "private_knowledge"):
        self._client = client
        self._table = table
    
    async def similarity_search(self, embedding, categories, top_k) -> list[KnowledgeChunk]:
        result = self._client.rpc(
            "match_private_knowledge",
            {
                "query_embedding": embedding,
                "filter_categories": categories,
                "match_count": top_k,
            }
        ).execute()
        return [KnowledgeChunk(**row) for row in result.data]
    
    async def upsert_chunk(self, chunk: KnowledgeChunk) -> None:
        self._client.table(self._table).upsert(chunk.model_dump()).execute()
    
    async def delete_by_source(self, source_url: str) -> int:
        result = self._client.table(self._table)\
            .delete().eq("source_url", source_url).execute()
        return len(result.data)
```

---

### sqlite-vec 實作（離線 / 開發用）

```python
# app/storage/stores/sqlite_store.py
import sqlite3
import sqlite_vec   # pip install sqlite-vec

class SqliteVecKnowledgeStore:
    def __init__(self, db_path: str = "knowledge.db"):
        self._conn = sqlite3.connect(db_path)
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._setup_schema()
    
    def _setup_schema(self):
        self._conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING vec0(
                embedding float[1536]
            );
            CREATE TABLE IF NOT EXISTS chunks_meta (
                rowid INTEGER PRIMARY KEY,
                id TEXT, content TEXT, source_url TEXT,
                category TEXT, score REAL
            );
        """)
    
    async def upsert(self, chunks: list[KnowledgeChunkInsert]) -> None:
        for c in chunks:
            # 1. 先寫向量（vec0 虛擬表只存 embedding）
            cur = self._conn.execute(
                "INSERT INTO chunks(embedding) VALUES (?)",
                (sqlite_vec.serialize_float32(c.embedding),),
            )
            rowid = cur.lastrowid   # vec0 自動分配的 rowid

            # 2. 寫 metadata（用同一個 rowid 對齊）
            self._conn.execute(
                """INSERT OR REPLACE INTO chunks_meta
                   (rowid, id, content, category, source_id, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (rowid, c.id, c.content, c.category, c.source_id, c.content_hash),
            )
        self._conn.commit()

    async def similarity_search(self, embedding, categories, top_k):
        rows = self._conn.execute("""
            SELECT m.id, m.content, m.category,
                   distance AS score
            FROM chunks v
            JOIN chunks_meta m ON v.rowid = m.rowid
            WHERE m.category IN ({placeholders})
            ORDER BY v.embedding <-> ?
            LIMIT ?
        """.format(placeholders=",".join("?" * len(categories))),
        (*categories, sqlite_vec.serialize_float32(embedding), top_k)
        ).fetchall()
        return [KnowledgeChunk(id=r[0], content=r[1], category=r[2],
                               combined_score=r[3]) for r in rows]

    # upsert 時如何更新已存在的 chunk？
    # → 先 DELETE FROM chunks WHERE rowid = (SELECT rowid FROM chunks_meta WHERE content_hash = ?)
    # → 再 INSERT（新 rowid）
    # Supabase 用 ON CONFLICT content_hash DO UPDATE 做同樣的事
```

切換方式（`.env`）：

```bash
KNOWLEDGE_STORE=supabase    # 預設
KNOWLEDGE_STORE=sqlite       # 離線開發
```

---

## 6-5  組裝 RuntimeServices

```python
# app/dependencies.py
from app.channels.line_adapter import LineChannelAdapter
from app.channels.http_adapter import HttpChannelAdapter
from app.storage.stores.supabase_store import SupabaseKnowledgeStore
from app.storage.stores.sqlite_store import SqliteVecKnowledgeStore

def get_services(settings: Settings) -> RuntimeServices:
    # Channel
    if settings.channel_type == "line":
        channel = LineChannelAdapter(settings.line_channel_access_token)
    else:
        channel = HttpChannelAdapter()
    
    # Store
    if settings.knowledge_store == "supabase":
        store = SupabaseKnowledgeStore(get_supabase_client(settings))
    else:
        store = SqliteVecKnowledgeStore(settings.sqlite_db_path)
    
    return RuntimeServices(channel=channel, store=store, ...)
```

---

## ✏️ 本章任務

1. 完成 task-21（`ChannelAdapter` Protocol + LINE / HTTP / Stub 三個實作）
2. 完成 task-22（`KnowledgeStoreAdapter` Protocol + Supabase / sqlite-vec 實作）
3. 用 `HttpChannelAdapter` 跑通 `/api/chat` endpoint
4. 用 `StubChannelAdapter` 改寫一個現有測試，確認不需要真實 LINE 連線
5. 在 `WEEK6.md` 記錄：你的 capstone 計畫用哪個 channel + store 組合？

---

## 📝 沒有蠢問題

**Q：為什麼用 Protocol 而不是直接用 `if isinstance(...)` 判斷？**

A：`isinstance` 讓程式碼依賴具體類別——你加一個新 adapter 就要改判斷邏輯。
Protocol 讓程式碼說「我需要有 push_text 方法的東西」，任何實作都能用。
這是 SOLID 原則裡的「依賴倒置原則（D）」和「開放封閉原則（O）」。

**Q：sqlite-vec 和 Supabase 的向量搜尋結果一樣嗎？**

A：不完全一樣。Supabase 用 `pgvector` 的 `ivfflat` index，sqlite-vec 用精確搜尋。
小資料集（<10K chunks）結果相近，大資料集會有差異。
開發和測試用 sqlite-vec（不需要網路），生產用 Supabase，是合理的選擇。

**Q：我的 capstone 一定要實作 sqlite-vec 嗎？**

A：不必要，Supabase 就夠了。
sqlite-vec 是讓你有「離線備份方案」的選項，不是必要條件。
Task-22 的最低要求是完成 Protocol 定義 + 一個 store 實作。

---

## 🧠 腦力激盪

> 如果你的 bot 需要同時支援 LINE 和 Telegram（雙通道），
> 你的 `push_node` 要怎麼改？
>
> 提示：
> - `RuntimeServices` 裡的 `channel` 能不能是一個 list？
> - 還是你應該有一個 `MultiChannelAdapter` 包住兩個 adapter？
> - 這兩種方案的 trade-off 是什麼？

---

## 🎯 本章里程碑

```
curl http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "什麼是 App Router？"}'

# 回傳 {"messages": ["根據文件，App Router 是..."]}
# graph 完全沒有 LINE 相關的程式碼
```

---

上一章 → [Ch 05：量化 + 觀測](ch05-evaluation.md)
下一章 → [Ch 07：多格式 + 人工介入](ch07-multiformat-hitl.md)
