"""教案数据模型 — 从 YAML 解析。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class Phase(BaseModel):
    """教学环节。"""

    name: str
    duration_minutes: int = Field(gt=0)
    description: str = ""
    key_points: list[str] = Field(default_factory=list)


class PresetQuestion(BaseModel):
    """预设问题：AI 学生会在合适时机提出，分析器检查教师回答质量。"""

    question: str
    expected_phase: str
    reference_answer: str = ""
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    asked_by: str


class StudentProfile(BaseModel):
    """学生角色配置。"""

    name: str
    persona: str
    traits: str
    knowledge_level: str = "中等"


class Lesson(BaseModel):
    """完整教案。"""

    title: str
    duration_minutes: int = Field(gt=0)
    phases: list[Phase] = Field(min_length=1)
    preset_questions: list[PresetQuestion] = Field(default_factory=list)
    students: list[StudentProfile] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_references(self) -> Lesson:
        phase_names = {p.name for p in self.phases}
        student_names = {s.name for s in self.students}

        for q in self.preset_questions:
            if q.expected_phase not in phase_names:
                raise ValueError(
                    f"预设问题 '{q.question[:20]}...' 的 expected_phase "
                    f"'{q.expected_phase}' 不存在于教案环节中。"
                    f"可选: {phase_names}"
                )
            if q.asked_by not in student_names:
                raise ValueError(
                    f"预设问题 '{q.question[:20]}...' 的 asked_by "
                    f"'{q.asked_by}' 不存在于学生列表中。"
                    f"可选: {student_names}"
                )
        return self

    @classmethod
    def from_yaml(cls, path: str | Path) -> Lesson:
        """从 YAML 文件加载教案。"""
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        lesson_data = raw.get("lesson", {})
        lesson_data["students"] = raw.get("students", [])
        lesson_data["preset_questions"] = lesson_data.get("preset_questions", [])

        return cls.model_validate(lesson_data)
