# Ch 02：Repo Pattern 與 DB 實務操作

> 核心檔案：[`app/storage/`](../../app/storage/) 全部
>
> Variant 適用性：**全部三個** — basic / selfrag / reflection 共用同一層 storage

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 認識 `SupabaseRestClient`：薄包裝的 HTTP 入口 |
| 2 | 讀懂 `KnowledgeRepository`，改成符合你資料的 top_k 預設 |
| 3 | 讀懂 `MessagesRepository`：save / history / HITL 三大職責 |
| 4 | 認識 `LogsRepository` / `TracesRepository`：極簡到一行 |
| 5 | 讀懂 `CacheRepository`：knowledge_version 失效機制 |
| 6 | 認識 `KnowledgeStore` Protocol，知道怎麼換到 sqlite-vec / Pinecone |
| 7 | 實務 A：psql 日常操作（查、改、reset） |
| 8 | 實務 B：`knowledge_version` 更新讓 cache 自動失效 |
| 9 | 實務 C：Supabase CLI 與 migration 策略 |

---

## Step 1：認識 `SupabaseRestClient`

打開 [`app/storage/supabase_client.py`](../../app/storage/supabase_client.py)：106 行的薄包裝，把所有 Supabase REST API 操作集中到一個類別。

### 1-1 五個方法

```python
class SupabaseRestClient:
    async def rpc(function_name, payload)              # 呼叫 stored function
    async def insert(table, row)                       # 寫一筆
    async def upsert(table, rows, on_conflict=...)     # 寫或更新
    async def select(table, params)                    # 查（params 走 PostgREST query syntax）
    async def update(table, patch, filters)            # 改（不會 INSERT）
```

application 端不直接打 httpx，永遠透過這層。好處：

- 統一 timeout（30 秒）
- 統一 header（service role key + schema profile）
- 統一錯誤處理（特別是 `upsert` 失敗時把 PostgREST 訊息完整冒泡，不是只回一個 `HTTPStatusError`）

### 1-2 為什麼不用官方 `supabase-py`？

- 官方 client 是 sync，本專案全 async
- 自己包可以精準控制錯誤訊息（見 [`supabase_client.py:67-76`](../../app/storage/supabase_client.py#L67-L76)）

```python
# 看 upsert 失敗時的 log
if response.status_code >= 400:
    logging.getLogger(__name__).error(
        "upsert %s failed: status=%s body=%s keys=%s",
        table, response.status_code, response.text[:500],
        sorted(rows[0].keys()) if rows else [],
    )
```

PostgREST 的錯誤訊息很長且很實用（會告訴你哪個欄位 type 不對、缺什麼）。debug 時非常救命。

### 1-3 ✏️ 改成你的需求：加 timeout 控制

預設 30 秒。如果你打的 RPC 慢（例如大量資料的向量檢索），可以改：

```python
# app/storage/supabase_client.py
async def rpc(self, function_name, payload):
    async with httpx.AsyncClient(timeout=60.0) as client:   # ← 改這裡
        ...
```

或更乾淨——從 settings 拉：

```python
def __init__(self, settings: Settings) -> None:
    self._settings = settings
    self._timeout = settings.supabase_timeout_seconds   # 加到 config.py

async def rpc(self, function_name, payload):
    async with httpx.AsyncClient(timeout=self._timeout) as client:
        ...
```

---

## Step 2：讀懂 `KnowledgeRepository`

[`app/storage/knowledge_repo.py`](../../app/storage/knowledge_repo.py) 整檔只有 32 行：

```python
class KnowledgeRepository:
    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    async def match_private_knowledge(
        self,
        *,
        query_embedding: list[float],
        query_text: str,
        categories: list[str] | None = None,
        top_k: int = 8,
        vector_weight: float = 1.0,
        keyword_weight: float = 0.0,
    ) -> list[KnowledgeChunk]:
        rows = await self._client.rpc(
            "match_private_knowledge",
            {
                "query_embedding": query_embedding,
                "query_text": query_text,
                "match_count": top_k,
                "category_filter": categories or None,
                "vector_weight": vector_weight,
                "keyword_weight": keyword_weight,
            },
        )
        return [KnowledgeChunk.model_validate(row) for row in rows]
```

它做的事：

1. 把 Python 參數打包成 dict
2. 呼叫 [Ch 01 Step 5 的 RPC](ch01-supabase-schema.md#step-5套用-functionssql用-sql-打-rpc)
3. 把回傳的 dict list 轉成 `KnowledgeChunk` pydantic 物件

`KnowledgeChunk` 的 schema 在 [`app/rag/schemas.py`](../../app/rag/schemas.py)（[Ch 06](ch06-multi-seed-retrieval.md) 詳述）。

### 2-1 ✏️ 改成你的需求一：調 top_k 預設

預設 `top_k=8`。如果你的 chunk 切得很細（每個 chunk 只有幾句話），需要更多 context：

```python
top_k: int = 20,   # 或從 settings 拉：top_k: int = settings.default_top_k
```

更乾淨的做法——讓呼叫端決定，不在這裡寫死。

### 2-2 ✏️ 改成你的需求二：永遠加上某個 category filter

假設你的 bot 永遠只查特定 categories，不希望別的 category 漏進來：

```python
async def match_private_knowledge(self, *, query_embedding, query_text, categories=None, ...):
    # 強制白名單
    ALLOWED = {"medical", "pharmacy", "general"}
    if categories:
        categories = [c for c in categories if c in ALLOWED]
    else:
        categories = list(ALLOWED)

    rows = await self._client.rpc(...)
```

這比在 router 那邊過濾更安全——即使 router 出包，DB 層還有一道防線。

---

## Step 3：讀懂 `MessagesRepository`

[`app/storage/messages_repo.py`](../../app/storage/messages_repo.py)，127 行，但分成**三組職責**：

### 3-1 第一組：對話歷史（save + list + build）

```python
async def save_message(self, *, line_user_id, direction, message_text, skill_id=None, router_result=None, rag_used=False)
async def list_recent_messages(self, line_user_id, limit=5)
async def build_recent_history(self, line_user_id, limit=5)
```

`save_message` 對應 [Ch 01 §7-1 line_messages 表](ch01-supabase-schema.md#7-1-line_messages--對話歷史)。

`build_recent_history` 把多筆 row 組成餵給 LLM 的 prompt 段落：

```python
async def build_recent_history(self, line_user_id, limit=5) -> str:
    rows = await self.list_recent_messages(line_user_id, limit=limit)
    if not rows:
        return "No recent conversation."

    lines = []
    for row in reversed(rows):
        speaker = "user" if row["direction"] == "inbound" else "assistant"
        lines.append(f"{speaker}: {row['message_text']}")
    return "\n".join(lines)
```

注意 `reversed(rows)`——`list_recent_messages` 是 `order by created_at.desc`（最新在前），但組 prompt 要時間正序，所以反過來。

### 3-2 第二組：HITL 三段式（mark / list / resolve）

```python
async def mark_pending_review(self, *, thread_id, line_user_id, status="pending")    # 進入待審
async def list_pending_reviews(self, limit=50)                                        # CLI / Dashboard 看清單
async def resolve_pending_review(self, *, thread_id, status)                          # approve / revise / drop
```

三個方法都有同樣的容錯模式：

```python
try:
    await self._client.upsert(...)   # 或 select / update
except Exception as exc:
    logger.warning("mark_pending_review failed thread=%s: %s(%s)",
                   thread_id, type(exc).__name__, exc)
```

**為什麼 HITL 方法都包 try/except？** 因為 `hitl_pending_reviews` 是 opt-in 表，學生若沒套用 `:51-68` 的部分，這些呼叫會 404。**graph 主流程不能被「opt-in 表沒建」打斷**，所以靜默吞掉，但記 log 讓 debug 能看到。

完整 HITL 流程在 [Ch 08](ch08-judge-hitl.md)。

### 3-3 ✏️ 改成你的需求：在 save_message 加自訂 metadata

假設你想記錄每則訊息的「情緒分數」（router 在 [Ch 04](ch04-router-skills.md) 會算）。最不破壞 schema 的做法是**塞進 `router_result` jsonb**：

```python
# 呼叫端
await messages_repo.save_message(
    line_user_id=user_id,
    direction="inbound",
    message_text=text,
    router_result={
        **router.result_dict(),
        "emotion_score": 0.8,  # ← 多加一個 key
    },
)
```

完全不用改 `save_message` 也不用改 schema——jsonb 的彈性就是這樣。

如果之後這個欄位變熱、需要 index，再 promote 成獨立欄位：

```sql
alter table line_messages add column emotion_score numeric;
create index line_messages_emotion_idx on line_messages(emotion_score);
```

### 3-4 ✏️ 改成你的需求：換 history 預設長度

```python
async def build_recent_history(self, line_user_id, limit=10) -> str:  # 5 → 10
```

但更建議從 settings 拉，[Ch 04](ch04-router-skills.md) 會看到 router prompt 對 history 長度敏感。

---

## Step 4：認識 `LogsRepository` / `TracesRepository`

### 4-1 LogsRepository：極簡到一行

[`app/storage/logs_repo.py`](../../app/storage/logs_repo.py) 整檔：

```python
class LogsRepository:
    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    async def log_retrieval(self, record: RetrievalLogRecord) -> None:
        await self._client.insert("retrieval_logs", record.model_dump())
```

`RetrievalLogRecord` 是個 pydantic model（[`app/rag/schemas.py`](../../app/rag/schemas.py)），結構直接對應 [Ch 01 §7-2 retrieval_logs 表](ch01-supabase-schema.md#7-2-retrieval_logs--檢索日誌)。

[Ch 06](ch06-multi-seed-retrieval.md) 會看到 retriever 在每次 fan-out 完都會呼叫 `log_retrieval`。

### 4-2 TracesRepository：opt-in trace 落庫

[`app/storage/traces_repo.py`](../../app/storage/traces_repo.py)，58 行。對應 [Ch 01 §8-3 graph_traces 表](ch01-supabase-schema.md#8-3-graph_traces--跨-session-trace獨立檔)：

```python
class TracesRepository:
    async def insert(self, trace: dict[str, Any]) -> None:
        """寫一筆 trace（GraphTracer.finalize() 的輸出）。"""
        row = {
            "thread_id": trace["thread_id"],
            "variant": trace["variant"],
            "started_at": _iso(trace.get("started_at")),
            "finished_at": _iso(trace.get("finished_at")),
            "total_duration_ms": trace.get("total_duration_ms", 0),
            "total_input_tokens": trace.get("total_input_tokens", 0),
            "total_output_tokens": trace.get("total_output_tokens", 0),
            "total_cost_usd": trace.get("total_cost_usd", 0),
            "payload": trace,
        }
        await self._client.insert("graph_traces", row)

    async def recent(self, *, variant=None, limit=50) -> list[dict[str, Any]]:
        """讀近 N 筆 trace。"""
        ...
```

注意這層**不**包 try/except——`OBSERVABILITY_PERSIST=true` 才會啟用，啟用後就視為正式設定，失敗應該冒泡讓 caller 知道。完整 tracer 在 [Ch 09](ch09-observability-security.md)。

### 4-3 ✏️ 改成你的需求：把 trace 跟 retrieval_log 串起來

兩者各自獨立，要關聯要靠 application 補。常見做法是把 `thread_id` 也塞進 `retrieval_logs` 的 metadata：

```python
# 呼叫 log_retrieval 時
record = RetrievalLogRecord(
    line_user_id=...,
    query=...,
    scores={..., "thread_id": thread_id},  # 借 jsonb scores 欄位塞
)
```

或乾脆加一個 `thread_id` column：

```sql
alter table retrieval_logs add column thread_id text;
create index retrieval_logs_thread_idx on retrieval_logs(thread_id);
```

這樣 dashboard 上點一個 trace 就能撈出該 thread 所有檢索紀錄。

---

## Step 5：讀懂 `CacheRepository`

[`app/storage/cache_repo.py`](../../app/storage/cache_repo.py)，132 行，對應 [Ch 01 §8-2 prompt_cache 表](ch01-supabase-schema.md#8-2-prompt_cache--llm-回應快取)。

### 5-1 cache_key 怎麼算

```python
def _normalize(user_input: str) -> str:
    return user_input.strip().lower()

def build_cache_key(*, skill_id: str, knowledge_version: int, user_input: str) -> str:
    payload = f"{skill_id}:{knowledge_version}:{_normalize(user_input)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

三個元素打進 hash：

- `skill_id`：同 prompt 不同 skill 不能共用 cache
- `knowledge_version`：知識更新就失效（這是失效機制的核心）
- `normalized_user_input`：去頭尾空白 + 小寫，讓「`你好`」與「`  你好  `」共用一筆 cache

### 5-2 get / set 都靜默吞錯

```python
async def get(self, cache_key: str) -> str | None:
    try:
        rows = await self._client.select("prompt_cache", {...})
    except Exception as exc:
        logger.warning("CacheRepository.get failed: %s", _describe(exc))
        return None
    if not rows:
        return None
    return rows[0].get("response_text")
```

跟 HITL 同理——cache 是 opt-in，不能因為它出問題就阻斷 graph。

### 5-3 `get_knowledge_version` 的 60 秒 TTL cache

```python
_KNOWLEDGE_VERSION_TTL_SECONDS = 60

async def get_knowledge_version(self) -> int:
    if self._version_cache is not None:
        version, cached_at = self._version_cache
        if time.monotonic() - cached_at < self._version_ttl:
            return version

    try:
        rows = await self._client.select(
            "private_knowledge",
            {"select": "knowledge_version", "order": "knowledge_version.desc", "limit": "1"},
        )
    except Exception as exc:
        logger.warning("get_knowledge_version failed: %s", _describe(exc))
        return 0
    if not rows:
        return 0
    version = int(rows[0].get("knowledge_version") or 0)
    self._version_cache = (version, time.monotonic())
    return version
```

如果每次 cache lookup 都先去 DB 撈 `knowledge_version`，等於把 cache 收益吃掉一半。in-process TTL cache 解決這問題——60 秒內所有 lookup 共用同一個 version。

代價：**ingest 新資料後最多 60 秒延遲生效**。對教學/生產都可接受。

### 5-4 ✏️ 改成你的需求：調 TTL

如果你的 ingest 很頻繁（每幾秒就 update），60 秒太長：

```python
# app/storage/cache_repo.py:35
_KNOWLEDGE_VERSION_TTL_SECONDS = 10   # 改成 10 秒
```

如果你的 ingest 很罕見（每天一次），可以放更長：

```python
_KNOWLEDGE_VERSION_TTL_SECONDS = 300  # 5 分鐘
```

更乾淨——從 settings 拉：

```python
def __init__(self, client, *, version_ttl_seconds=_KNOWLEDGE_VERSION_TTL_SECONDS):
    ...
# dependencies.py 建立 CacheRepository 時傳：
CacheRepository(client, version_ttl_seconds=settings.cache_version_ttl)
```

### 5-5 ✏️ 改成你的需求：cache key 加上 user_id（per-user cache）

假設你的 bot 同樣的問題對不同人要給不同答案（例如帶用戶背景）：

```python
def build_cache_key(*, skill_id, knowledge_version, user_input, user_id=None):
    parts = [skill_id, str(knowledge_version), _normalize(user_input)]
    if user_id:
        parts.append(user_id)
    payload = ":".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

權衡：per-user cache 命中率低很多，可能不划算。先用 metrics 看你的「同問題不同人」比例多高再決定。

---

## Step 6：認識 `KnowledgeStore` Protocol

[`app/storage/knowledge_store.py`](../../app/storage/knowledge_store.py)，74 行。這是 retrieval 層的關鍵抽象——**讓 retriever 不綁定 Supabase**。

### 6-1 Protocol 定義

```python
class KnowledgeStore(Protocol):
    name: str

    async def search(self, *, query_embedding, query_text=None, filters=None, top_k=8) -> list[KnowledgeChunk]: ...
    async def upsert(self, chunks: list[KnowledgeChunkInsert]) -> int: ...
    async def delete_by_source(self, source_id: str) -> int: ...
    async def health_check(self) -> bool: ...
    async def source_hash(self, source_id: str) -> str | None: ...
```

三個實作在 [`app/storage/stores/`](../../app/storage/stores/)：

| 實作 | 適用 |
|------|------|
| `SupabaseKnowledgeStore` | 預設、本專案 production |
| `SqliteVecStore` | 教學版單機、零外部依賴 |
| `PineconeStore` | 雲端 vector DB（如果你已經有 Pinecone） |

### 6-2 為什麼要這層抽象？

- **教學**：學生可以從 sqlite-vec 起步，不用先建 Supabase
- **可選 vendor**：未來想換 Qdrant / Weaviate，只要新增一個 store class
- **測試**：mock 一個 in-memory store 給單元測試用

retriever（[`app/rag/retriever.py`](../../app/rag/retriever.py)）只認 Protocol，不關心後面是誰。

### 6-3 ✏️ 改成你的需求：切換到 sqlite-vec

`.env`：

```bash
# 把預設的 supabase 切到 sqlite_vec
KNOWLEDGE_STORE=sqlite_vec
SQLITE_VEC_PATH=./data/knowledge.db
```

[`app/dependencies.py`](../../app/dependencies.py) 會依 `KNOWLEDGE_STORE` 在啟動時 build 對應 store。retriever / ingest 完全不用改。

### 6-4 ✏️ 進階：寫你自己的 store

假設你想接 ElasticSearch：

```python
# app/storage/stores/es_store.py
from app.storage.knowledge_store import KnowledgeStore
from app.rag.schemas import KnowledgeChunk

class ElasticSearchStore:
    name = "elasticsearch"

    def __init__(self, settings): ...

    async def search(self, *, query_embedding, query_text=None, filters=None, top_k=8):
        # 用 ES kNN search API
        ...

    async def upsert(self, chunks): ...
    async def delete_by_source(self, source_id): ...
    async def health_check(self): ...
    async def source_hash(self, source_id): ...
```

把它註冊到 dependencies.py 的 store factory，然後 `KNOWLEDGE_STORE=elasticsearch` 就生效。

---

## Step 7：實務 A — psql 日常操作

接下來三個 Step 是 DB 日常操作，跟 application code 無關。

### 7-1 查資料

```bash
# 看 schema
psql "$SUPABASE_DB_URL" -c '\d private_knowledge'

# 看某 skill 設定
psql "$SUPABASE_DB_URL" -c "select * from ai_skills where skill_id = 'general_chat';"

# 看最近 10 則對話
psql "$SUPABASE_DB_URL" -c "
  select direction, left(message_text, 50) as preview, created_at
  from line_messages
  order by created_at desc
  limit 10;
"

# 看哪些 category 有資料
psql "$SUPABASE_DB_URL" -c "
  select category, count(*) as n
  from private_knowledge
  group by category
  order by n desc;
"
```

### 7-2 改資料（小心）

```bash
# 暫時下架 skill
psql "$SUPABASE_DB_URL" -c "update ai_skills set enabled = false where skill_id = 'general_chat';"

# 改某個 chunk 的 category（例如重分類）
psql "$SUPABASE_DB_URL" -c "
  update private_knowledge
  set category = 'pharmacy'
  where id = 'XXX-XXX-XXX';
"

# 把某個 source 的所有 chunk 砍掉
psql "$SUPABASE_DB_URL" -c "delete from private_knowledge where source_id = 'old_doc_v1';"
```

> ⚠️ **production 操作前**：先 `select` 確認 affected row 數量，再執行 `update` / `delete`。

### 7-3 ✏️ 改成你的需求：重設整個 KB（測試環境）

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
-- 砍掉所有 chunk，重新從 ingest 跑
truncate private_knowledge restart identity cascade;

-- 砍掉所有對話歷史 + log
truncate line_messages, retrieval_logs;

-- 砍 cache（如果有）
truncate prompt_cache;
SQL
```

> ⚠️ `truncate ... cascade` 會連 FK reference 都清，比 `delete` 快很多。**只在測試環境用**。

### 7-4 ✏️ 改成你的需求：備份再操作

```bash
# 操作前先 dump 一份
pg_dump "$SUPABASE_DB_URL" -t private_knowledge > backup_$(date +%Y%m%d).sql

# 出事可以還原
psql "$SUPABASE_DB_URL" -c "truncate private_knowledge;"
psql "$SUPABASE_DB_URL" -f backup_20251201.sql
```

---

## Step 8：實務 B — `knowledge_version` 更新讓 cache 自動失效

### 8-1 流程總覽

[Ch 01 Step 3](ch01-supabase-schema.md#step-3讀懂-private_knowledge加一個自訂欄位) + [Step 5-3](#5-3-get_knowledge_version-的-60-秒-ttl-cache) 已經看過機制。完整流程：

```
1. ingest 新資料 → 寫 private_knowledge，knowledge_version 設成 (max + 1)
2. cache_repo.get_knowledge_version() 過 60 秒 TTL 後，重新撈到新 version
3. 下次 query 算 cache_key 用新 version → 跟舊 cache 對不上 → cache miss
4. 重新走 LLM → set 新 cache（key 含新 version）
```

### 8-2 手動更新版本（ingest 之外）

如果你直接在 DB 改了某筆資料，想讓 cache 失效：

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
-- 把全表 version 推到下一個
update private_knowledge
set knowledge_version = (select coalesce(max(knowledge_version), 0) + 1 from private_knowledge);
SQL
```

最壞情況等 60 秒，所有 cache 失效。

### 8-3 ✏️ 改成你的需求：per-category version

預設全表共用一個 version——任一筆 chunk 變動，全 KB 的 cache 都會失效。如果你的 KB 很大，想要更細粒度：

```sql
-- 改 schema：knowledge_version 改成 per-category
alter table private_knowledge add column category_version integer default 1;

-- 加 index
create index private_knowledge_cat_ver_idx on private_knowledge(category, category_version);
```

然後改 `cache_repo.build_cache_key` 把 `category` 也納入：

```python
def build_cache_key(*, skill_id, category, category_version, user_input):
    payload = f"{skill_id}:{category}:{category_version}:{_normalize(user_input)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

這樣 `medical` category 更新不會打掉 `general` category 的 cache。

代價是 cache_repo 邏輯變複雜（要先知道 query 屬於哪個 category）。值不值得看你的 KB 規模。

---

## Step 9：實務 C — Supabase CLI 與 migration 策略

### 9-1 為什麼這個專案不用 supabase migrations？

本專案直接用裸 SQL 檔（`schema.sql` / `functions.sql` / `seed.sql`）+ idempotent 寫法（`if not exists` / `on conflict do update`），不用 Supabase 的 migration 系統。原因：

- 教學情境下，學生環境千差萬別，純 SQL 更可預測
- `if not exists` 讓重跑安全，沒有「migration history 對不上」的痛
- 缺點：無法 track 變更歷史。production 規模時需要補

### 9-2 Supabase CLI 對本地 ↔ 遠端

如果你還是想用 CLI（推薦給 production 場景）：

```bash
# 安裝
brew install supabase/tap/supabase

# 在專案根目錄 init
supabase init

# Link 到 Supabase 專案
supabase link --project-ref [YOUR-PROJECT-REF]

# 把遠端 schema dump 下來
supabase db pull

# 本地改完 push 上去
supabase db push
```

### 9-3 ✏️ 改成你的需求：把純 SQL 轉成 migration

假設你要進入 production，想要正式 migration history：

```bash
mkdir -p supabase/migrations

# 把現有 schema.sql 變成第一個 migration
cp supabase/schema.sql supabase/migrations/20251201000001_initial_schema.sql
cp supabase/functions.sql supabase/migrations/20251201000002_match_private_knowledge.sql

# 之後每次改 schema 都建新 migration
# 例如加 language 欄位
cat > supabase/migrations/20251215000001_add_language_column.sql <<'SQL'
alter table private_knowledge
add column if not exists language text;

update private_knowledge
set language = 'zh-TW'
where language is null;
SQL

# Apply
supabase db push
```

注意：CLI migration 系統會記錄哪些 migration 跑過，不會重跑。如果你還是想保留 idempotent，每個 migration 內仍要寫 `if not exists`。

### 9-4 不用 CLI 的最小 migration 模式

如果你不想引入 CLI，可以自己做最小版：

```
supabase/
├── schema.sql           # 初始版本（idempotent）
├── functions.sql        # 初始 RPC（idempotent）
├── seed.sql             # 種子（idempotent）
└── patches/             # 後續變更
    ├── 001_add_language.sql
    ├── 002_add_per_category_version.sql
    └── ...
```

跑 patch：

```bash
for f in supabase/patches/*.sql; do
  psql "$SUPABASE_DB_URL" -f "$f"
done
```

每個 patch 寫成 idempotent（`if not exists` / `if exists`），任意次數重跑都安全。簡單夠用。

---

## 🎯 本章驗收

### Step 1：跑 application code 確認 RuntimeServices 能建起來

```bash
# 從專案根目錄
poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services

async def main():
    settings = Settings()
    services = await build_runtime_services(settings)
    print("✅ services built")
    print("  knowledge_repo:", type(services.rag_graph).__name__ if hasattr(services, "rag_graph") else "n/a")

asyncio.run(main())
'
```

預期：`✅ services built`。如果出錯，看訊息 debug `.env` 設定。

### Step 2：用 Python 打 KnowledgeRepository（不透過 LINE）

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient
from app.storage.knowledge_repo import KnowledgeRepository

async def main():
    settings = Settings()
    client = SupabaseRestClient(settings)
    repo = KnowledgeRepository(client)

    # 用 dummy embedding 測連線
    chunks = await repo.match_private_knowledge(
        query_embedding=[0.1] * 1536,
        query_text="測試",
        top_k=3,
    )
    print(f"✅ retrieved {len(chunks)} chunks")
    for c in chunks[:3]:
        print(f"  {c.title} (score={c.combined_score:.3f})")

asyncio.run(main())
'
```

預期：看到 retrieved 數量 + 幾筆 title（如果 DB 有資料）。

### Step 3：寫一筆 message 看 messages_repo 通

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient
from app.storage.messages_repo import MessagesRepository

async def main():
    repo = MessagesRepository(SupabaseRestClient(Settings()))
    await repo.save_message(
        line_user_id="test-user",
        direction="inbound",
        message_text="hello from ch02 test",
    )
    history = await repo.build_recent_history("test-user", limit=3)
    print(history)

asyncio.run(main())
'
```

```bash
# 確認寫進去了
psql "$SUPABASE_DB_URL" -c "select direction, message_text from line_messages where line_user_id = 'test-user';"

# 清掉測試資料
psql "$SUPABASE_DB_URL" -c "delete from line_messages where line_user_id = 'test-user';"
```

### Step 4：cache_repo TTL 行為

```bash
poetry run python -c '
import asyncio, time
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient
from app.storage.cache_repo import CacheRepository

async def main():
    repo = CacheRepository(SupabaseRestClient(Settings()), version_ttl_seconds=2)

    v1 = await repo.get_knowledge_version()
    print(f"first call: version={v1} (took remote)")

    v2 = await repo.get_knowledge_version()
    print(f"second call: version={v2} (from TTL cache)")

    time.sleep(3)
    v3 = await repo.get_knowledge_version()
    print(f"after TTL expire: version={v3} (took remote again)")

asyncio.run(main())
'
```

預期：第二次 instant、第三次 sleep 後又有 latency。

### Step 5：（選擇性）切換 store 看是否能換

`.env` 改 `KNOWLEDGE_STORE=sqlite_vec`，跑 Step 1，看 RuntimeServices 是否能建起來。能 = abstraction 通。

---

## 下一章

[Ch 03：Channel 抽象與 LINE Webhook](ch03-channel-webhook.md) — 把這層 storage 接到外面世界：LINE、HTTP、Stub 三種入口共用同一份 graph。
