"""Student Agent — 模拟学生的 LLM Agent。"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from simclass.agents.prompts import (
    STUDENT_FORCED_RESPONSE_USER,
    STUDENT_FREE_RESPONSE_USER,
    STUDENT_REACTION_USER,
    STUDENT_SYSTEM_PROMPT,
)
from simclass.models.lesson import StudentProfile

if TYPE_CHECKING:
    from simclass.agents.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class AgentAction:
    """Agent 的一次发言行为。"""

    student_name: str
    type: str  # "free_response" | "preset_question" | "forced_response" | "reaction"
    text: str


@dataclass
class OrchestratorContext:
    """Orchestrator 传递给 Agent 的上下文。"""

    current_phase_name: str = ""
    phase_description: str = ""
    lesson_title: str = ""
    elapsed_minutes: float = 0.0
    scheduled_question: dict | None = None


@dataclass
class StudentAgent:
    """一个 AI 学生 Agent。"""

    profile: StudentProfile
    llm: LLMClient
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    turns_silent: int = 0

    # 人设对应的发言倾向
    _speak_base_prob: float = field(init=False, default=0.15)

    def __post_init__(self) -> None:
        persona_probs = {
            "积极主动型": 0.35,
            "认真沉默型": 0.08,
            "容易走神型": 0.12,
        }
        self._speak_base_prob = persona_probs.get(self.profile.persona, 0.15)

    def _build_system_prompt(self, ctx: OrchestratorContext) -> str:
        return STUDENT_SYSTEM_PROMPT.format(
            name=self.profile.name,
            persona=self.profile.persona,
            traits=self.profile.traits.strip(),
            knowledge_level=self.profile.knowledge_level,
            lesson_title=ctx.lesson_title,
            current_phase=ctx.current_phase_name,
            phase_description=ctx.phase_description,
            elapsed_minutes=ctx.elapsed_minutes,
        )

    def _compute_speak_probability(
        self,
        teacher_asked_question: bool,
    ) -> float:
        prob = self._speak_base_prob
        if teacher_asked_question:
            prob += 0.20
        # 沉默越久，发言概率越高
        prob += min(self.turns_silent * 0.03, 0.15)
        return min(prob, 0.80)

    async def decide(
        self,
        teacher_text: str,
        ctx: OrchestratorContext,
    ) -> AgentAction | None:
        """教师说完一段话后，Agent 决策是否发言及发言内容。"""

        # 1. 被点名 → 强制回应
        if self.profile.name in teacher_text:
            return await self._generate(teacher_text, ctx, forced=True)

        # 2. Orchestrator 调度了预设问题
        sq = ctx.scheduled_question
        if sq and sq.get("asked_by") == self.profile.name:
            self.turns_silent = 0
            return AgentAction(
                student_name=self.profile.name,
                type="preset_question",
                text=sq["question"],
            )

        # 3. 自由发言概率
        teacher_asked = "?" in teacher_text or "？" in teacher_text
        prob = self._compute_speak_probability(teacher_asked)

        if random.random() < prob:
            return await self._generate(teacher_text, ctx, forced=False)

        # 4. 小概率发一个简短反应
        if random.random() < 0.08:
            return await self._generate_reaction(teacher_text, ctx)

        self.turns_silent += 1
        return None

    async def _generate(
        self,
        teacher_text: str,
        ctx: OrchestratorContext,
        forced: bool,
    ) -> AgentAction:
        system = self._build_system_prompt(ctx)
        user_tmpl = STUDENT_FORCED_RESPONSE_USER if forced else STUDENT_FREE_RESPONSE_USER
        user_msg = user_tmpl.format(teacher_text=teacher_text)

        messages = [
            {"role": "system", "content": system},
            *self.conversation_history[-6:],
            {"role": "user", "content": user_msg},
        ]

        text = await self.llm.chat(messages=messages, max_tokens=128)

        self.conversation_history.append({"role": "user", "content": f"老师: {teacher_text}"})
        self.conversation_history.append({"role": "assistant", "content": text})

        self.turns_silent = 0
        return AgentAction(
            student_name=self.profile.name,
            type="forced_response" if forced else "free_response",
            text=text,
        )

    async def _generate_reaction(
        self,
        teacher_text: str,
        ctx: OrchestratorContext,
    ) -> AgentAction:
        system = self._build_system_prompt(ctx)
        user_msg = STUDENT_REACTION_USER.format(teacher_text=teacher_text)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

        text = await self.llm.chat(messages=messages, max_tokens=16)
        self.turns_silent = 0
        return AgentAction(
            student_name=self.profile.name,
            type="reaction",
            text=text,
        )
