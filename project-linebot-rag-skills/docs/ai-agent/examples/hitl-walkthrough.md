# HITL（Human-in-the-Loop）走查

> 對應 [task-21](../tasks/task-21-persistence-hitl.md)、ch06 §3「高風險領域 Reflection Agent + human_review」承諾。

## 何時啟用

| 情境 | 是否啟用 HITL |
|---|---|
| 教學 demo / 一般 RAG | ❌（預設 `hitl_enabled=False`，retry 用盡走 `mark_warning + ⚠️`）|
| 高風險領域（醫療 / 法規 / 金融）| ✅（`hitl_enabled=True`，retry 用盡走 `human_review` 中斷）|

## 啟用設定

`.env`：

```bash
HITL_ENABLED=true
CHECKPOINT_BACKEND=memory     # 教學用：跨 restart 不持久
# CHECKPOINT_BACKEND=sqlite   # 生產用：跨 restart 持久（需 pip install -e ".[hitl]"）
```

> ⚠️ **`hitl_enabled=True` 但 `checkpoint_backend=none` 會 raise**：HITL 需要 checkpointer 才能 interrupt + resume。

## 流程

```
LINE / Web 訊息
    ↓
graph 跑到 judge → 失敗 → retry → 仍失敗
    ↓
路由到 human_review → INTERRUPT
    ↓
graph 暫停，state 存在 checkpointer
LINE / Web 用戶端不收到任何訊息（push_node 還沒跑）
    ↓
管理員：python scripts/review_queue.py list
    ↓
管理員看 thread_id + judge 分數，選擇：
  - approve  → 推原 narrative
  - revise   → 推改後內容
  - drop     → 不推
    ↓
graph resume，push_node 依 reviewer_decision 動作
```

## 範例 session

### 1. 啟動 bot（HITL on）

```bash
HITL_ENABLED=true CHECKPOINT_BACKEND=memory ./scripts/run_local.sh
```

### 2. 用戶傳會觸發低分的訊息

LINE 用戶傳：「請列出 RAG 系統的所有評估指標」（forbidden phrases 案例）

預期 log：

```
INFO judge mean=4.5 pass=False issues=2
INFO reflection retry → 1
INFO judge mean=4.0 pass=False issues=2
INFO human_review entered: ...
```

→ 用戶 LINE **沒收到任何訊息**（graph interrupted）。

### 3. 管理員列出待審

```bash
python scripts/review_queue.py list
```

```
thread_id                                user                 judge_mean  query
----------------------------------------------------------------------------------------------------
line-U_xxx-evt_001                       U_xxx                       4.0  請列出 RAG 系統的所有評估指標
```

### 4. 看詳細

```bash
python scripts/review_queue.py show line-U_xxx-evt_001
```

```
thread:    line-U_xxx-evt_001
user:      U_xxx
query:     請列出 RAG 系統的所有評估指標
contract.summary: 關於「評估指標」的相關說明。
contract.findings: 4
contract.citations: 4
judge: ground=4 cite=4 format=4 uncert=4 mean=4.0
judge.issues: ['宣稱「所有」缺乏依據', '未誠實標示不確定']

narrative:
  **摘要**：...
  ...

next: ('human_review',)
```

### 5. 三種處置

```bash
# 批准 — 推原 narrative
python scripts/review_queue.py approve line-U_xxx-evt_001

# 改寫 — 推改後內容
python scripts/review_queue.py revise line-U_xxx-evt_001 \
  --text "RAG 評估指標包含 chunk_recall / citation_accuracy 等；本知識庫覆蓋的指標清單詳見 docs/RAG/ch06。"

# 撤回 — 不推
python scripts/review_queue.py drop line-U_xxx-evt_001
```

執行任一指令後，LINE 用戶才會收到對應結果（或不收到）。

## 教學重點

1. **interrupt_before vs interrupt()**：
   - 用 `interrupt_before=["human_review"]` 而非 `interrupt(...)`，因為 interrupt 應該是路徑性（走到 human_review 才中斷），不是動態決策性
   - `judge=pass` 路徑根本不路由到 human_review → 不會 interrupt
2. **thread_id 命名**：channel adapter 提供 `build_thread_id(input)`，命名格式 `{channel}-{user_id}-{message_id}` 確保跨 channel 不撞
3. **reviewer_decision 流通**：state 欄位 → checkpointer 序列化 → resume 時 push_node 讀
4. **`hitl_enabled=False` 時行為**：retry 用盡走 mark_warning（既有行為），與 hitl_enabled 路徑互不影響——這是「漸進啟用 HITL」的承諾

## 進階：sqlite 跨 restart 持久化

memory backend 在 process restart 後 thread state 會消失。要做真實的「白天累積、晚上人工 batch review」流程：

```bash
python -m pip install -e ".[hitl]"
```

`.env`：
```
CHECKPOINT_BACKEND=sqlite
```

**注意**：sqlite saver 用 AsyncSqliteSaver，需要在 FastAPI startup hook 內 async 設定。本專案教學版未提供完整 startup integration，學生需自行加：

```python
# app/main.py
from app.graph.checkpoint import build_sqlite_saver_async

@app.on_event("startup")
async def _setup_checkpointer():
    services = get_runtime_services()
    if services.settings.checkpoint_backend == "sqlite":
        services.checkpointer = await build_sqlite_saver_async(
            services.settings.checkpoint_sqlite_path
        )
        # 必須 rebuild graph 讓新 checkpointer 生效
        from app.graph.rag_graph import build_rag_graph
        services.rag_graph = build_rag_graph(services)
```

完成後，跨 process restart 也能 resume 任何待審 thread。
