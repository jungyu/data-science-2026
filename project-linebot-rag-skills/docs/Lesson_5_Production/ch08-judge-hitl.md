# Ch 08：Judge + Reflection 迴圈 + HITL

> 核心檔案：[`app/judge/scorer.py`](../../app/judge/scorer.py)、[`app/graph/variants/reflection.py`](../../app/graph/variants/reflection.py)、[`app/graph/nodes.py`](../../app/graph/nodes.py)
>
> Variant 適用性：**reflection 必要** — basic / selfrag 沒這層

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 看 `JudgeScore`：4 軸結構化評分 |
| 2 | 讀懂 `GroundednessJudge`：LLM 評分 + graceful degrade |
| 3 | `passes()` 為什麼是 double gate（min_axis + min_mean） |
| 4 | 讀懂 `judge_node` 與 SKIP_JUDGE_SKILLS |
| 5 | 讀懂 `make_route_after_judge`：closure + HARD_MAX 保險 |
| 6 | retry 流程：`increment_retry` → render 帶 feedback |
| 7 | force_push 流程：`mark_warning` 加 ⚠️ 前綴 |
| 8 | HITL 流程：interrupt + resume + `hitl_pending_reviews` |
| 9 | ✏️ 調 judge 門檻 |
| 10 | ✏️ 啟用 HITL + 寫 review CLI |
| 11 | ✏️ 加自訂評分軸（safety_score） |

---

## Step 1：`JudgeScore` — 4 軸結構化評分

打開 [`app/judge/scorer.py:29-53`](../../app/judge/scorer.py#L29-L53)：

```python
class JudgeScore(BaseModel):
    groundedness: int = Field(..., ge=0, le=10)
    citation_fidelity: int = Field(..., ge=0, le=10)
    format_completeness: int = Field(..., ge=0, le=10)
    uncertainty_honesty: int = Field(..., ge=0, le=10)
    issues: list[str] = Field(default_factory=list)

    @property
    def mean(self) -> float:
        return (self.groundedness + self.citation_fidelity
                + self.format_completeness + self.uncertainty_honesty) / 4

    def passes(self, *, min_axis: int = 6, min_mean: float = 7.0) -> bool:
        worst = min(self.groundedness, self.citation_fidelity,
                    self.format_completeness, self.uncertainty_honesty)
        return worst >= min_axis and self.mean >= min_mean
```

### 1-1 四軸各管什麼

| 軸 | 抓什麼問題 | 為 0-3 分代表 |
|----|----------|--------------|
| `groundedness` | 結論有沒有 contract 中的依據 | 答案在自由發揮 / 編造 |
| `citation_fidelity` | 引用文字與 contract.citations[].snippet 是否逐字相符 | 引用變形 / 亂湊 |
| `format_completeness` | 是否符合 response_mode 的格式要求 | 該 brief 卻寫一大段 |
| `uncertainty_honesty` | caveats 是否完整呈現 | 故意省略不確定性 |

`issues` 是 LLM 列出的具體問題（最多 5 條）——retry 時帶進下一輪 prompt 提示 LLM 別重犯。

### 1-2 為什麼用 4 軸而非單一總分？

註解寫：

> 4 軸而非單一分數 — 學生看到「為什麼」分數低

優點：

- **debug 容易**：8/9/3/8 一眼看出是 `format_completeness` 出問題
- **threshold 可分軸調**：高風險領域可獨立提高 `groundedness` 門檻
- **issues 有針對性**：LLM 知道是哪一軸不過，列的 issue 更具體

---

## Step 2：讀懂 `GroundednessJudge` — LLM 評分 + 降級

[`scorer.py:55-127`](../../app/judge/scorer.py#L55-L127)：

### 2-1 嚴格 JSON 契約 prompt

```python
_PROMPT = """你是嚴格的 RAG 輸出審查員。
你會收到 (a) 助理產出的回覆 markdown；(b) 該次的 Answer Contract（含 citations）。

依以下 4 軸打分（0~10）：
- groundedness: 結論是否都有 contract 中的依據
- citation_fidelity: 引用文字是否與 contract.citations[].snippet 逐字相符
- format_completeness: 是否符合 response_mode={response_mode} 的格式要求
- uncertainty_honesty: caveats 是否完整呈現

輸出嚴格 JSON（無 markdown fence、無前後文、不要解釋）：
{{
  "groundedness": 0,
  "citation_fidelity": 0,
  "format_completeness": 0,
  "uncertainty_honesty": 0,
  "issues": ["最多 5 條具體問題"]
}}

回覆 markdown：
{narrative}

Answer Contract：
{contract_json}
"""
```

關鍵：把 narrative + contract 都餵進去，judge 才能「對比」找出落差。

### 2-2 `judge` 三道降級

```python
async def judge(self, *, narrative, contract, response_mode) -> JudgeScore | None:
    if self.llm is None:
        return None   # 沒 LLM → None（視為 pass）

    prompt = _PROMPT.format(...)
    try:
        raw = await self.llm.complete(prompt)
        data = json.loads(_strip_fence(raw))
        issues = data.get("issues") or []
        if isinstance(issues, list):
            issues = [str(i) for i in issues if i][:5]   # 限 5 條防 prompt 注入
        return JudgeScore(
            groundedness=int(data["groundedness"]),
            citation_fidelity=int(data["citation_fidelity"]),
            format_completeness=int(data["format_completeness"]),
            uncertainty_honesty=int(data["uncertainty_honesty"]),
            issues=issues,
        )
    except Exception:
        logger.warning("judge call failed; degrading to pass", exc_info=True)
        return None   # LLM 失敗 / JSON 解析錯 → None
```

**為什麼 judge 失敗視為 pass？**

如果 judge 失敗 = 阻斷輸出，整個 graph 等於是 LLM single point of failure 加倍——既要相信 narrative LLM 也要相信 judge LLM。任何一個 down 就壞。

降級為 pass 的選擇：**judge 是品質保險，不是必經審核**。失敗時讓答案先出去，記 log 給維運看，不阻斷使用者體驗。

如果你的場景嚴格要求 judge 必過（高風險），可以改成 fail-closed：

```python
# 改成失敗阻斷
async def judge(self, ...):
    if self.llm is None:
        raise RuntimeError("judge LLM unavailable")   # 不降級
    try:
        # ...
    except Exception:
        raise   # 不 swallow
```

並在 `judge_node` 設「失敗 → human_review」分支。

---

## Step 3：`passes()` 為什麼是 double gate

```python
def passes(self, *, min_axis: int = 6, min_mean: float = 7.0) -> bool:
    worst = min(self.groundedness, self.citation_fidelity,
                self.format_completeness, self.uncertainty_honesty)
    return worst >= min_axis and self.mean >= min_mean
```

兩個條件**同時**要過：

- **`worst >= min_axis`**：最弱一軸要 ≥ 6
- **`mean >= min_mean`**：平均要 ≥ 7

### 3-1 為什麼不單看平均？

假設四軸 `[10, 10, 10, 0]`，平均 7.5。沒 double gate 就 pass——但 `uncertainty_honesty=0` 代表「故意省略 caveats」，是嚴重問題。

double gate 防止「一軸超高拉平均」的漏洞。

### 3-2 ✏️ 改成你的需求：依領域調 gate

```bash
# .env 一般場景
JUDGE_MIN_AXIS=6
JUDGE_MIN_MEAN=7.0

# 醫療嚴格
JUDGE_MIN_AXIS=8
JUDGE_MIN_MEAN=8.5

# 閒聊寬鬆
JUDGE_MIN_AXIS=4
JUDGE_MIN_MEAN=5.0
```

---

## Step 4：`judge_node` 與 SKIP_JUDGE_SKILLS

[`app/graph/nodes.py:300-341`](../../app/graph/nodes.py#L300-L341)：

```python
SKIP_JUDGE_SKILLS: set[str] = {"general_chat", "emotional_calibration"}


@traced("judge")
async def judge_node(state: RAGState, services: Any) -> dict[str, Any]:
    settings = services.settings

    # 1. 全域 disable
    if not getattr(settings, "judge_enabled", True):
        return {"judge_score": None, "judge_feedback": []}

    # 2. 特定 skill 跳過
    skill = state.get("skill")
    if skill is not None and skill.skill_id in SKIP_JUDGE_SKILLS:
        logger.info("judge skipped: skill=%s in SKIP_JUDGE_SKILLS", skill.skill_id)
        return {"judge_score": None, "judge_feedback": []}

    # 3. 不需 RAG 的回覆跳過
    router_result = state["router_result"]
    if not router_result.is_rag_required:
        return {"judge_score": None, "judge_feedback": []}

    # 4. 真正打 judge
    response_mode = getattr(router_result, "response_mode", "default")
    narrative = "\n\n".join(state.get("responses") or [])
    score = await services.judge.judge(
        narrative=narrative,
        contract=state["answer_contract"],
        response_mode=response_mode,
    )
    if score is None:
        return {"judge_score": None, "judge_feedback": []}

    # 5. 決定 pass / fail
    passed = score.passes(min_axis=settings.judge_min_axis, min_mean=settings.judge_min_mean)
    feedback = [] if passed else list(score.issues)
    logger.info("judge mean=%.1f pass=%s issues=%d", score.mean, passed, len(score.issues))
    return {"judge_score": score, "judge_feedback": feedback}
```

### 4-1 為什麼 `general_chat` / `emotional_calibration` 不過 judge？

- **`general_chat`**：閒聊回覆沒 chunks 可 grounded，4 軸都不適用
- **`emotional_calibration`**：情緒回應重感受不重 citation，judge 規則只會誤殺

跳過 = judge_score 為 None → route 視為 pass → 直接 push。

### 4-2 ✏️ 改 SKIP 名單

```python
# app/graph/nodes.py:300
SKIP_JUDGE_SKILLS: set[str] = {"general_chat", "emotional_calibration", "casual_chat"}
```

或從 settings 拉：

```python
# config.py
skip_judge_skills: set[str] = {"general_chat", "emotional_calibration"}
```

---

## Step 5：`make_route_after_judge` — closure + HARD_MAX 保險

[`nodes.py:344-363`](../../app/graph/nodes.py#L344-L363)：

```python
def make_route_after_judge(max_retries: int, *, hitl_enabled: bool = False):
    """Closure：注入 max_retries 作為 retry → force_push / human_review 的門檻。

    硬上限保險：effective_max = min(max(max_retries, 0), 2)
    ——避免設定過高導致無限迴圈，也用 max(.., 0) 防 settings 配成負數。
    """
    HARD_MAX = 2
    effective_max = min(max(max_retries, 0), HARD_MAX)

    def route_after_judge(state: RAGState) -> str:
        score = state.get("judge_score")
        feedback = state.get("judge_feedback") or []
        if score is None or not feedback:
            return "pass"   # judge 跳過 / 失敗 / 通過
        retry = state.get("reflection_retry", 0)
        if retry >= effective_max:
            return "human_review" if hitl_enabled else "force_push"
        return "retry"

    return route_after_judge
```

### 5-1 三向分流

```
              judge
                │
       ┌────────┼─────────┐
       ↓        ↓         ↓
     pass     retry    force_push (或 human_review)
       │       │              │
     push  increment    mark_warning
              │              │
        (回 render)         push
```

- `score is None or not feedback`：pass（judge 跳過 / 沒問題）
- `retry < effective_max`：再試一次
- `retry >= effective_max`：放棄，依 hitl_enabled 走不同分支

### 5-2 `HARD_MAX = 2` 硬上限

```python
HARD_MAX = 2
effective_max = min(max(max_retries, 0), HARD_MAX)
```

不管 settings 寫多少都最多 2 次 retry。原因：

- **成本爆炸**：每 retry 多一輪 LLM render + judge call
- **延遲累積**：retry 3 次 = 6 次 LLM call，使用者等不及
- **品質遞減**：retry 2 次還不過，多半是根本沒救（chunks 不夠 / prompt 有問題）

如果你真的要更高 retry，改 `HARD_MAX`：

```python
# 高品質要求場景
HARD_MAX = 3
```

但建議先看 trace 確認「多 retry 真的會 pass 嗎？」——大部分情況 retry 2 次仍 fail 表示問題不在 generator。

---

## Step 6：retry 流程 — `increment_retry` → render 帶 feedback

### 6-1 `increment_retry_node`

```python
@traced("increment_retry")
async def increment_retry_node(state: RAGState, services: Any) -> dict[str, Any]:
    """retry 路徑：累加 reflection_retry 計數，下一輪 render_narrative 會帶 feedback。"""
    current = state.get("reflection_retry", 0)
    next_count = current + 1
    logger.info("reflection retry → %d (max=%d)", next_count, services.settings.max_reflection_retries)
    return {"reflection_retry": next_count}
```

只做一件事：`reflection_retry` 計數 +1。

### 6-2 render_narrative 怎麼讀 feedback

[Ch 07 §5-2](ch07-sufficiency-generation.md#5-2-feedback_section--retry-時帶上次-judge-的意見) 已詳述：

```python
def _build_prompt(self, *, contract, skill, response_mode, emotion_state, feedback):
    feedback_section = ""
    if feedback:
        feedback_section = (
            "（前一次的問題，請改善）\n"
            + "\n".join(f"- {f}" for f in feedback)
            + "\n\n"
        )
    return _PROMPT.format(..., feedback_section=feedback_section)
```

`state["judge_feedback"]`（judge 列的 issues）會塞進這段，提示 LLM 別重犯。

### 6-3 完整 retry 流程

```
render_narrative ──→ judge
                       │
                       └─ retry → increment_retry ──→ render_narrative
                                                          ↑
                                              (帶 judge_feedback 進 prompt)
```

retry 後 reflect_retry=1 → judge 再評 → 還 fail 就再 retry（retry=2） → 第 3 次 fail → force_push 或 human_review。

---

## Step 7：force_push 流程 — `mark_warning` 加 ⚠️ 前綴

```python
@traced("mark_warning")
async def mark_warning_node(state: RAGState, services: Any) -> dict[str, Any]:
    """force_push 前在訊息開頭加品質警告。"""
    responses = list(state.get("responses") or [])
    if responses:
        responses[0] = "⚠️ 品質警告：本次回覆未通過自審\n\n" + responses[0]
    return {"responses": responses, "judge_warning_prefix": True}
```

對使用者透明告知：「這條訊息我自己審完不滿意，但我還是給你看，請審慎參考」。

比起靜默 push（讓使用者拿到不可信答案）或完全擋下（使用者體驗差），加前綴是 **「告知並交還決定權」** 的中庸解。

`judge_warning_prefix` 欄位寫進 state，給後續 audit / metrics 用——統計「過去一週多少 % 的回覆帶警告」就能評估系統健康度。

---

## Step 8：HITL 流程 — interrupt + resume

`hitl_enabled=true` 時，judge fail + retry 用盡會走到 `human_review` 而非 `force_push`。

### 8-1 `human_review_node` 與 LangGraph interrupt

```python
@traced("human_review")
async def human_review_node(state: RAGState, services: Any) -> dict[str, Any]:
    """HITL 中繼 node。實際 interrupt 由 graph compile 時的 interrupt_before 完成。

    Resume 後本 node 不做事；push_node 會讀 reviewer_decision 決定推什麼。
    """
    logger.info("human_review entered: thread=%s reviewer_decision=%s",
                state.get("external_message_id"), state.get("reviewer_decision"))
    return {}
```

關鍵在 graph compile 時的 `interrupt_before`：

```python
# reflection.py:118
if hitl_enabled:
    compile_kwargs["interrupt_before"] = ["human_review"]
return g.compile(**compile_kwargs)
```

`interrupt_before=["human_review"]` 告訴 LangGraph：**跑到 `human_review` 之前停下來**，把 state 寫入 checkpointer，回給呼叫端。呼叫端拿到 `state.next == ("human_review",)` 就知道被 interrupt。

### 8-2 webhook 端怎麼處理 interrupt

[`app/line/webhook.py:104-112`](../../app/line/webhook.py#L104-L112)：

```python
# 偵測 interrupt — 若 graph 在 push 前中斷（hitl_enabled + judge fail），
# 只標記 pending review，不執行 outbound 落庫 / 推送，等 review_queue.py 接手。
if await _is_interrupted(services.rag_graph, graph_config):
    try:
        await services.messages_repo.mark_pending_review(
            thread_id=thread_id, line_user_id=user_id
        )
    except Exception:
        logger.warning("mark_pending_review failed for thread=%s", thread_id, exc_info=True)
    return
```

### 8-3 `_is_interrupted` 怎麼偵測

```python
async def _is_interrupted(graph, config: dict) -> bool:
    """spec-21：判斷 graph 是否在 interrupt_before 節點處中斷。

    LangGraph 中斷時 `aget_state(config).next` 會回傳 pending 節點名稱 tuple；
    無 checkpointer / 無 thread_id 時 aget_state 會拋例外，安全當作未中斷處理。
    """
    try:
        snapshot = await graph.aget_state(config)
    except Exception:
        return False
    return bool(getattr(snapshot, "next", ()))
```

`snapshot.next` 是 LangGraph 的 API——回傳 **tuple of node names**（接下來要跑哪些 node）：
- 中斷時：`("human_review",)` 或 `("某 node",)`，非空 tuple
- 正常跑完：`()`，空 tuple

`bool(())` 是 `False`、`bool(("anything",))` 是 `True`——所以一行 `bool(getattr(snapshot, "next", ()))` 就能判斷有沒有 pending node。

### 8-4 完整 HITL 流程

```
1. user 發訊息 → webhook → graph 開始跑
2. judge fail 兩次 → route_after_judge 回 "human_review"
3. interrupt_before=["human_review"] → graph 停在 human_review 之前
4. webhook 偵測到 interrupt → 呼叫 mark_pending_review，寫一筆到 hitl_pending_reviews 表
5. ----- 等待人類 -----
6. 管理員用 CLI / Dashboard 看 list_pending_reviews → 撈出待審
7. 管理員 review 完，呼叫 graph.ainvoke({"reviewer_decision": "approve"}, config=...) resume
8. graph 從 human_review 接著跑 → push 推給使用者
9. messages_repo.resolve_pending_review(thread_id, "approved")
```

完整 spec 見 `docs/specs/spec-21-hitl.md`。

### 8-5 啟用 HITL 需要 checkpointer

```python
# reflection.py:111-117
if hitl_enabled:
    if checkpointer is None:
        raise RuntimeError(
            "hitl_enabled=True 但 services.checkpointer 為 None。"
            " HITL 需要 checkpointer 才能 interrupt + resume；"
            " 設 CHECKPOINT_BACKEND=memory（教學）或 sqlite（生產）。"
        )
```

沒 checkpointer，state 無法持久化，interrupt 後就找不到上下文。明確 raise 比靜默壞掉好。

---

## Step 9：✏️ 調 judge 門檻

### 9-1 全套門檻設定

```bash
# .env
JUDGE_ENABLED=true                # false 就完全跳過 judge
JUDGE_MIN_AXIS=6                  # 最弱軸下限
JUDGE_MIN_MEAN=7.0                # 平均下限
MAX_REFLECTION_RETRIES=2          # 但 HARD_MAX=2 永遠生效
JUDGE_MODEL=gpt-4o-mini           # judge 用便宜模型即可
```

### 9-2 ✏️ 改變特定 skill 的門檻

預設 `judge_min_axis` 是全域。如果你要某 skill 更嚴格：

```python
# app/graph/nodes.py:judge_node
async def judge_node(state, services):
    # ...
    score = await services.judge.judge(...)
    if score is None:
        return ...

    # 依 skill 切換 threshold
    min_axis = settings.judge_min_axis
    min_mean = settings.judge_min_mean
    if skill and skill.skill_id == "legal_advisor":
        min_axis = 8
        min_mean = 8.5

    passed = score.passes(min_axis=min_axis, min_mean=min_mean)
    feedback = [] if passed else list(score.issues)
    return {"judge_score": score, "judge_feedback": feedback}
```

更乾淨——把 threshold 放進 SkillDefinition：

```yaml
# skills/legal_advisor/SKILL.md frontmatter
---
skill_id: legal_advisor
# ...
judge_min_axis: 8
judge_min_mean: 8.5
---
```

對應改 SkillDefinition pydantic model 與 judge_node 讀法。

---

## Step 10：✏️ 啟用 HITL + 寫 review CLI

### 10-1 啟用

```bash
# .env
HITL_ENABLED=true
CHECKPOINT_BACKEND=sqlite           # 或 postgres
CHECKPOINT_SQLITE_PATH=./data/checkpoints.db
```

確保 hitl_pending_reviews 表已套用：

```bash
# 看 ch01 schema.sql 是否含 hitl 段
psql "$SUPABASE_DB_URL" -c '\d hitl_pending_reviews'
```

### 10-2 用既有 `scripts/review_queue.py`

本專案已備好 [`scripts/review_queue.py`](../../scripts/review_queue.py)（spec-21 / task-21 步驟 6）。它的設計比上面教學版簡化更完整：

**用 checkpointer 找 pending 而非用 hitl_pending_reviews 表**：

```python
def _list_pending(services) -> list[dict]:
    """用 checkpointer 列出 next=human_review 的 thread。"""
    cp = services.checkpointer
    if cp is None:
        return []
    out = []
    for tup in cp.list(None, limit=200):   # checkpointer 內建 list 方法
        thread_id = tup.config["configurable"].get("thread_id")
        if not thread_id:
            continue
        snapshot = services.rag_graph.get_state(_cfg(thread_id))
        if "human_review" in (snapshot.next or ()):   # 用 graph 真實狀態判定
            out.append(...)
    return out
```

**為什麼用 checkpointer 而非 hitl_pending_reviews 表？**

- `hitl_pending_reviews` 是 audit/CLI 索引用的副本，**真實的 interrupt 狀態在 checkpointer**
- 直接查 checkpointer 永遠跟 graph 一致；查 hitl_pending_reviews 可能有 race condition
- `hitl_pending_reviews` 是為了未來給 Dashboard / 跨 service 查詢用的（spec-21 §opt-in 表）

**Approve / revise / drop 用 `update_state + ainvoke(None)` resume**：

```python
async def _approve(services, thread_id: str):
    cfg = _cfg(thread_id)
    # 把人類決策寫入 state
    await services.rag_graph.aupdate_state(cfg, {"reviewer_decision": "approve"})
    # ainvoke(None) 從 interrupt 點 resume
    await services.rag_graph.ainvoke(None, config=cfg)
    # 標 resolved（給 audit 用）
    await services.messages_repo.resolve_pending_review(thread_id=thread_id, status="approved")
```

跑：

```bash
poetry run python scripts/review_queue.py list
poetry run python scripts/review_queue.py show line-U123-msg456
poetry run python scripts/review_queue.py approve line-U123-msg456
poetry run python scripts/review_queue.py revise line-U123-msg456 --text "改後內容"
poetry run python scripts/review_queue.py drop line-U999-msg789
```

> ⚠️ checkpointer 要設成 `sqlite` 或 `postgres`（持久後端），不然重啟後 review queue 就空了。memory backend 只在同一個 process 內看得到 pending。

---

## Step 11：✏️ 加自訂評分軸（safety_score）

假設你的領域要加「安全性」軸（醫療：是否有提到風險、法律：是否有「諮詢律師」提醒）。

### 11-1 改 `JudgeScore` schema

```python
# app/judge/scorer.py
class JudgeScore(BaseModel):
    groundedness: int = Field(..., ge=0, le=10)
    citation_fidelity: int = Field(..., ge=0, le=10)
    format_completeness: int = Field(..., ge=0, le=10)
    uncertainty_honesty: int = Field(..., ge=0, le=10)
    safety_score: int = Field(0, ge=0, le=10)   # ← 新增，default 0
    issues: list[str] = Field(default_factory=list)

    @property
    def mean(self) -> float:
        return (self.groundedness + self.citation_fidelity
                + self.format_completeness + self.uncertainty_honesty
                + self.safety_score) / 5   # ← 改除以 5

    def passes(self, *, min_axis=6, min_mean=7.0) -> bool:
        worst = min(self.groundedness, self.citation_fidelity,
                    self.format_completeness, self.uncertainty_honesty,
                    self.safety_score)
        return worst >= min_axis and self.mean >= min_mean
```

### 11-2 改 prompt 加軸描述

```python
_PROMPT = """...
依以下 5 軸打分（0~10）：
- groundedness: 結論是否都有 contract 中的依據
- citation_fidelity: 引用文字是否與 contract.citations[].snippet 逐字相符
- format_completeness: 是否符合 response_mode={response_mode} 的格式要求
- uncertainty_honesty: caveats 是否完整呈現
- safety_score: 是否包含必要的安全提醒（醫療/法律建議須註明專業諮詢）   ← 新增

輸出嚴格 JSON：
{{
  "groundedness": 0,
  "citation_fidelity": 0,
  "format_completeness": 0,
  "uncertainty_honesty": 0,
  "safety_score": 0,                          ← 新增
  "issues": ["最多 5 條具體問題"]
}}
...
"""
```

### 11-3 改 `judge.judge` 解析新欄位

```python
return JudgeScore(
    groundedness=int(data["groundedness"]),
    citation_fidelity=int(data["citation_fidelity"]),
    format_completeness=int(data["format_completeness"]),
    uncertainty_honesty=int(data["uncertainty_honesty"]),
    safety_score=int(data.get("safety_score", 0)),   # 兼容舊回應
    issues=issues,
)
```

`get` + default 0 讓 schema 變更不會破壞既有 LLM 回應。

---

## 🎯 本章驗收

### Step 1：JudgeScore 邊界

```bash
poetry run python -c '
from app.judge.scorer import JudgeScore

# 高分一軸拉平均的 case
s1 = JudgeScore(groundedness=10, citation_fidelity=10, format_completeness=10, uncertainty_honesty=0)
print(f"mean={s1.mean}, passes={s1.passes()}")   # mean=7.5, passes=False（worst=0）

# 全部 7 分
s2 = JudgeScore(groundedness=7, citation_fidelity=7, format_completeness=7, uncertainty_honesty=7)
print(f"mean={s2.mean}, passes={s2.passes()}")   # mean=7, passes=True

# 全部 5 分
s3 = JudgeScore(groundedness=5, citation_fidelity=5, format_completeness=5, uncertainty_honesty=5)
print(f"mean={s3.mean}, passes={s3.passes()}")   # mean=5, passes=False
'
```

### Step 2：judge degrade 行為

```bash
poetry run python -c '
import asyncio
from app.judge.scorer import GroundednessJudge
from app.generator.contract import AnswerContract, Citation

async def main():
    j = GroundednessJudge(llm=None)
    contract = AnswerContract(summary="x", key_findings=[], citations=[Citation(chunk_id="c1", source="s", snippet="x")])
    score = await j.judge(narrative="test", contract=contract, response_mode="brief")
    print(f"score={score}")   # None

asyncio.run(main())
'
```

預期：`score=None`（degrade pass）。

### Step 3：route_after_judge 三向

```bash
poetry run python -c '
from app.graph.nodes import make_route_after_judge
from app.judge.scorer import JudgeScore

route = make_route_after_judge(max_retries=2, hitl_enabled=False)

# pass
print(route({"judge_score": None, "judge_feedback": []}))

# retry
score = JudgeScore(groundedness=3, citation_fidelity=3, format_completeness=3, uncertainty_honesty=3, issues=["issue 1"])
print(route({"judge_score": score, "judge_feedback": ["issue 1"], "reflection_retry": 0}))

# force_push（retry 用盡）
print(route({"judge_score": score, "judge_feedback": ["issue 1"], "reflection_retry": 5}))
'
```

預期：`pass / retry / force_push`。

### Step 4：reflection variant 完整跑

```bash
GRAPH_VARIANT=reflection poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    services = await build_runtime_services(Settings())
    inp = ChannelInput(channel="stub", external_user_id="U_demo_judge",
                       external_message_id="msg_1",
                       raw_text="Supabase HNSW 怎麼設 m 與 ef？")
    await process_channel_input(inp, services)
    for r, ms in services.channels["stub"].pushed:
        for m in ms:
            print(m[:200])

asyncio.run(main())
'
```

預期：看到回應。看 `.traces/*.json` 能看到 `judge` 節點被執行。

### Step 5：HITL（選擇性）

```bash
# 啟用 HITL
HITL_ENABLED=true CHECKPOINT_BACKEND=sqlite \
  poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    services = await build_runtime_services(Settings())
    # 故意餵一個容易判 fail 的 query（沒對應 KB）
    inp = ChannelInput(channel="stub", external_user_id="U_eval_hitl",
                       external_message_id="msg_hitl_1",
                       raw_text="火星上的稅務規定是什麼？")
    await process_channel_input(inp, services)

asyncio.run(main())
'

# 看待審
psql "$SUPABASE_DB_URL" -c "select * from hitl_pending_reviews;"
```

預期：表內有一筆 pending review。

---

## 下一章

[Ch 09：觀測（Tracer + Logger + Pricing）+ 安全 Guards](ch09-observability-security.md) — 系統跑起來後，怎麼看每次請求的 token cost、latency、決策軌跡？怎麼擋 prompt injection 與 PII 外洩？
