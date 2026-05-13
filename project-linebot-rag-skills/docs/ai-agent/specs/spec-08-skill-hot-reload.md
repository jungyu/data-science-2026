# Spec-08：Skill 熱更新

> **✅ 已實作（commit `0328e58`）**
>
> - `SkillRegistry` 加 `from_supabase` / `reload_from_supabase`（async + `asyncio.Lock` 原子替換）
> - 新增 `skill_reload_loop` 背景無限迴圈；`config.py` 加 `skill_source` / `skill_reload_interval`
> - `app/main.py` 改寫為 `lifespan` 模式：startup 從 `ai_skills` 載入並啟動 reload task，shutdown cancel
> - `app/dependencies.py::replace_skill_registry` 在 runtime 替換 services.skill_registry
> - Supabase 拉取失敗保留舊 skills，不中斷服務
> - 驗收測試：`tests/test_skill_hot_reload.py`（8 cases 含 supabase 失敗 fallback、空表 fallback、reload loop 循環）

## 背景

目前 `SkillRegistry` 在 App 啟動時從本地 `skills/*/SKILL.md` 載入，修改 skill system prompt 後需重啟 App 才能生效。`ai_skills` Supabase 資料表已存在並由 `seed_skills.py` 寫入，但 App runtime 不讀它。

## 目標

讓 `SkillRegistry` 支援從 Supabase 動態載入 skills，並加入定時 reload 機制，不重啟 App 就能更新 skill 定義。

## 設計

### 兩種載入來源（可配置）

```
SKILL_SOURCE=file        # 現有行為（從 skills/ 目錄載入）
SKILL_SOURCE=supabase    # 從 ai_skills 資料表載入
```

### Reload 機制

`SKILL_SOURCE=supabase` 時，每 N 分鐘（預設 10 分鐘）重新從 Supabase 拉取 `ai_skills`，更新 in-memory 的 registry。

使用 FastAPI 的 `lifespan` context manager 啟動背景 reload task。

## 介面契約

**修改**：`app/config.py`
```python
skill_source: str = "file"          # "file" | "supabase"
skill_reload_interval: int = 600    # 秒，SKILL_SOURCE=supabase 時生效
```

**修改**：`app/skills/registry.py`

```python
class SkillRegistry:
    def __init__(self, skills: list[SkillDefinition]) -> None: ...

    @classmethod
    def from_directory(cls, skills_dir: Path) -> "SkillRegistry": ...

    @classmethod
    async def from_supabase(cls, supabase_client) -> "SkillRegistry":
        # SELECT * FROM ai_skills WHERE enabled = true
        # 轉換為 SkillDefinition list

    async def reload_from_supabase(self, supabase_client) -> None:
        # 拉取最新 skills，替換 in-memory 的 _skills dict
        # 使用 asyncio.Lock 確保並發安全
```

**修改**：`app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.skill_source == "supabase":
        asyncio.create_task(_skill_reload_loop(registry, supabase, interval))
    yield
```

## Fallback

Supabase 拉取失敗時，保留上一次成功載入的 skills，記 log，不中斷服務。

## 不做什麼

- 不支援 webhook 觸發即時 reload（間隔 reload 已足夠個人使用）
- 不修改 `skills/*/SKILL.md` 的格式
- 不刪除 file-based 載入（預設仍用 `file`）

## 驗收標準

- `SKILL_SOURCE=supabase` 啟動後，修改 `ai_skills` 的 `system_prompt`，等待 10 分鐘，bot 回覆風格改變
- Supabase 斷線時，bot 仍用舊 skills 正常運作，log 有警告
- `SKILL_SOURCE=file` 行為與現在完全一致（不破壞現有功能）
