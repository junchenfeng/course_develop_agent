"""Repository-root paths for data and prompts (shared by review scripts)."""

from pathlib import Path

# agent_prompt_review/app/paths.py → repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CSV_PATH = DATA_DIR / "run_log.csv"
CONV_DIR = DATA_DIR / "conversations"
MD_DIR = CONV_DIR / "markdown"
JSONL_DIR = CONV_DIR / "jsonl"
SAMPLED_DIR = CONV_DIR / "sampled"
DIAGNOSIS_DIR = DATA_DIR / "diagnosis"
TEMPLATE_PATH = DATA_DIR / "analysis_prompt_template.md"
AGENT_PROMPT_PATH = DATA_DIR / "agent_prompt.md"
FINAL_REPORT_PATH = DATA_DIR / "final_report.md"
