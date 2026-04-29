from pathlib import Path

import pytest

from app.skills.loader import SkillFormatError, load_skills, parse_skill_markdown


def test_parse_skill_markdown_extracts_frontmatter_and_body() -> None:
    skill = parse_skill_markdown(
        """---
skill_id: test_skill
name: 測試技能
description: 測試說明
category: general
---

這是 system prompt。
"""
    )

    assert skill.skill_id == "test_skill"
    assert skill.name == "測試技能"
    assert skill.system_prompt == "這是 system prompt。"


def test_load_skills_from_directory(tmp_path: Path) -> None:
    skill_dir = tmp_path / "sample-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
skill_id: sample_skill
name: 範例技能
description: 範例說明
category: general
---

範例 prompt。
""",
        encoding="utf-8",
    )

    skills = load_skills(tmp_path)
    assert [skill.skill_id for skill in skills] == ["sample_skill"]


def test_invalid_skill_format_raises_clear_error() -> None:
    with pytest.raises(SkillFormatError):
        parse_skill_markdown("no frontmatter")
