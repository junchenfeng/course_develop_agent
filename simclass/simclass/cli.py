"""SimClass CLI — 命令行入口。"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import signal
import time
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from simclass import __version__
from simclass.config import load_config
from simclass.models.lesson import Lesson
from simclass.models.session import EventType, Session, TimelineEvent

app = typer.Typer(
    name="simclass",
    help="SimClass — AI 模拟学生备课练习系统",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # 第三方库日志降级
    for name in ("httpx", "httpcore", "openai", "websockets"):
        logging.getLogger(name).setLevel(logging.WARNING)


@app.command()
def validate(
    lesson_file: Path = typer.Argument(..., help="教案 YAML 文件路径"),
) -> None:
    """验证教案 YAML 格式。"""
    from simclass.ui.terminal import print_error, print_lesson_info, print_success

    try:
        lesson = Lesson.from_yaml(lesson_file)
        print_success(f"教案验证通过: {lesson_file}")
        print_lesson_info(lesson)
    except Exception as e:
        print_error(f"教案验证失败: {e}")
        raise typer.Exit(1) from None


@app.command()
def start(
    lesson_file: Path = typer.Argument(..., help="教案 YAML 文件路径"),
    no_screen: bool = typer.Option(False, "--no-screen", help="不录制屏幕"),
    no_audio: bool = typer.Option(False, "--no-audio", help="不录制音频（同时禁用 STT 语音识别）"),
    stt: str = typer.Option("", "--stt", help="STT 提供商 (seedasr/deepgram)"),
    llm: str = typer.Option("", "--llm", help="Agent LLM 模型 (OpenRouter model ID)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细日志"),
) -> None:
    """启动模拟练课。"""
    _setup_logging(verbose)
    asyncio.run(_start_session(lesson_file, no_screen, no_audio, stt, llm))


async def _start_session(
    lesson_file: Path,
    no_screen: bool,
    no_audio: bool,
    stt_override: str,
    llm_override: str,
) -> None:
    from simclass.agents.llm_client import LLMClient
    from simclass.agents.student_agent import AgentAction, StudentAgent
    from simclass.services.orchestrator import Orchestrator
    from simclass.ui import terminal as ui

    # 1. 加载配置和教案
    config = load_config()
    if stt_override:
        config.stt_provider = stt_override
    if llm_override:
        config.llm.agent_model = llm_override

    try:
        lesson = Lesson.from_yaml(lesson_file)
    except Exception as e:
        ui.print_error(f"教案加载失败: {e}")
        return

    ui.print_banner()
    ui.print_lesson_info(lesson)

    # 2. 创建会话
    session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_dir = config.sessions_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # 保存教案副本
    shutil.copy2(lesson_file, session_dir / "lesson.yaml")

    session = Session(
        session_id=session_id,
        lesson_title=lesson.title,
        lesson_path=str(lesson_file),
    )
    session.add_event(TimelineEvent(
        t=0,
        type=EventType.SESSION_START,
        text=f"练课开始: {lesson.title}",
    ))

    # 3. 初始化 LLM 和 Agents
    llm_client = LLMClient(config.llm)
    agents = [
        StudentAgent(profile=sp, llm=llm_client)
        for sp in lesson.students
    ]

    # 4. 初始化 Orchestrator
    async def on_student_action(action: AgentAction) -> None:
        ui.print_student_action(action, session.elapsed / 60)

    async def on_phase_change(name: str, idx: int) -> None:
        ui.print_phase_change(name, idx)

    orchestrator = Orchestrator(
        lesson=lesson,
        agents=agents,
        session=session,
        on_student_action=on_student_action,
        on_phase_change=on_phase_change,
    )

    # 5. 初始化 STT（如果 no_audio 则跳过 STT）
    stt_service = None if no_audio else _create_stt_service(config)

    # 6. 初始化录制（仅在需要时创建）
    audio_recorder = None
    screen_recorder = None

    if not no_audio and stt_service is not None:
        # 有 STT 时才需要音频录制（音频数据同时送 STT 和录制）
        from simclass.services.recorder import AudioRecorder

        audio_recorder = AudioRecorder(config.recorder)
    elif not no_audio:
        # 没有 STT 但用户没有明确 --no-audio：尝试录制音频（可能失败则优雅降级）
        try:
            from simclass.services.recorder import AudioRecorder

            audio_recorder = AudioRecorder(config.recorder)
        except Exception:
            console.print("[yellow]⚠ 音频录制初始化失败，已跳过[/]")

    if not no_screen:
        try:
            from simclass.services.recorder import ScreenRecorder

            screen_recorder = ScreenRecorder(config.recorder)
        except Exception:
            console.print("[yellow]⚠ 屏幕录制初始化失败，已跳过[/]")

    # 7. 启动
    loop = asyncio.get_event_loop()
    audio_queue = None

    if audio_recorder is not None:
        audio_queue = audio_recorder.subscribe()
        audio_recorder.start(loop)

    if screen_recorder is not None:
        screen_recorder.start(session_dir)

    if stt_service is not None:
        await stt_service.connect()

    ui.print_session_start(session_id)

    # 8. 主循环
    stop_event = asyncio.Event()

    def _signal_handler(sig, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)

    try:
        if stt_service is not None and audio_queue is not None:
            # 启动两个并行任务：发送音频 + 处理 STT 结果
            await asyncio.gather(
                _feed_audio_to_stt(audio_queue, stt_service, stop_event),
                _process_stt_results(stt_service, orchestrator, session, stop_event),
            )
        else:
            # 没有 STT 配置：使用文字输入模式
            await _text_input_loop(orchestrator, session, stop_event)

    except asyncio.CancelledError:
        pass
    finally:
        # 9. 清理
        if audio_recorder is not None:
            audio_recorder.stop()
        if stt_service is not None:
            await stt_service.close()
        if screen_recorder is not None:
            screen_recorder.stop()

        session.end()
        session.add_event(TimelineEvent(
            t=session.elapsed,
            type=EventType.SESSION_END,
            text="练课结束",
        ))

        # 10. 保存
        session.save(session_dir)
        if audio_recorder is not None:
            audio_recorder.save_wav(session_dir / "audio.wav")
        if screen_recorder is not None:
            screen_recorder.encode_video(session_dir / "screen.mp4")

        ui.print_session_end(
            session.duration_seconds or 0,
            str(session_dir),
        )


def _create_stt_service(config):
    """根据配置创建 STT 服务实例。"""
    from simclass.services.stt import DeepgramService, SeedASRService

    if config.stt_provider == "seedasr":
        if not config.seed_asr.app_id:
            console.print("[yellow]⚠ SeedASR 未配置 (SEED_ASR_APP_ID)，将使用文字输入模式[/]")
            return None
        return SeedASRService(config.seed_asr)
    elif config.stt_provider == "deepgram":
        if not config.deepgram.api_key:
            console.print("[yellow]⚠ Deepgram 未配置 (DEEPGRAM_API_KEY)，将使用文字输入模式[/]")
            return None
        return DeepgramService(config.deepgram)
    else:
        console.print(f"[yellow]⚠ 未知 STT 提供商 '{config.stt_provider}'，将使用文字输入模式[/]")
        return None


async def _feed_audio_to_stt(audio_queue, stt_service, stop_event):
    """从音频队列读取 chunk，发送到 STT 服务。"""
    while not stop_event.is_set():
        try:
            chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.5)
            if chunk == b"":
                break
            await stt_service.send_audio(chunk)
        except TimeoutError:
            continue


async def _process_stt_results(stt_service, orchestrator, session, stop_event):
    """处理 STT 识别结果，触发 Orchestrator。"""
    from simclass.ui import terminal as ui

    async for result in stt_service.results():
        if stop_event.is_set():
            break
        if result.is_final and result.text.strip():
            ui.print_teacher_speech(result.text, session.elapsed / 60)
            await orchestrator.on_teacher_utterance(result.text)
        elif not result.is_final:
            ui.print_stt_interim(result.text)


async def _text_input_loop(orchestrator, session, stop_event):
    """文字输入模式（STT 不可用时的 fallback）。"""
    from simclass.ui import terminal as ui

    console.print("[yellow]📝 文字输入模式：输入教师讲话内容，按回车发送。输入 q 退出。[/]\n")

    while not stop_event.is_set():
        try:
            text = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("👨‍🏫 教师> ")
            )
        except EOFError:
            break

        if text.strip().lower() in ("q", "quit", "exit"):
            stop_event.set()
            break

        if text.strip():
            ui.print_teacher_speech(text, session.elapsed / 60)
            await orchestrator.on_teacher_utterance(text)


@app.command()
def sessions(
    sessions_dir: Path = typer.Option("./sessions", "--dir", help="会话存储目录"),
) -> None:
    """列出历史会话。"""
    from simclass.ui import terminal as ui

    sessions_path = Path(sessions_dir)
    if not sessions_path.exists():
        ui.print_error(f"目录不存在: {sessions_path}")
        raise typer.Exit(1)

    dirs = sorted(sessions_path.iterdir())
    if not dirs:
        console.print("[dim]暂无历史会话[/]")
        return

    from rich.table import Table

    table = Table(title="历史会话", show_header=True, header_style="bold magenta")
    table.add_column("会话 ID", style="cyan")
    table.add_column("课题")
    table.add_column("时长")
    table.add_column("报告")

    for d in dirs:
        if not d.is_dir():
            continue
        timeline_file = d / "timeline.json"
        if not timeline_file.exists():
            continue
        data = json.loads(timeline_file.read_text())
        title = data.get("lesson_title", "?")
        dur = data.get("duration_seconds")
        dur_str = f"{dur / 60:.1f}min" if dur else "进行中"
        has_report = "✅" if (d / "report.md").exists() else "❌"
        table.add_row(d.name, title, dur_str, has_report)

    console.print(table)


@app.command()
def analyze(
    session_path: Path = typer.Argument(..., help="会话目录路径"),
    model: str = typer.Option("", "--model", help="分析用的 LLM 模型"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """分析一次练课，生成教学反馈报告。"""
    _setup_logging(verbose)
    asyncio.run(_analyze_session(session_path, model))


async def _analyze_session(session_path: Path, model_override: str) -> None:
    from simclass.agents.llm_client import LLMClient
    from simclass.services.analyzer import TeachingAnalyzer
    from simclass.ui import terminal as ui

    config = load_config()
    if model_override:
        config.llm.analyzer_model = model_override

    # 加载数据
    lesson_file = session_path / "lesson.yaml"
    timeline_file = session_path / "timeline.json"

    if not lesson_file.exists() or not timeline_file.exists():
        ui.print_error(f"会话数据不完整，需要 lesson.yaml 和 timeline.json: {session_path}")
        return

    lesson = Lesson.from_yaml(lesson_file)
    session_data = json.loads(timeline_file.read_text())
    session = Session.model_validate(session_data)

    ui.print_banner()
    console.print(f"[bold]正在分析会话: {session_path.name}[/]\n")

    llm_client = LLMClient(config.llm)
    analyzer = TeachingAnalyzer(llm_client)

    with console.status("[bold green]正在生成分析报告..."):
        report_path = await analyzer.generate_and_save_report(lesson, session, session_path)

    ui.print_success(f"报告已保存到: {report_path}")
    console.print()
    report_text = report_path.read_text()
    ui.print_report(report_text)


@app.command()
def report(
    session_path: Path = typer.Argument(..., help="会话目录路径"),
) -> None:
    """查看分析报告。"""
    from simclass.ui import terminal as ui

    report_file = session_path / "report.md"
    if not report_file.exists():
        ui.print_error(f"报告不存在。请先运行 simclass analyze {session_path}")
        raise typer.Exit(1)

    ui.print_banner()
    ui.print_report(report_file.read_text())


@app.command()
def replay(
    session_path: Path = typer.Argument(..., help="会话目录路径"),
    speed: float = typer.Option(3.0, "--speed", help="回放速度倍率"),
) -> None:
    """回放一次练课的时间线（文字回放）。"""
    from simclass.ui import terminal as ui

    timeline_file = session_path / "timeline.json"
    if not timeline_file.exists():
        ui.print_error(f"时间线不存在: {session_path}")
        raise typer.Exit(1)

    data = json.loads(timeline_file.read_text())
    events = data.get("timeline", [])

    ui.print_banner()
    console.print(f"[bold]回放会话: {data.get('lesson_title', '?')}[/]")
    console.print(f"[dim]速度: {speed}x[/]\n")

    prev_t = 0.0
    for ev in events:
        t = ev.get("t", 0)
        wait = (t - prev_t) / speed
        if wait > 0:
            time.sleep(wait)
        prev_t = t

        minutes = t / 60
        ev_type = ev.get("type", "")
        text = ev.get("text", "")
        speaker = ev.get("speaker", "")

        if ev_type == "teacher_speech":
            console.print(f"  [dim][{minutes:05.1f}][/] [bold]👨\u200d🏫 教师:[/] {text}")
        elif ev_type == "student_action":
            ev.get("action_type", "")
            console.print(f"  [dim][{minutes:05.1f}][/] [green]💬 {speaker}:[/] {text}")
        elif ev_type == "phase_change":
            console.print(f"\n  [yellow]📋 环节切换 → {text}[/]\n")
        elif ev_type == "session_start":
            console.print(f"  [green]▶ {text}[/]")
        elif ev_type == "session_end":
            console.print(f"  [blue]■ {text}[/]")

    console.print("\n[bold]回放结束[/]")


@app.command()
def version() -> None:
    """显示版本号。"""
    console.print(f"SimClass v{__version__}")


def app_entry() -> None:
    """Package entry point."""
    app()


if __name__ == "__main__":
    app()
