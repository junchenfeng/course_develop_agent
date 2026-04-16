"""会话编排器 — 协调 STT、Agent、录制的核心枢纽。"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable

from simclass.agents.student_agent import AgentAction, OrchestratorContext, StudentAgent
from simclass.models.lesson import Lesson
from simclass.models.session import EventType, Session, TimelineEvent

logger = logging.getLogger(__name__)


class Orchestrator:
    """管理一次模拟课堂会话。"""

    def __init__(
        self,
        lesson: Lesson,
        agents: list[StudentAgent],
        session: Session,
        on_student_action: Callable[[AgentAction], Awaitable[None]] | None = None,
        on_phase_change: Callable[[str, int], Awaitable[None]] | None = None,
    ) -> None:
        self.lesson = lesson
        self.agents = agents
        self.session = session
        self.on_student_action = on_student_action
        self.on_phase_change = on_phase_change

        self.current_phase_idx = 0
        self._phase_start_time = time.time()
        self._asked_questions: set[int] = set()
        self._lock = asyncio.Lock()

    @property
    def current_phase(self):
        if self.current_phase_idx < len(self.lesson.phases):
            return self.lesson.phases[self.current_phase_idx]
        return self.lesson.phases[-1]

    @property
    def elapsed_minutes(self) -> float:
        return self.session.elapsed / 60.0

    def _build_context(self) -> OrchestratorContext:
        phase = self.current_phase
        return OrchestratorContext(
            current_phase_name=phase.name,
            phase_description=phase.description,
            lesson_title=self.lesson.title,
            elapsed_minutes=self.elapsed_minutes,
        )

    def _update_phase_tracking(self) -> None:
        """基于时间自动推进教学环节。"""
        elapsed = time.time() - self._phase_start_time
        phase_duration = self.current_phase.duration_minutes * 60

        if elapsed >= phase_duration and self.current_phase_idx < len(self.lesson.phases) - 1:
            self.current_phase_idx += 1
            self._phase_start_time = time.time()

            self.session.add_event(TimelineEvent(
                t=self.session.elapsed,
                type=EventType.PHASE_CHANGE,
                text=self.current_phase.name,
                metadata={"phase_idx": self.current_phase_idx},
            ))

            logger.info(
                "Phase changed to [%d] %s",
                self.current_phase_idx,
                self.current_phase.name,
            )

            if self.on_phase_change:
                asyncio.create_task(
                    self.on_phase_change(self.current_phase.name, self.current_phase_idx)
                )

    def _maybe_schedule_preset_question(self) -> dict | None:
        """检查当前环节是否有未提出的预设问题。"""
        phase_name = self.current_phase.name
        candidates = []
        for i, q in enumerate(self.lesson.preset_questions):
            if i not in self._asked_questions and q.expected_phase == phase_name:
                candidates.append((i, q))

        if not candidates:
            return None

        # 每次调用有 30% 概率触发一个预设问题
        if random.random() > 0.3:
            return None

        idx, q = random.choice(candidates)
        self._asked_questions.add(idx)
        return {
            "question": q.question,
            "asked_by": q.asked_by,
            "reference_answer": q.reference_answer,
            "difficulty": q.difficulty,
            "question_index": idx,
        }

    async def on_teacher_utterance(self, text: str) -> list[AgentAction]:
        """教师说完一段话后触发（STT is_final=true）。"""
        async with self._lock:
            timestamp = self.session.elapsed

            # 1. 记录教师发言
            self.session.add_event(TimelineEvent(
                t=timestamp,
                type=EventType.TEACHER_SPEECH,
                text=text,
                speaker="teacher",
            ))

            # 2. 更新教学环节
            self._update_phase_tracking()

            # 3. 检查预设问题
            scheduled_q = self._maybe_schedule_preset_question()

            # 4. 构建上下文
            ctx = self._build_context()
            if scheduled_q:
                ctx.scheduled_question = scheduled_q

            # 5. 并行触发所有 Agent 决策
            decisions = await asyncio.gather(
                *[agent.decide(text, ctx) for agent in self.agents],
                return_exceptions=True,
            )

            # 6. 收集有效 action
            actions: list[AgentAction] = []
            for d in decisions:
                if isinstance(d, AgentAction):
                    actions.append(d)
                elif isinstance(d, Exception):
                    logger.error("Agent decision error: %s", d)

            # 7. 排队输出（模拟真实反应时间）
            for action in actions:
                delay = random.uniform(0.8, 3.0)
                await asyncio.sleep(delay)

                self.session.add_event(TimelineEvent(
                    t=self.session.elapsed,
                    type=EventType.STUDENT_ACTION,
                    text=action.text,
                    speaker=action.student_name,
                    action_type=action.type,
                ))

                if self.on_student_action:
                    await self.on_student_action(action)

            return actions
