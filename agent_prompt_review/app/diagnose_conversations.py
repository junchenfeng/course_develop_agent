"""Batch-diagnose all conversations using Azure OpenAI Responses API (GPT-5.4).

Reads each conversation from data/conversations/jsonl/, sends it along with
the analysis prompt template and original agent prompt via the Responses API,
and saves the diagnosis to data/diagnosis/{conversation_id}.md.

Supports resuming: existing diagnosis files are skipped.

Usage:
    poetry run apr-diagnose
    python -m agent_prompt_review.app.diagnose_conversations
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, RateLimitError

from agent_prompt_review.app.paths import (
    AGENT_PROMPT_PATH,
    DIAGNOSIS_DIR,
    JSONL_DIR,
    REPO_ROOT,
    TEMPLATE_PATH,
)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 5  # seconds


def _normalize_base_url(raw: str) -> str:
    """Ensure base_url ends with /openai/v1/ for the Responses API SDK."""
    raw = raw.rstrip("/")
    if raw.endswith("/openai/v1"):
        return raw + "/"
    # Strip REST-style suffixes like /openai/responses?api-version=...
    for suffix in ("/openai/responses", "/openai/deployments"):
        idx = raw.find(suffix)
        if idx != -1:
            raw = raw[:idx]
            break
    if "?" in raw:
        raw = raw.split("?")[0].rstrip("/")
    return raw + "/openai/v1/"


def load_env():
    load_dotenv(REPO_ROOT / ".env")
    base_url_raw = os.getenv("AZURE_OPENAI_BASE_URL") or os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DIAGNOSIS_DEPLOYMENT", "gpt-5.4")
    concurrency = int(os.getenv("DIAGNOSIS_MAX_CONCURRENCY", "5"))
    if not base_url_raw or not api_key:
        print("Error: AZURE_OPENAI_BASE_URL and AZURE_OPENAI_API_KEY must be set.")
        print("Copy .env.example to .env and fill in your Azure credentials.")
        sys.exit(1)
    base_url = _normalize_base_url(base_url_raw)
    return base_url, api_key, deployment, concurrency


def format_conversation(jsonl_path: Path) -> tuple[str, dict]:
    """Read a JSONL file and format it as readable dialogue.

    Returns (formatted_text, metadata_dict).
    """
    messages = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                messages.append(json.loads(line))

    if not messages:
        return "", {}

    user_msgs = [m for m in messages if m["role"] == "user"]

    first_time = messages[0].get("timestamp", "")
    last_time = messages[-1].get("timestamp", "")

    lines = []
    for msg in messages:
        role_label = "User" if msg["role"] == "user" else "Agent"
        lines.append(f"## {role_label}\n{msg['content']}\n")

    metadata = {
        "conversation_id": jsonl_path.stem,
        "message_count": len(user_msgs),
        "first_time": first_time,
        "last_time": last_time,
    }

    return "\n---\n\n".join(lines), metadata


async def diagnose_one(
    client: AsyncOpenAI,
    deployment: str,
    sem: asyncio.Semaphore,
    template_text: str,
    agent_prompt_text: str,
    jsonl_path: Path,
    idx: int,
    total: int,
) -> bool:
    """Diagnose a single conversation. Returns True on success."""
    cid = jsonl_path.stem
    out_path = DIAGNOSIS_DIR / f"{cid}.md"

    if out_path.exists():
        print(f"  [{idx}/{total}] {cid} — already diagnosed, skipping")
        return True

    conversation_text, meta = format_conversation(jsonl_path)
    if not conversation_text:
        print(f"  [{idx}/{total}] {cid} — empty conversation, skipping")
        return True

    instructions = template_text.replace("{agent_prompt}", agent_prompt_text)
    instructions = instructions.replace("{conversation}", conversation_text)

    user_content = (
        f"对话ID: {meta['conversation_id']}，"
        f"共 {meta['message_count']} 轮，"
        f"时间 {meta['first_time']} ~ {meta['last_time']}。"
        f"\n\n请严格按照上述分析框架对该对话进行全面诊断。"
        f"在关键发现中，请务必引用出问题时的原始对话上下文片段，并追溯到 prompt 的具体规则。"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with sem:
                print(f"  [{idx}/{total}] {cid} (attempt {attempt})...")
                t0 = time.time()
                response = await client.responses.create(
                    model=deployment,
                    instructions=instructions,
                    input=user_content,
                    max_output_tokens=4096,
                    temperature=0.3,
                    store=False,
                )
                elapsed = time.time() - t0

            result = response.output_text

            header = f"""# 对话诊断: {cid}

- 消息轮数: {meta['message_count']}
- 时间范围: {meta['first_time']} ~ {meta['last_time']}
- 诊断模型: {deployment}
- 耗时: {elapsed:.1f}s

---

"""
            out_path.write_text(header + result, encoding="utf-8")
            print(f"  [{idx}/{total}] {cid} — done ({elapsed:.1f}s)")
            return True

        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"  [{idx}/{total}] {cid} — {type(e).__name__}, retrying in {delay}s...")
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"  [{idx}/{total}] {cid} — unexpected error: {e}")
            if attempt == MAX_RETRIES:
                return False
            await asyncio.sleep(RETRY_BASE_DELAY)

    print(f"  [{idx}/{total}] {cid} — failed after {MAX_RETRIES} retries")
    return False


async def async_main():
    base_url, api_key, deployment, concurrency = load_env()

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    DIAGNOSIS_DIR.mkdir(parents=True, exist_ok=True)

    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    agent_prompt_text = AGENT_PROMPT_PATH.read_text(encoding="utf-8")

    jsonl_files = sorted(JSONL_DIR.glob("*.jsonl"))
    total = len(jsonl_files)
    print(f"Found {total} conversations to diagnose")
    print(f"Using deployment: {deployment}")
    print(f"Base URL: {base_url}")
    print(f"Max concurrency: {concurrency}")
    print(f"Output directory: {DIAGNOSIS_DIR}\n")

    sem = asyncio.Semaphore(concurrency)

    tasks = [
        diagnose_one(client, deployment, sem, template_text, agent_prompt_text, p, i + 1, total)
        for i, p in enumerate(jsonl_files)
    ]

    results = await asyncio.gather(*tasks)

    succeeded = sum(1 for r in results if r)
    failed = total - succeeded
    existing = sum(1 for p in jsonl_files if (DIAGNOSIS_DIR / f"{p.stem}.md").exists())

    print("\nDiagnosis complete:")
    print(f"  Total conversations: {total}")
    print(f"  Succeeded: {succeeded}")
    print(f"  Failed: {failed}")
    print(f"  Files in diagnosis/: {existing}")

    await client.close()


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
