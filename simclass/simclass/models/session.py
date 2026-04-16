"""会话数据模型 — 运行时状态和持久化。"""

from __future__ import annotations

import json
import time
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    TEACHER_SPEECH = "teacher_speech"
    STUDENT_ACTION = "student_action"
    PHASE_CHANGE = "phase_change"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class TimelineEvent(BaseModel):
    """时间线中的一个事件。"""

    t: float = Field(description="相对于会话开始的秒数")
    type: EventType
    text: str = ""
    speaker: str = ""
    action_type: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Session(BaseModel):
    """一次练课会话。"""

    session_id: str
    lesson_title: str
    lesson_path: str
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str | None = None
    duration_seconds: float | None = None
    timeline: list[TimelineEvent] = Field(default_factory=list)

    _start_ts: float = 0.0

    def model_post_init(self, __context: Any) -> None:
        self._start_ts = time.time()

    @property
    def elapsed(self) -> float:
        return time.time() - self._start_ts

    def add_event(self, event: TimelineEvent) -> None:
        self.timeline.append(event)

    def end(self) -> None:
        self.ended_at = datetime.now().isoformat()
        self.duration_seconds = self.elapsed

    def save(self, directory: Path) -> Path:
        """保存 timeline 到 JSON 文件。"""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "timeline.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                self.model_dump(exclude={"_start_ts"}),
                f,
                ensure_ascii=False,
                indent=2,
            )
        return path
