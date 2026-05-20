# Ch 10：Checkpoint / Cache / 成本 / 部署清單 / 地雷集

> 核心檔案：[`app/graph/checkpoint.py`](../../app/graph/checkpoint.py)、[`app/storage/cache_repo.py`](../../app/storage/cache_repo.py)、[`app/generator/responder.py`](../../app/generator/responder.py)
>
> Variant 適用性：**全部三個** — 上線前最後一哩

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 看 `build_checkpointer`：三種後端何時用哪個 |
| 2 | 看 `build_sqlite_saver_async` / `build_postgres_saver_async`：async lifespan 整合 |
| 3 | 啟用 prompt cache：knowledge_version 失效機制完整流程 |
| 4 | 看 ResponseGenerator 的 cache hit / miss 邏輯 |
| 5 | ✏️ 加成本預算斷路器 |
| 6 | 部署前 smoke test 清單 |
| 7 | Golden cases 回歸測試 |
| 8 | 12 條地雷集（每條附 app/ 防禦碼） |
| 9 | 完整 production 架構圖（升級版） |

---

## Step 1：`build_checkpointer` — 三種後端

打開 [`app/graph/checkpoint.py`](../../app/graph/checkpoint.py)：

```python
def build_checkpointer(settings: Settings) -> Any | None:
    backend = settings.checkpoint_backend
    if backend in ("none", ""):
        return None
    if backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver
        return InMemorySaver()
    if backend == "sqlite":
        logger.warning("checkpoint_backend=sqlite needs async setup; ...")
        return None
    if backend == "postgres":
        logger.warning("checkpoint_backend=postgres needs async setup; ...")
        return None
    raise ValueError(f"unknown checkpoint_backend: {backend!r}")
```

### 1-1 三種後端對照

| Backend | 適用 | 持久化 | 啟動 |
|---------|------|--------|------|
| `none` | 不需 HITL 也不需復原 | 無 | 同步 |
| `memory` | 教學 / 測試 | 重啟丟失 | 同步 |
| `sqlite` | 單機 production | 本機 file | async setup |
| `postgres` | 多 instance production | Supabase | async setup |

### 1-2 設定

```bash
# .env

# 開發機，每次重啟乾淨
CHECKPOINT_BACKEND=memory

# 單機 production
CHECKPOINT_BACKEND=sqlite
CHECKPOINT_SQLITE_PATH=./data/checkpoints.db

# 多 instance（Cloud Run / k8s）
CHECKPOINT_BACKEND=postgres
# 用 supabase_db_url
```

### 1-3 ✏️ 改成你的需求：HITL 場景必須選持久後端

[Ch 08 §8-5](ch08-judge-hitl.md#8-5-啟用-hitl-需要-checkpointer) 提到：HITL interrupt 需要 checkpointer。但選 `memory` 在多 instance 環境下 interrupt 後 resume 可能撞到不同 instance，state 拿不到。

production HITL 場景必須選 `sqlite`（單機）或 `postgres`（多 instance）。

---

## Step 2：async setup — FastAPI lifespan

sqlite 與 postgres 後端的建構是 async 的，必須在 FastAPI lifespan 內做。

### 2-1 看 `build_sqlite_saver_async`

```python
async def build_sqlite_saver_async(path: str) -> tuple[Any, Any]:
    """在 FastAPI startup（async context）建構 AsyncSqliteSaver。

    回傳 `(saver, conn)` — caller 必須在 shutdown 時 `await conn.close()`。
    """
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(path)
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    return saver, conn
```

回傳 `(saver, conn)` tuple——saver 用來建 graph，conn 要在 shutdown 時關閉避免 leak。

### 2-2 看 `build_postgres_saver_async`

```python
async def build_postgres_saver_async(conn_url: str) -> tuple[Any, Any]:
    """在 FastAPI startup（async context）建構 AsyncPostgresSaver。

    回傳 `(saver, cm)` tuple — caller 必須在 shutdown 時
    `await cm.__aexit__(None, None, None)` 才不會洩漏 postgres 連線。
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    cm = AsyncPostgresSaver.from_conn_string(conn_url)
    saver = await cm.__aenter__()
    await saver.setup()
    return saver, cm
```

postgres 多了一個 context manager 要關閉（`AsyncPostgresSaver.from_conn_string` 是 async context manager）。

### 2-3 整合到 FastAPI lifespan

[`app/main.py`](../../app/main.py) 應該長這樣（節錄）：

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import Settings
from app.dependencies import build_runtime_services
from app.graph.checkpoint import build_sqlite_saver_async, build_postgres_saver_async


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    services = await build_runtime_services(settings)

    # 處理 async checkpointer
    if settings.checkpoint_backend == "sqlite":
        saver, conn = await build_sqlite_saver_async(settings.checkpoint_sqlite_path)
        services.checkpointer = saver
        services._checkpoint_conn = conn
        # rebuild graph 以注入 checkpointer
        services.rag_graph = build_rag_graph(services)

    elif settings.checkpoint_backend == "postgres":
        saver, cm = await build_postgres_saver_async(settings.supabase_db_url)
        services.checkpointer = saver
        services._checkpoint_cm = cm
        services.rag_graph = build_rag_graph(services)

    app.state.services = services

    try:
        yield
    finally:
        # shutdown：關閉資源
        if hasattr(services, "_checkpoint_conn"):
            await services._checkpoint_conn.close()
        if hasattr(services, "_checkpoint_cm"):
            await services._checkpoint_cm.__aexit__(None, None, None)


app = FastAPI(lifespan=lifespan)
```

### 2-4 ✏️ 改成你的需求：用獨立 postgres（非 Supabase）

```bash
# .env
CHECKPOINT_BACKEND=postgres
SUPABASE_DB_URL=postgresql://...    # Supabase
CHECKPOINT_DB_URL=postgresql://...  # 獨立 postgres
```

```python
# main.py lifespan
elif settings.checkpoint_backend == "postgres":
    db_url = settings.checkpoint_db_url or settings.supabase_db_url
    saver, cm = await build_postgres_saver_async(db_url)
```

獨立 postgres 好處：checkpoint 流量不打 Supabase（保留給 RAG 用）；壞處：多一個維運點。

---

## Step 3：啟用 prompt cache（spec-05）

[Ch 01 §8-2](ch01-supabase-schema.md#8-2-prompt_cache--llm-回應快取) + [Ch 02 §5](ch02-repo-pattern.md#step-5讀懂-cacherepository) 已建好基礎。這節串完整流程。

### 3-1 啟用條件

`.env`：

```bash
PROMPT_CACHE_ENABLED=true
```

確認 schema 已套用 `prompt_cache` 表（schema.sql 已含）。

### 3-2 cache key 的三元組

```
cache_key = sha256(skill_id : knowledge_version : normalized_user_input)
```

三個元素都必須對齊才命中：

- **`skill_id`**：同 user_input 不同 skill 不共用（router 改判定就 miss）
- **`knowledge_version`**：知識更新就 miss
- **`normalized_user_input`**：去頭尾空白 + 小寫

### 3-3 失效時機

| 事件 | 失效範圍 |
|------|---------|
| Ingest 新文件 → `knowledge_version + 1` | 全部 cache（下次 lookup 用新 version 全 miss）|
| `update private_knowledge set knowledge_version = ...`（手動） | 全部 cache |
| Router 把同 query 路由到不同 skill | 該 query 在新 skill 下重新算 |
| User 改字（多打一個空白）| 同 query 但 normalize 不一致 → miss（已用 lower+strip 避免大部分） |

### 3-4 60 秒 TTL 的取捨

[Ch 02 §5-3](ch02-repo-pattern.md#5-3-get_knowledge_version-的-60-秒-ttl-cache) 詳述過——`get_knowledge_version()` 60 秒 TTL，平衡「lookup 延遲」與「ingest 後生效時間」。

如果你需要 ingest 立即生效（例如管理員改一筆，下一個請求就要新版）：

```bash
# .env
KNOWLEDGE_VERSION_TTL_SECONDS=1   # 1 秒
```

代價：每次 cache lookup 多一次 `select max(knowledge_version)` 來回。

---

## Step 4：ResponseGenerator 的 cache 邏輯

打開 [`app/generator/responder.py:28-88`](../../app/generator/responder.py#L28-L88)（basic variant 用 responder，selfrag/reflection 用 two-stage 但 cache 邏輯類似）：

```python
async def generate_response(self, *, user_input, router_result, skill, rag_chunks, rag_context, recent_history):
    if self.llm is None:
        return self._fallback_response(router_result, rag_chunks)

    # spec-05：is_rag_required=True 且 rag_chunks 非空才走快取
    cacheable = bool(
        self.cache_repo is not None
        and router_result.is_rag_required
        and rag_chunks
    )

    cache_key: str | None = None
    knowledge_version = 0
    if cacheable:
        knowledge_version = await self.cache_repo.get_knowledge_version()
        cache_key = build_cache_key(
            skill_id=skill.skill_id,
            knowledge_version=knowledge_version,
            user_input=user_input,
        )
        cached = await self.cache_repo.get(cache_key)
        if cached is not None:
            logger.info("prompt cache hit skill=%s version=%s key=%s",
                       skill.skill_id, knowledge_version, cache_key[:12])
            return split_for_line(cached, max_chars=self.line_max_message_chars)

    # miss → 正常生成
    prompt = render_synthesis_prompt(...)
    response_text = await self.llm.complete(prompt)

    if router_result.is_rag_required and not rag_chunks:
        response_text = f"目前知識庫沒有足夠資料。\n\n{response_text}".strip()

    if cacheable and cache_key is not None:
        await self.cache_repo.set(
            cache_key=cache_key,
            user_input=user_input,
            skill_id=skill.skill_id,
            knowledge_version=knowledge_version,
            response_text=response_text,
        )

    return split_for_line(response_text, max_chars=self.line_max_message_chars)
```

### 4-1 `cacheable` 的三個條件

```python
cacheable = bool(
    self.cache_repo is not None    # 1. cache 有啟用
    and router_result.is_rag_required  # 2. RAG 需要的（純閒聊不快取）
    and rag_chunks                 # 3. 有撈到 chunks（沒撈到的別快取錯誤）
)
```

第 3 點關鍵：**「目前知識庫沒有足夠資料」這種回覆不該被快取**——下次 ingest 後可能就有資料了。

### 4-2 hit log 為什麼只印前 12 字

```python
logger.info("prompt cache hit skill=%s version=%s key=%s",
           skill.skill_id, knowledge_version, cache_key[:12])
```

整個 sha256 hash 64 字太長，前 12 字夠 debug 對照（用 `select ... where cache_key like '前12字%'` 撈完整 row）。

### 4-3 ✏️ 觀測 cache hit rate

加個 metric：

```python
# app/generator/responder.py
class ResponseGenerator:
    cache_hits: int = 0
    cache_misses: int = 0

    async def generate_response(self, ...):
        # ...
        if cached is not None:
            self.cache_hits += 1
            logger.info("prompt cache hit ...")
            return ...
        else:
            self.cache_misses += 1
```

開個 admin endpoint 看：

```python
@router.get("/admin/cache-stats")
async def cache_stats(services: RuntimeServices = Depends(get_runtime_services)):
    g = services.responder
    return {
        "hits": g.cache_hits,
        "misses": g.cache_misses,
        "hit_rate": g.cache_hits / max(g.cache_hits + g.cache_misses, 1),
    }
```

健康的 cache hit rate 通常 30-60%。<10% 表示 cache key 設計不對（user_input 變化太多）。

---

## Step 5：✏️ 加成本預算斷路器

目前 graph 沒有 cost budget 機制——理論上一個 retry 風暴可能燒掉幾美金。手動補：

### 5-1 在 state 加欄位

```python
# app/graph/state.py
class RAGState(TypedDict, total=False):
    # ... 既有
    total_cost_usd: float
    budget_cutoff_usd: float
```

### 5-2 在 graph 各 LLM-heavy node 之間插一個 budget_guard_node

```python
# app/graph/nodes.py
@traced("budget_guard")
async def budget_guard_node(state, services) -> dict:
    """檢查累積成本是否超預算。"""
    tracer = get_current_tracer()
    if tracer is None:
        return {}

    current_cost = tracer.total_cost_usd
    budget = state.get("budget_cutoff_usd") or services.settings.default_budget_cutoff_usd

    if current_cost > budget:
        logger.warning("budget exceeded: $%.4f > $%.4f", current_cost, budget)
        return {
            "blocked": True,
            "blocked_reason": "budget_exceeded",
            "responses": [f"⚠️ 本次處理已達成本上限 (${budget})，已停止以避免異常開銷。"],
        }
    return {"total_cost_usd": current_cost}
```

### 5-3 在 graph 上掛

```python
# reflection.py
g.add_node("budget_guard", partial(budget_guard_node, services=services))

# 在 retry loop 之前加一道 budget check
g.add_edge("increment_retry", "budget_guard")
g.add_conditional_edges(
    "budget_guard",
    lambda s: "blocked" if s.get("blocked") else "continue",
    {"blocked": "mark_warning", "continue": "render_narrative"},
)
```

### 5-4 設預算

```bash
# .env
DEFAULT_BUDGET_CUTOFF_USD=0.05    # 每次 invocation 最多花 5 美分
```

可以為高風險領域設更低，例如客服 bot：

```bash
DEFAULT_BUDGET_CUTOFF_USD=0.02
```

---

## Step 6：部署前 smoke test 清單

```bash
#!/bin/bash
# scripts/smoke_test.sh

set -e

echo "=== 1. 環境變數 ==="
for var in SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY OPENAI_API_KEY LINE_CHANNEL_SECRET LINE_CHANNEL_ACCESS_TOKEN; do
    if [ -z "${!var}" ]; then
        echo "❌ $var unset"; exit 1
    else
        echo "✅ $var set"
    fi
done

echo "=== 2. Supabase 連線 ==="
psql "$SUPABASE_DB_URL" -c "select 1" > /dev/null && echo "✅ DB connect" || (echo "❌ DB"; exit 1)

echo "=== 3. Schema 完整 ==="
for t in ai_skills private_knowledge line_messages retrieval_logs prompt_cache; do
    psql "$SUPABASE_DB_URL" -c "\\d $t" > /dev/null 2>&1 && echo "✅ table $t" || (echo "❌ missing $t"; exit 1)
done

echo "=== 4. RPC 存在 ==="
psql "$SUPABASE_DB_URL" -c '\df match_private_knowledge' | grep -q match_private_knowledge && echo "✅ RPC" || (echo "❌ RPC"; exit 1)

echo "=== 5. 至少一筆 skill ==="
count=$(psql "$SUPABASE_DB_URL" -t -c "select count(*) from ai_skills where enabled = true;" | xargs)
if [ "$count" -gt 0 ]; then echo "✅ $count skills enabled"; else echo "❌ no skills"; exit 1; fi

echo "=== 6. 至少一筆 knowledge ==="
count=$(psql "$SUPABASE_DB_URL" -t -c "select count(*) from private_knowledge;" | xargs)
if [ "$count" -gt 0 ]; then echo "✅ $count chunks"; else echo "⚠️ no knowledge (ingest 才能 RAG)"; fi

echo "=== 7. LLM 通 ==="
poetry run python -c '
import asyncio
from app.config import Settings
from app.ai.factory import build_llm

async def main():
    llm = build_llm(Settings(), role="router")
    out = await llm.complete("回應這個字: OK")
    print("✅ LLM:", out[:50])

asyncio.run(main())
' || (echo "❌ LLM"; exit 1)

echo "=== 8. graph 跑通（stub channel）==="
poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    services = await build_runtime_services(Settings())
    inp = ChannelInput(channel="stub", external_user_id="U_demo_smoke",
                       external_message_id="smoke_test", raw_text="你好")
    await process_channel_input(inp, services)
    stub = services.channels["stub"]
    assert stub.pushed, "no response pushed"
    print("✅ graph:", stub.pushed[0][1][0][:50])

asyncio.run(main())
'

echo ""
echo "🎉 All smoke tests passed!"
```

跑：

```bash
bash scripts/smoke_test.sh
```

每次 deploy 之前跑一次。也可以掛 CI。

---

## Step 7：Golden cases 回歸測試（app/eval/ 完整框架）

[`app/eval/`](../../app/eval/) 提供完整 eval framework，分四個檔：

| 檔案 | 角色 |
|------|------|
| [`schema.py`](../../app/eval/schema.py) | `GoldenCase` / `GoldenCaseSet` Pydantic schema + YAML 載入 |
| [`metrics.py`](../../app/eval/metrics.py) | 4 個純函式 metric（無 LLM） |
| [`runner.py`](../../app/eval/runner.py) | 跑 cases 對三 variants 出結果 |
| [`retrieval_analytics.py`](../../app/eval/retrieval_analytics.py) | retrieval_logs 聚合分析（給 scripts/analyze_retrieval.py 用） |

### 7-1 `GoldenCase` schema

```python
# app/eval/schema.py:15-27
class GoldenCase(BaseModel):
    id: str
    query: str
    category: str | None = None
    expected_chunks: list[str] = []      # chunk_id 應命中清單
    must_cite_sources: list[str] = []    # 回覆必須引用的 source 子字串
    forbidden_phrases: list[str] = []    # 回覆禁止出現的字串
    expect_clarification: bool = False
    notes: str = ""
```

### 7-2 範例 `tests/cases/golden.yaml`

```yaml
- id: "tcm_pulse_001"
  query: "脈象浮數代表什麼？"
  category: "tcm"
  expected_chunks: ["chunk-uuid-001", "chunk-uuid-002"]
  must_cite_sources: ["脈經", "傷寒論"]
  forbidden_phrases: ["診斷", "處方"]
  notes: "脈象問題不該變診斷建議"

- id: "engineer_hnsw_001"
  query: "Supabase HNSW 怎麼設 lists？"
  category: "engineering"
  expected_chunks: ["chunk-uuid-101"]
  must_cite_sources: ["pgvector"]

- id: "gap_001"
  query: "火星上的稅務"
  expect_clarification: true   # 應該追問而非硬編
  notes: "KB 無資料的 case"

- id: "hallucination_001"
  query: "Linus Torvalds 是誰？"
  expected_chunks: []          # 故意沒有 expected
  forbidden_phrases: ["創辦 Microsoft"]   # 抓常見幻覺
  notes: "易誘發 hallucination 的案例"
```

### 7-3 四個 metrics 各自管什麼

[`app/eval/metrics.py`](../../app/eval/metrics.py) 全是純函式，0 個 LLM call：

| Metric | 在算什麼 | 為 None 代表 |
|--------|---------|-------------|
| `chunk_recall_at_k` | `expected_chunks` 中有幾個出現在 retrieved | case 沒指定 expected_chunks |
| `citation_accuracy` | 回覆引用的 chunk_id 是否都在 retrieved 集合內（無杜撰） | 回覆沒引用任何 chunk |
| `forbidden_phrase_hit` | 回覆是否出現禁用詞 | 永遠回 bool |
| `must_cite_satisfied` | 回覆是否至少引用了 must_cite_sources 之一 | case 沒指定 must_cite |

`None` 代表「**不適用**」，aggregate 時會排除這個 case，不會把 metric 拉低。

### 7-4 `EvalRunner` 怎麼跑

[`app/eval/runner.py:37-122`](../../app/eval/runner.py#L37-L122) 的 `EvalRunner.run_case`：

```python
async def run_case(self, case: GoldenCase, variant: str) -> EvalResult:
    builder = VARIANT_BUILDERS[variant]
    graph = builder(self._services)   # 切 variant 要重建 graph

    final = await graph.ainvoke({
        "user_input": case.query,
        "external_user_id": f"U_eval_{case.id}",   # 觸發 dry_run
        "recent_history": "",
        "dry_run": True,
    })

    retrieved = final.get("rag_chunks") or []
    responses = final.get("responses") or []
    contract = final.get("answer_contract")

    # 算四個 metric + judge_passed + latency
    return EvalResult(
        case_id=case.id, variant=variant,
        chunk_recall=chunk_recall_at_k(case, retrieved),
        citation_accuracy=citation_accuracy(retrieved, [c.chunk_id for c in contract.citations] if contract else []),
        ...
    )
```

關鍵：

- **每個 variant 都 rebuild graph**——不污染 production graph 實例
- **`external_user_id` 用 `U_eval_*` 前綴**——觸發 [Ch 03 §4-2](ch03-channel-webhook.md#4-2-幾個關鍵設計) 的 dry_run，不寫真實 message log
- **`failure_reasons`** 列出本 case 沒過的原因，aggregate 時可以看哪些 case 失敗

### 7-5 `failure_reasons` 的細節判定

```python
# runner.py:82-99
failures: list[str] = []
if case.expect_clarification and not went_to_clarify:
    failures.append("expected clarify but went to generate")
if (not case.expect_clarification
    and went_to_clarify
    and case.expected_chunks):   # 只有「應該找到 chunks」的 case 才檢查
    failures.append("unexpected clarify (case has chunks but graph asked to clarify)")
if forbidden_hit:
    failures.append(f"hit forbidden phrase: {case.forbidden_phrases}")
if cite_satisfied is False and variant != "basic":
    failures.append(f"missing required citation: {case.must_cite_sources}")
```

注意第二條與最後一條的 **「只有特定情境才算 failure」** 設計——避免「對 basic variant 強求 citation」這種錯誤誤判。

### 7-6 跑 eval — 用既有 `scripts/eval.py`

scripts 已備好，直接跑：

```bash
# 跑全部 golden cases × 三 variants
poetry run python scripts/eval.py

# 指定 cases 檔
poetry run python scripts/eval.py --cases tests/cases/golden.yaml

# 只測 reflection variant
poetry run python scripts/eval.py --variants reflection

# 只跑特定 case
poetry run python scripts/eval.py --case-id tcm_pulse_001,gap_001

# 快速模式（前 3 個 case）
poetry run python scripts/eval.py --quick

# 出 JSON 給 CI 用
poetry run python scripts/eval.py --output baseline.json --format json
```

### 7-7 aggregate 輸出

`EvalRunner.aggregate(results)` 對每 variant 出統計：

```python
{
  "basic": {
    "n": 12,
    "chunk_recall_avg": 0.65,
    "citation_accuracy_avg": None,    # ← basic variant 不產 AnswerContract、無 citation → None
    "forbidden_phrase_rate": 0.083,   # 8.3% 的 case 觸到 forbidden 詞
    "clarification_rate": 0.0,        # basic 沒 sufficiency 機制 → 永遠不會 clarify
    "judge_pass_rate": None,          # ← basic 沒 judge node → None
    "latency_ms_median": 1450,
    "failed": ["gap_001"]             # 1 個 case 進 failure_reasons
  },
  "selfrag": {...},                   # selfrag 有 contract、clarify，但無 judge → judge_pass_rate=None
  "reflection": {
    "n": 12, "chunk_recall_avg": 0.71, "citation_accuracy_avg": 0.94,
    "forbidden_phrase_rate": 0.0, "clarification_rate": 0.083,
    "judge_pass_rate": 0.91,          # ← 12 個 case 中 11 個 judge 通過
    "latency_ms_median": 3200, "failed": []
  }
}
```

幾個欄位為何可能是 `None`：

| 欄位 | None 代表 |
|------|----------|
| `chunk_recall_avg` | 該 variant 內所有 case 都沒設 `expected_chunks` |
| `citation_accuracy_avg` | basic variant 不產 contract（無 citation 可比對）、或所有 case 都沒引用 |
| `judge_pass_rate` | basic / selfrag 沒跑 judge node |

`None` 表示「**不適用**」，不是 0 分——做 baseline 對比時要把 None 排除。

每次重大改動（換 model、改 fusion、改 router prompt）跑一次，對比 baseline 看回歸是否還過。

### 7-8 ✏️ 加自己的 metric

假設你要算「答案長度」是否合理：

```python
# app/eval/metrics.py 加
def response_length_in_range(response_text: str, min_chars: int, max_chars: int) -> bool:
    return min_chars <= len(response_text) <= max_chars
```

在 `EvalResult` 加欄位、在 `EvalRunner.run_case` 算進去、在 `aggregate` 統計。

### 7-9 retrieval_logs 分析（不同主題）

`app/eval/retrieval_analytics.py` 是另一條軸——分析**正式運行中的 retrieval_logs**（vs golden case 評估）。三個聚合函式：

| 函式 | 在問什麼 |
|------|---------|
| `aggregate_empty_hits` | 哪些 query 完全沒撈到 chunks？（KB 缺洞訊號） |
| `aggregate_low_score` | 撈到但分數普遍偏低的 query（retrieval 品質訊號） |
| `aggregate_category_stats` | 各 category 的命中量與平均分（KB 健康度） |

CLI 入口已備好：

```bash
# KB 缺洞排行
poetry run python scripts/analyze_retrieval.py --empty-hits --days 7

# 低分檢索
poetry run python scripts/analyze_retrieval.py --low-score --threshold 0.3 --days 7

# 按 category 分佈
poetry run python scripts/analyze_retrieval.py --category-stats --days 30

# 看某個 query 的歷史
poetry run python scripts/analyze_retrieval.py --query "LangGraph 是什麼"
```

eval 是「golden case 看回歸」、analytics 是「真實流量看趨勢」——兩條軸互補。

---

## Step 8：12 條地雷集

每條附 app/ 中的防禦碼或對應檔案。

### 🪤 地雷 1：Decision 用自由文字
LLM 某天回 `"REWRITE"`、某天回 `"rewrite the query"`，router 崩。
→ **防禦**：[`app/router/schemas.py`](../../app/router/schemas.py) 用 `Literal` 鎖死 + `_normalize_result` 過濾。

### 🪤 地雷 2：忘記 max_attempts
無限迴圈、帳單爆掉。
→ **防禦**：[`app/graph/nodes.py:344-363`](../../app/graph/nodes.py#L344-L363) `make_route_after_judge` 用 `HARD_MAX=2` 雙重保險。

### 🪤 地雷 3：InMemorySaver 上 production
重啟就沒了。HITL 完全失效。
→ **防禦**：[`app/graph/checkpoint.py`](../../app/graph/checkpoint.py) 三後端切換 + lifespan async setup。

### 🪤 地雷 4：把 routing 邏輯放進 LLM prompt
模型自己判斷要走哪。一次失敗整條崩。
→ **防禦**：[`app/router/intent_router.py`](../../app/router/intent_router.py) LLM 只回結構化 JSON，分支由 graph routing function 做。

### 🪤 地雷 5：Reflect 順便改答案
責任爆炸，很難 audit。
→ **防禦**：[`app/judge/scorer.py`](../../app/judge/scorer.py) 純評分，不碰 narrative。改答案由 retry → render_narrative 做。

### 🪤 地雷 6：retrieved_docs 直接塞 JSON 給模型
格式太亂，judge 對不上 citation。
→ **防禦**：[`app/generator/contract.py`](../../app/generator/contract.py) 兩階段——Contract 純程式組、narrative 受限 LLM 引用。

### 🪤 地雷 7：節點偷用全域變數
Checkpoint 還原失敗。
→ **防禦**：所有跨節點狀態都進 [`app/graph/state.py`](../../app/graph/state.py) 的 `RAGState`。觀測層用 [`tracer.py`](../../app/observability/tracer.py) 的 ContextVar（透過 asyncio task 隱式傳遞）。

### 🪤 地雷 8：Vector 查詢忘記 `::vector` 轉型
PostgreSQL 報錯 `operator does not exist`。
→ **防禦**：[`supabase/functions.sql`](../../supabase/functions.sql) 把所有 vector cast 封裝在 RPC 裡，Python 端不用碰。

### 🪤 地雷 9：沒有 retrieval_history / route_history
系統一直查同樣 query / debug 看不到走過哪些 node。
→ **防禦**：每次 retrieve 透過 [`logs_repo.log_retrieval`](../../app/storage/logs_repo.py)，每次 graph invocation 透過 [`tracer.py`](../../app/observability/tracer.py) 的 events。

### 🪤 地雷 10：LLM 失敗整條崩
任何一個 LLM 節點掛掉 → 整次請求失敗。
→ **防禦**：每個 LLM-using 節點都有 graceful degrade：
- Router → heuristic fallback（[`intent_router.py`](../../app/router/intent_router.py)）
- Feature extractor → `_fallback`（[`feature_extractor.py`](../../app/graph/feature_extractor.py)）
- Query transform → 回原 query（[`query_transform.py`](../../app/graph/query_transform.py)）
- Clarifier → `_FALLBACK_QUESTIONS`（[`clarifier.py`](../../app/graph/clarifier.py)）
- Narrative → `_fallback_render` 模板（[`narrative.py`](../../app/generator/narrative.py)）
- Judge → 視為 pass（[`scorer.py`](../../app/judge/scorer.py)）
- Reranker → 回 score 排序（[`reranker.py`](../../app/rag/reranker.py)）

### 🪤 地雷 11：cache 沒帶 knowledge_version
ingest 後使用者一直拿到舊答案。
→ **防禦**：[`app/storage/cache_repo.py`](../../app/storage/cache_repo.py) `build_cache_key` 把 `knowledge_version` 編進 key，schema 強制存欄位（[`schema.sql:97`](../../supabase/schema.sql#L97)）。

### 🪤 地雷 12：trace 寫滿磁碟
`.traces/*.json` 每次都寫，沒清理就吃滿 disk。
→ **防禦**：
- 開發環境定期 `rm -rf .traces/*.json`
- production 用 `OBSERVABILITY_PERSIST=true` 寫到 Supabase `graph_traces`，本機停寫
- 加 cron 清舊 trace：`find .traces -mtime +7 -delete`

---

## Step 9：完整 production 架構圖（升級版）

```
╔════════════════════════════════════════════════════════════════════╗
║                          External Entry                             ║
║  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  ║
║  │  LINE       │  │   HTTP /     │  │  Telegram    │  │  Web    │  ║
║  │  Webhook    │  │   API        │  │  (custom)    │  │  UI     │  ║
║  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └────┬────┘  ║
╚═════════│════════════════│══════════════════│═══════════════│══════╝
          ↓                ↓                  ↓               ↓
    ┌─────────────────────────────────────────────────────────────┐
    │      Channel Layer (app/channels/)                          │
    │  parse_request → ChannelInput → build_thread_id             │
    └────────────────────────────┬────────────────────────────────┘
                                 ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ process_channel_input (app/line/webhook.py)                 │
    │  + tracer.start                                             │
    │  + messages_repo.save_message (inbound)                     │
    │  + graph.ainvoke(state, config={thread_id})                 │
    │  + interrupt 偵測 → mark_pending_review                     │
    │  + messages_repo.save_message (outbound)                    │
    └────────────────────────────┬────────────────────────────────┘
                                 ↓
    ┌─────────────────────────────────────────────────────────────┐
    │  LangGraph (app/graph/variants/reflection.py)               │
    │                                                              │
    │  input_guard ──┬──→ blocked → push                          │
    │                │                                             │
    │                └──→ route (LLM + heuristic fallback)        │
    │                        ↓                                     │
    │                     query_transform (hyde/step-back/...)    │
    │                        ↓                                     │
    │                     extract_features (LLM + fallback)       │
    │                        ↓                                     │
    │                     expand_seeds                            │
    │                        ↓                                     │
    │           [fan-out] retrieve_one × N                        │
    │                        ↓                                     │
    │                     fuse_scores (max/mean/rrf)              │
    │                        ↓                                     │
    │                     rerank (cohere/bge + degrade)           │
    │                        ↓                                     │
    │                     check_sufficiency ──insuf──→ clarify   │
    │                        │                          │         │
    │                        └─sufficient──→ build_answer_contract│
    │                                        ↓                     │
    │                                    render_narrative          │
    │                                        ↓                     │
    │                                      judge ──pass──→ push   │
    │                                        │                     │
    │                                        ├──retry──→ inc_retry │
    │                                        │            ↑        │
    │                                        │            └────────┘
    │                                        │                     │
    │                                        └──hitl/force─→ ...   │
    └─────────────────────┬───────────────────────────────────────┘
                          ↓
            ┌────────────────────────────┐  ┌─────────────────────┐
            │  Storage (Supabase REST)   │  │   LLM Providers     │
            │  ─ knowledge_repo (RPC)    │  │  ─ openai           │
            │  ─ messages_repo (HITL)    │  │  ─ anthropic        │
            │  ─ logs_repo               │  │  ─ gemini           │
            │  ─ cache_repo (version)    │  │  ─ github_copilot   │
            │  ─ traces_repo (opt-in)    │  │  ─ huggingface      │
            └──────────┬─────────────────┘  └──────────┬──────────┘
                       ↓                                ↓
            ┌────────────────────────────────────────────────────┐
            │       Supabase Postgres + pgvector                  │
            │  ─ ai_skills        (DB-driven prompts)            │
            │  ─ private_knowledge (HNSW + tsvector + version)   │
            │  ─ line_messages    (inbound/outbound audit)       │
            │  ─ retrieval_logs   (per-retrieval forensic)       │
            │  ─ prompt_cache     (version-keyed)                │
            │  ─ hitl_pending_reviews (opt-in)                   │
            │  ─ graph_traces     (opt-in)                       │
            │  ─ match_private_knowledge() RPC                   │
            └────────────────────────────────────────────────────┘
                       │
                       ↓
            ┌────────────────────────────────────────────────────┐
            │  Observability (app/observability/)                 │
            │  ─ GraphTracer (ContextVar, per-invocation)         │
            │  ─ .traces/*.json (always)                          │
            │  ─ graph_traces (opt-in via OBSERVABILITY_PERSIST)  │
            │  ─ JSON logger (python-json-logger / fallback)      │
            │  ─ pricing.py (per-model USD/1M)                    │
            └────────────────────────────────────────────────────┘

                          Across all layers:
            ┌────────────────────────────────────────────────────┐
            │  Security (app/security/guards.py)                  │
            │  ─ Input: prompt injection (input_guard_node)       │
            │  ─ Output: PII redaction (output_guard, optional)   │
            │  ─ Ingest: RAG poison detection                     │
            └────────────────────────────────────────────────────┘
```

---

## 🎯 本章驗收

### Step 1：checkpoint backend 切換

```bash
# memory
CHECKPOINT_BACKEND=memory poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services

async def main():
    s = await build_runtime_services(Settings())
    print("checkpointer:", type(s.checkpointer).__name__ if s.checkpointer else "None")

asyncio.run(main())
'

# sqlite
CHECKPOINT_BACKEND=sqlite poetry run python -c '
# 注意：sqlite 需走 lifespan async setup，本 script 會印 None + warning
'
```

### Step 2：cache hit / miss

```bash
PROMPT_CACHE_ENABLED=true poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    services = await build_runtime_services(Settings())

    # 第一次 query
    inp = ChannelInput(channel="stub", external_user_id="U_demo_cache",
                       external_message_id="m1", raw_text="HNSW 怎麼設？")
    await process_channel_input(inp, services)
    print("first run done")

    # 第二次相同 query
    inp = ChannelInput(channel="stub", external_user_id="U_demo_cache",
                       external_message_id="m2", raw_text="HNSW 怎麼設？")
    await process_channel_input(inp, services)
    print("second run done — look for `prompt cache hit` in logs")

asyncio.run(main())
'
```

預期：第二次跑會在 log 看到 `prompt cache hit`。

### Step 3：smoke test

```bash
bash scripts/smoke_test.sh
```

預期：8 步全綠。

### Step 4：12 條地雷自我檢查

把上面 12 條對著你目前的 fork / 改動跑一遍：

```bash
# 隨機抽幾條驗
poetry run python -c "from app.router.schemas import SkillId; print('地雷 1: SkillId 是 Literal 嗎？', SkillId)"
poetry run python -c "from app.graph.nodes import make_route_after_judge; print('地雷 2: HARD_MAX 還在？', 'HARD_MAX = 2' in open('app/graph/nodes.py').read())"
poetry run python -c "from app.security.guards import detect_prompt_injection; print('地雷 4 防禦: input_guard 偵測:', detect_prompt_injection('ignore previous'))"
```

---

## 🎓 完課

恭喜你讀完 Lesson 5。回顧你建立了什麼：

1. ✅ Supabase schema + HNSW + hybrid RPC（[Ch 01](ch01-supabase-schema.md)）
2. ✅ Repo Pattern + 實務操作（[Ch 02](ch02-repo-pattern.md)）
3. ✅ Channel 抽象 + LINE webhook + multi-entry（[Ch 03](ch03-channel-webhook.md)）
4. ✅ Intent Router + Skills + DB-driven prompts（[Ch 04](ch04-router-skills.md)）
5. ✅ Feature Extraction + Query Transform（[Ch 05](ch05-query-understanding.md)）
6. ✅ Multi-seed Retrieval + Fusion + Rerank（[Ch 06](ch06-multi-seed-retrieval.md)）
7. ✅ Sufficiency + Clarifier + 兩階段生成（[Ch 07](ch07-sufficiency-generation.md)）
8. ✅ Judge + Reflection 迴圈 + HITL（[Ch 08](ch08-judge-hitl.md)）
9. ✅ Tracer + Pricing + Guards（[Ch 09](ch09-observability-security.md)）
10. ✅ Checkpoint + Cache + 部署清單 + 地雷集（本章）

## 三句話收斂

1. **LLM 負責想內容，Graph 負責管流程，Database 負責保留證據。**
2. **每個 LLM 節點都有降級路徑——沒有單點故障。**
3. **每次失敗都有 trace、有 log、有 metric，能事後重建現場。**

---

## 進階閱讀

- [`docs/specs/`](../specs/README.md)：本專案 32 個 spec 的設計決策完整紀錄
- [`docs/adr/`](../adr/README.md)：架構決策紀錄（ADR）
- [`docs/RAG/LangGraph/`](../RAG/LangGraph/README.md)：LangGraph 概念 10 章（教科書視角）
- [`docs/Lesson_3_LangGraph_RAG/`](../Lesson_3_LangGraph_RAG/README.md)：LangGraph 動手實作 8 章（介於概念與 production 之間）
- [`docs/Lesson_4_Build_Yours/`](../Lesson_4_Build_Yours/README.md)：換成你自己領域的 KB / skill / channel

> 「If your agent can't tell you why it failed, it's not production.」
