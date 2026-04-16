"""终端 UI — 使用 rich 在终端中显示课堂状态和学生消息。"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from simclass.agents.student_agent import AgentAction
from simclass.models.lesson import Lesson

console = Console()

PERSONA_EMOJI = {
    "积极主动型": "🙋",
    "认真沉默型": "📝",
    "容易走神型": "😴",
}


def print_banner() -> None:
    console.print(
        Panel(
            "[bold cyan]SimClass[/] — AI 模拟学生备课练习系统",
            subtitle="v0.1.0",
            style="bold blue",
        )
    )


def print_lesson_info(lesson: Lesson) -> None:
    table = Table(title="教案信息", show_header=True, header_style="bold magenta")
    table.add_column("项目", style="cyan")
    table.add_column("内容")
    table.add_row("课题", lesson.title)
    table.add_row("时长", f"{lesson.duration_minutes} 分钟")
    table.add_row("环节数", str(len(lesson.phases)))
    table.add_row("学生数", str(len(lesson.students)))
    table.add_row("预设问题", str(len(lesson.preset_questions)))
    console.print(table)

    console.print("\n[bold]教学环节：[/]")
    for i, p in enumerate(lesson.phases, 1):
        console.print(f"  {i}. {p.name} ({p.duration_minutes}分钟) — {p.description}")

    console.print("\n[bold]学生角色：[/]")
    for s in lesson.students:
        emoji = PERSONA_EMOJI.get(s.persona, "👤")
        console.print(f"  {emoji} {s.name} [{s.persona}] 知识水平: {s.knowledge_level}")

    console.print()


def print_session_start(session_id: str) -> None:
    console.print(
        Panel(
            f"[bold green]练课开始！[/]\n"
            f"会话 ID: {session_id}\n"
            f"请开始授课，AI 学生会根据你的讲解做出反应。\n"
            f"按 [bold]Ctrl+C[/] 结束练课。",
            style="green",
        )
    )


def print_phase_change(phase_name: str, phase_idx: int) -> None:
    console.print(f"\n[bold yellow]📋 环节切换 → [{phase_idx + 1}] {phase_name}[/]\n")


def print_teacher_speech(text: str, elapsed_minutes: float) -> None:
    time_str = f"{elapsed_minutes:05.1f}"
    console.print(f"  [dim][{time_str}][/] [bold]👨\u200d🏫 教师:[/] {text}")


def print_student_action(action: AgentAction, elapsed_minutes: float) -> None:
    time_str = f"{elapsed_minutes:05.1f}"
    type_indicator = {
        "preset_question": "[yellow]❓[/]",
        "free_response": "[green]💬[/]",
        "forced_response": "[cyan]📢[/]",
        "reaction": "[dim]💭[/]",
    }.get(action.type, "💬")

    console.print(
        f"  [dim][{time_str}][/] {type_indicator} [bold]{action.student_name}:[/] {action.text}"
    )


def print_stt_interim(text: str) -> None:
    """显示 STT 中间结果（非 final）。"""
    console.print(f"  [dim italic]🎤 ...{text}[/]", end="\r")


def print_session_end(duration_seconds: float, session_dir: str) -> None:
    minutes = duration_seconds / 60
    console.print(
        Panel(
            f"[bold]练课结束！[/]\n"
            f"时长: {minutes:.1f} 分钟\n"
            f"数据保存到: {session_dir}\n\n"
            f"运行 [cyan]simclass analyze {session_dir}[/] 生成分析报告",
            style="bold blue",
        )
    )


def print_report(report_text: str) -> None:
    from rich.markdown import Markdown

    console.print(Markdown(report_text))


def print_error(message: str) -> None:
    console.print(f"[bold red]❌ 错误:[/] {message}")


def print_success(message: str) -> None:
    console.print(f"[bold green]✅[/] {message}")
