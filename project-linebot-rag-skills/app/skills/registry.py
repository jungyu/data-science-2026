from __future__ import annotations

from pathlib import Path

from app.skills.loader import SkillDefinition, load_skills


class SkillRegistry:
    def __init__(self, skills: list[SkillDefinition]) -> None:
        self._skills = {skill.skill_id: skill for skill in skills}

    @classmethod
    def from_directory(cls, skills_root: Path) -> "SkillRegistry":
        return cls(load_skills(skills_root))

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self._skills.get(skill_id)

    def require(self, skill_id: str) -> SkillDefinition:
        skill = self.get(skill_id)
        if skill is None:
            raise KeyError(f"Unknown skill: {skill_id}")
        return skill

    def list(self) -> list[SkillDefinition]:
        return list(self._skills.values())
