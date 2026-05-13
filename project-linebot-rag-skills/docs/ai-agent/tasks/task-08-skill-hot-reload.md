# task-08：實作 Skill 熱更新

> 規格詳見 [spec-08](../specs/spec-08-skill-hot-reload.md)
>
> **✅ 已完成（commit `0328e58`）** — 實作記錄與驗收測試見 spec-08 頂部「實作狀態」段。
---

請修改 `app/skills/registry.py` 與 `app/main.py`，支援從 Supabase 定時載入 skills。

## 步驟 1：修改 `app/config.py`

```python
skill_source: str = "file"       # "file" | "supabase"
skill_reload_interval: int = 600  # 秒
```

## 步驟 2：修改 `app/skills/registry.py`

```python
import asyncio
import logging
from app.skills.loader import SkillDefinition

logger = logging.getLogger(__name__)

class SkillRegistry:
    def __init__(self, skills: list[SkillDefinition]) -> None:
        self._lock = asyncio.Lock()
        self._skills: dict[str, SkillDefinition] = {s.skill_id: s for s in skills}

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self._skills.get(skill_id)

    def require(self, skill_id: str) -> SkillDefinition:
        skill = self._skills.get(skill_id)
        if skill is None:
            raise KeyError(f"Skill not found: {skill_id}")
        return skill

    @classmethod
    def from_directory(cls, skills_dir) -> "SkillRegistry":
        from app.skills.loader import load_all_skills
        return cls(load_all_skills(Path(skills_dir)))

    @classmethod
    async def from_supabase(cls, supabase_client) -> "SkillRegistry":
        skills = await _fetch_skills_from_supabase(supabase_client)
        return cls(skills)

    async def reload_from_supabase(self, supabase_client) -> None:
        try:
            skills = await _fetch_skills_from_supabase(supabase_client)
            async with self._lock:
                self._skills = {s.skill_id: s for s in skills}
            logger.info("Skills reloaded from Supabase: %d skills", len(skills))
        except Exception:
            logger.exception("Failed to reload skills from Supabase, keeping current")


async def _fetch_skills_from_supabase(supabase_client) -> list[SkillDefinition]:
    result = await supabase_client.table("ai_skills").select("*").eq("enabled", True).execute()
    skills = []
    for row in result.data:
        skills.append(SkillDefinition(
            skill_id=row["skill_id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            system_prompt=row["system_prompt"],
            use_when=row.get("use_when") or [],
            avoid_when=row.get("avoid_when") or [],
            rag_categories=row.get("output_style", {}).get("rag_categories") or [],
            default_temperature=float(row.get("default_temperature") or 0.4),
            version=row.get("version") or "0.1.0",
        ))
    return skills
```

## 步驟 3：修改 `app/main.py`

```python
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.skill_source == "supabase":
        task = asyncio.create_task(_skill_reload_loop(registry, supabase_client, settings.skill_reload_interval))
    yield
    if settings.skill_source == "supabase":
        task.cancel()

async def _skill_reload_loop(registry: SkillRegistry, supabase_client, interval: int):
    while True:
        await asyncio.sleep(interval)
        await registry.reload_from_supabase(supabase_client)

app = FastAPI(title="project-linebot-rag-skills", lifespan=lifespan)
```

## 步驟 4：修改 `app/dependencies.py`

```python
if settings.skill_source == "supabase":
    registry = await SkillRegistry.from_supabase(supabase_client)
else:
    registry = SkillRegistry.from_directory(settings.skills_path)
```

## 請輸出

1. 修改後的 `app/skills/registry.py`
2. 修改後的 `app/main.py`（加入 lifespan）
3. 修改後的 `app/config.py`
4. 修改後的 `app/dependencies.py`
5. `.env.example` 新增 `SKILL_SOURCE=file`
6. 測試：mock Supabase client，確認 `reload_from_supabase` 在失敗時保留舊 skills

## 驗收指令

```bash
# 預設行為不變
SKILL_SOURCE=file ./scripts/run_local.sh

# Supabase 模式
SKILL_SOURCE=supabase ./scripts/run_local.sh
# log 應顯示 "Skills reloaded from Supabase"
```
