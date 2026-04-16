"""教学分析器 — 课后分析教师表现。"""

from __future__ import annotations

import logging
from pathlib import Path

from simclass.agents.llm_client import LLMClient
from simclass.models.lesson import Lesson
from simclass.models.session import Session

logger = logging.getLogger(__name__)

PLAN_EXECUTION_PROMPT = """\
你是一个教学观察专家。以下是一份教案计划和实际的课堂时间线记录。
请对教师的教案执行情况进行详细分析。

## 教案计划

课题：{title}
计划总时长：{duration_minutes} 分钟

### 教学环节
{phases_text}

## 实际课堂时间线
{timeline_text}

## 请分析

1. 每个教案环节是否被执行了？（跳过 / 完成 / 部分完成）
2. 每个环节的实际用时 vs 计划用时
3. 各环节的知识点 key_points 是否在教师的讲解中被覆盖到
4. 环节之间的衔接是否流畅（是否有长时间停顿、跳跃、倒回）
5. 整体时间分配是否合理

## 输出格式

用中文 Markdown 格式输出：
- 总览表格：每个环节的计划时间 / 实际时间 / 完成度 / 知识点覆盖率
- 亮点（做得好的地方）
- 改进建议（具体、可操作）
"""

QA_CHECK_PROMPT = """\
你是一个教学评估专家。以下是课堂中学生提出的预设问题、参考答案，以及教师的实际回答。
请评估教师回答每个预设问题的质量。

## 预设问题列表

{questions_text}

## 课堂完整时间线（用于找到教师对每个问题的回答）

{timeline_text}

## 请逐一评估教师的回答

1. 准确性：教师的回答是否正确？与参考答案对比
2. 清晰度：教师的解释是否通俗易懂？适合学生水平？
3. 完整性：是否涵盖了参考答案的核心要点？
4. 应变能力：如果教师偏离了参考答案但回答合理，应给予正面评价

注意：有些预设问题可能没有在课堂中被提出（学生没问），这种情况请标注"未提出"。

## 输出格式

用中文 Markdown 格式输出：
- 每个问题的评分（A/B/C/D）+ 点评
- 总体评价
- 建议教师加强的知识点
"""


class TeachingAnalyzer:
    """教学分析器：分析 session 数据，生成反馈报告。"""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _format_phases(self, lesson: Lesson) -> str:
        lines = []
        for i, p in enumerate(lesson.phases, 1):
            kp = "、".join(p.key_points) if p.key_points else "无"
            lines.append(
                f"{i}. **{p.name}**（{p.duration_minutes} 分钟）\n"
                f"   说明：{p.description}\n"
                f"   关键知识点：{kp}"
            )
        return "\n\n".join(lines)

    def _format_timeline(self, session: Session) -> str:
        lines = []
        for ev in session.timeline:
            minutes = ev.t / 60
            if ev.type == "teacher_speech":
                lines.append(f"[{minutes:05.1f}min] 教师: {ev.text}")
            elif ev.type == "student_action":
                lines.append(f"[{minutes:05.1f}min] {ev.speaker}({ev.action_type}): {ev.text}")
            elif ev.type == "phase_change":
                lines.append(f"[{minutes:05.1f}min] --- 环节切换: {ev.text} ---")
        return "\n".join(lines)

    def _format_questions(self, lesson: Lesson) -> str:
        lines = []
        for i, q in enumerate(lesson.preset_questions, 1):
            lines.append(
                f"{i}. 问题（{q.asked_by} 提出，难度={q.difficulty}）：{q.question}\n"
                f"   参考答案：{q.reference_answer}"
            )
        return "\n\n".join(lines)

    async def analyze_plan_execution(self, lesson: Lesson, session: Session) -> str:
        """功能 1：教案执行检查。"""
        prompt = PLAN_EXECUTION_PROMPT.format(
            title=lesson.title,
            duration_minutes=lesson.duration_minutes,
            phases_text=self._format_phases(lesson),
            timeline_text=self._format_timeline(session),
        )
        return await self.llm.analyze(
            messages=[{"role": "user", "content": prompt}],
        )

    async def analyze_qa_quality(self, lesson: Lesson, session: Session) -> str:
        """功能 2：预设问题回答检查。"""
        if not lesson.preset_questions:
            return "本次教案没有配置预设问题，跳过 Q&A 分析。"

        prompt = QA_CHECK_PROMPT.format(
            questions_text=self._format_questions(lesson),
            timeline_text=self._format_timeline(session),
        )
        return await self.llm.analyze(
            messages=[{"role": "user", "content": prompt}],
        )

    async def generate_report(self, lesson: Lesson, session: Session) -> str:
        """生成完整分析报告（Markdown）。"""
        plan_analysis = await self.analyze_plan_execution(lesson, session)
        qa_analysis = await self.analyze_qa_quality(lesson, session)

        report = f"""\
# 教学分析报告

## 课程信息
- **课题**：{lesson.title}
- **计划时长**：{lesson.duration_minutes} 分钟
- **实际时长**：{session.duration_seconds / 60:.1f if session.duration_seconds else '未知'} 分钟
- **学生数量**：{len(lesson.students)} 人
- **预设问题**：{len(lesson.preset_questions)} 个
- **会话 ID**：{session.session_id}

---

## 一、教案执行分析

{plan_analysis}

---

## 二、预设问题回答分析

{qa_analysis}
"""
        return report

    async def generate_and_save_report(
        self,
        lesson: Lesson,
        session: Session,
        output_dir: Path,
    ) -> Path:
        """生成报告并保存到文件。"""
        report = await self.generate_report(lesson, session)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "report.md"
        path.write_text(report, encoding="utf-8")
        logger.info("Report saved to %s", path)
        return path
