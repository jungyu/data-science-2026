# task-skill-loader · Skill Loader 實作

> **使用時機**：從零實作 skill loader，或修改 SKILL.md 格式時使用。

---

請在 `app/skills/` 目錄下實作 skill 定義的載入、驗證與 Supabase seed 模組，以及對應的 CLI seed 腳本。

## 目標目錄結構

```
app/skills/
├── loader.py    # SkillDefinition dataclass + load_skill_from_path()
└── registry.py  # SkillRegistry

scripts/
└── seed_skills.py   # CLI：將 skills/*/SKILL.md 寫入 ai_skills 資料表
```

## SKILL.md 格式（現行標準）

```markdown
---
skill_id: tech_architect          # 對應 SkillId，必填
name: 技術架構師                   # 顯示名稱，必填
category: engineering
version: 0.1.0
description: "..."                # 必填
use_when:                         # list[str]
  - ...
avoid_when:                       # list[str]
  - ...
default_temperature: 0.3          # 0.0 ~ 1.0
rag_categories:                   # 此 skill 可用的 category 白名單
  - engineering
  - architecture
  - code
  - rag
---

{system_prompt 正文，Markdown 格式}
```

## loader.py 規格

```python
@dataclass
class SkillDefinition:
    skill_id: str
    name: str
    description: str
    category: str
    system_prompt: str
    use_when: list[str]
    avoid_when: list[str]
    rag_categories: list[str]
    default_temperature: float
    version: str

def load_skill_from_path(path: Path) -> SkillDefinition:
    # 1. 讀取 SKILL.md
    # 2. 分離 frontmatter（--- 之間的 YAML）與 body（system prompt）
    # 3. 驗證必填欄位：skill_id, name, description, system_prompt
    # 4. 回傳 SkillDefinition
    # 5. 格式錯誤 → 拋出有明確說明的 ValueError（skill_id 是哪個檔案）

def load_all_skills(skills_dir: Path) -> list[SkillDefinition]:
    # glob skills_dir/*/SKILL.md
    # 逐一 load_skill_from_path()
    # 收集所有結果，個別失敗不影響其他 skill 載入
```

## registry.py 規格

```python
class SkillRegistry:
    def __init__(self, skills: list[SkillDefinition]) -> None: ...

    def get(self, skill_id: str) -> SkillDefinition | None: ...

    def require(self, skill_id: str) -> SkillDefinition:
        # 找不到 → raise KeyError
```

## scripts/seed_skills.py 規格

```python
#!/usr/bin/env python
# 使用方式：.venv/bin/python scripts/seed_skills.py
# 必須使用 venv Python，系統 Python 可能缺少依賴

# 流程：
# 1. 載入 .env（使用 python-dotenv 或 pydantic-settings）
# 2. load_all_skills(skills_path)
# 3. 對每個 skill，upsert 到 ai_skills（以 skill_id 為 conflict target）
# 4. 印出每個 skill 的 upsert 結果（成功 / 失敗）
# 5. 結束時印出 summary：「Seeded N skills」
```

**注意**：`ai_skills` 的 upsert 以 `skill_id` 為 conflict target，`skill_id` 是 PRIMARY KEY，不需要額外的 UNIQUE constraint。

## 請輸出

1. `app/skills/loader.py` 完整程式碼
2. `app/skills/registry.py` 完整程式碼
3. `scripts/seed_skills.py` 完整程式碼
4. `tests/test_skill_loader.py` 測試案例，覆蓋：
   - 正常解析 SKILL.md → SkillDefinition 欄位正確
   - 缺少必填欄位（skill_id / name / description）→ ValueError
   - system_prompt 為空 → ValueError
   - SkillRegistry.get() 找到 / 找不到
   - SkillRegistry.require() 找不到 → KeyError

## 驗收指令

```bash
pytest tests/test_skill_loader.py -v

# 實際 seed 到 Supabase
.venv/bin/python scripts/seed_skills.py
# 期望：Seeded 6 skills（或你目前的 skill 數量），無 auth error
```

## Skill System Prompt 設計注意事項

- 只描述**回覆風格**，不要求模型輸出分類前綴（如「層級：xxx」）
- 這類中間推理輸出會直接出現在用戶看到的 LINE 訊息中，污染回覆品質
- 若需要引導模型思考，使用 user prompt（render_synthesis_prompt）傳入，而非 system prompt
