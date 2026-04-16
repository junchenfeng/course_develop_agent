"""教案模型单元测试。"""

import pytest
from pathlib import Path

from simclass.models.lesson import Lesson, Phase, PresetQuestion, StudentProfile


EXAMPLE_YAML = Path(__file__).parent.parent.parent / "examples" / "python_variables.yaml"


class TestPhase:
    def test_basic(self):
        p = Phase(name="test", duration_minutes=5, description="desc", key_points=["a"])
        assert p.name == "test"
        assert p.duration_minutes == 5

    def test_duration_must_be_positive(self):
        with pytest.raises(Exception):
            Phase(name="bad", duration_minutes=0)


class TestLesson:
    def test_from_yaml(self):
        lesson = Lesson.from_yaml(EXAMPLE_YAML)
        assert lesson.title == "Python 变量与数据类型"
        assert lesson.duration_minutes == 20
        assert len(lesson.phases) == 5
        assert len(lesson.students) == 3
        assert len(lesson.preset_questions) == 4

    def test_student_names(self):
        lesson = Lesson.from_yaml(EXAMPLE_YAML)
        names = [s.name for s in lesson.students]
        assert "小明" in names
        assert "小红" in names
        assert "小刚" in names

    def test_preset_question_references_valid(self):
        lesson = Lesson.from_yaml(EXAMPLE_YAML)
        phase_names = {p.name for p in lesson.phases}
        student_names = {s.name for s in lesson.students}
        for q in lesson.preset_questions:
            assert q.expected_phase in phase_names
            assert q.asked_by in student_names

    def test_invalid_phase_reference_raises(self):
        with pytest.raises(ValueError, match="expected_phase"):
            Lesson(
                title="test",
                duration_minutes=10,
                phases=[Phase(name="A", duration_minutes=10)],
                students=[StudentProfile(name="X", persona="test", traits="test")],
                preset_questions=[
                    PresetQuestion(
                        question="?",
                        expected_phase="NONEXISTENT",
                        asked_by="X",
                    )
                ],
            )

    def test_invalid_student_reference_raises(self):
        with pytest.raises(ValueError, match="asked_by"):
            Lesson(
                title="test",
                duration_minutes=10,
                phases=[Phase(name="A", duration_minutes=10)],
                students=[StudentProfile(name="X", persona="test", traits="test")],
                preset_questions=[
                    PresetQuestion(
                        question="?",
                        expected_phase="A",
                        asked_by="NOBODY",
                    )
                ],
            )


class TestSession:
    def test_timeline_event(self):
        from simclass.models.session import Session, TimelineEvent, EventType

        s = Session(session_id="test", lesson_title="test", lesson_path="test.yaml")
        s.add_event(TimelineEvent(t=0, type=EventType.SESSION_START, text="start"))
        assert len(s.timeline) == 1

    def test_save_and_load(self, tmp_path):
        from simclass.models.session import Session, TimelineEvent, EventType
        import json

        s = Session(session_id="test", lesson_title="test", lesson_path="test.yaml")
        s.add_event(TimelineEvent(t=0, type=EventType.SESSION_START, text="start"))
        s.add_event(TimelineEvent(
            t=5.0, type=EventType.TEACHER_SPEECH, text="hello", speaker="teacher"
        ))
        s.end()
        path = s.save(tmp_path)

        data = json.loads(path.read_text())
        assert data["session_id"] == "test"
        assert len(data["timeline"]) == 2
