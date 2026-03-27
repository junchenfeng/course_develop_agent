"""CLI：从课程目录中的 activity_design.md 生成同课次的 ppt_outline.md。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[misc, assignment]

from src.openrouter_client import OpenRouterError, chat_completions
from src.prompts import build_messages

ACTIVITY_FILENAME = "activity_design.md"
OUTLINE_FILENAME = "ppt_outline.md"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _normalize_level(level: str) -> str:
    s = level.strip().lower()
    if s in ("1", "level_1", "level1", "l1"):
        return "level_1"
    if s in ("2", "level_2", "level2", "l2"):
        return "level_2"
    raise ValueError(f"无效的 stage：{level!r}，应为 level_1 / level_2（或 1 / 2）")


def _normalize_unit(unit: str) -> str:
    s = unit.strip()
    if re.fullmatch(r"\d+", s):
        return f"unit_{int(s)}"
    m = re.fullmatch(r"unit[_\s]?(\d+)", s, re.IGNORECASE)
    if m:
        return f"unit_{int(m.group(1))}"
    raise ValueError(f"无效的单元：{unit!r}，示例：6、unit_6")


def _normalize_lesson(lesson: str) -> str:
    s = lesson.strip()
    if re.fullmatch(r"\d+", s):
        return f"lesson_{int(s)}"
    m = re.fullmatch(r"lesson[_\s]?(\d+)", s, re.IGNORECASE)
    if m:
        return f"lesson_{int(m.group(1))}"
    raise ValueError(f"无效的课次：{lesson!r}，示例：1、lesson_1")


def _lesson_dir(course_root: Path, level: str, unit: str, lesson: str) -> Path:
    return course_root / level / unit / lesson


def _read_activity_file(lesson_path: Path) -> Path:
    p = lesson_path / ACTIVITY_FILENAME
    if not p.is_file():
        raise FileNotFoundError(
            f"未找到教学活动设计文件: {p}（请在该课次目录下放置 {ACTIVITY_FILENAME}）"
        )
    return p


def _read_design_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"文件为空: {path}")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="读取 course 目录下某课次的 activity_design.md，生成同目录的 ppt_outline.md。",
    )
    parser.add_argument(
        "--level",
        required=True,
        help="阶段：level_1（基础启航班）或 level_2（进阶智造营），也可写 1 / 2",
    )
    parser.add_argument(
        "--unit",
        required=True,
        help="单元：如 6 或 unit_6",
    )
    parser.add_argument(
        "--lesson",
        required=True,
        help="课次：如 1 或 lesson_1",
    )
    parser.add_argument(
        "--course-root",
        type=Path,
        default=None,
        help="课程根目录（默认：<仓库根>/course）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"覆盖输出路径（默认：<课次目录>/{OUTLINE_FILENAME}）",
    )
    args = parser.parse_args(argv)

    root = _repo_root()
    if load_dotenv is not None:
        load_dotenv(root / ".env")

    course_root = args.course_root
    if course_root is None:
        course_root = root / "course"
    else:
        course_root = course_root.expanduser().resolve()

    try:
        level = _normalize_level(args.level)
        unit = _normalize_unit(args.unit)
        lesson = _normalize_lesson(args.lesson)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    lesson_path = _lesson_dir(course_root, level, unit, lesson)
    try:
        activity_path = _read_activity_file(lesson_path)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    try:
        design_text = _read_design_text(activity_path)
    except (ValueError, OSError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    out_path = args.output
    if out_path is None:
        out_path = lesson_path / OUTLINE_FILENAME
    else:
        out_path = out_path.expanduser().resolve()

    messages = build_messages(design_text)
    try:
        outline = chat_completions(messages)
    except OpenRouterError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(outline + "\n", encoding="utf-8")
    except OSError as e:
        print(f"错误: 无法写入 {out_path}: {e}", file=sys.stderr)
        return 1

    print(f"已生成: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
