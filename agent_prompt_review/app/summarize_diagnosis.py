"""Summarize all conversation diagnoses using Azure OpenAI Responses API (GPT-5.4 Pro).

Reads individual diagnosis files from data/diagnosis/, extracts summaries,
identifies the 5 lowest-scoring conversations for full inclusion, assembles
a comprehensive prompt, and calls GPT-5.4 Pro to generate a final report.

Usage:
    poetry run apr-summarize
    python -m agent_prompt_review.app.summarize_diagnosis
"""

import asyncio
import os
import re
import sys
import time

from dotenv import load_dotenv
from openai import AsyncOpenAI

from agent_prompt_review.app.paths import (
    AGENT_PROMPT_PATH,
    DIAGNOSIS_DIR,
    FINAL_REPORT_PATH,
    REPO_ROOT,
)


def _normalize_base_url(raw: str) -> str:
    """Ensure base_url ends with /openai/v1/ for the Responses API SDK."""
    raw = raw.rstrip("/")
    if raw.endswith("/openai/v1"):
        return raw + "/"
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
    deployment = os.getenv("AZURE_OPENAI_SUMMARY_DEPLOYMENT") or os.getenv(
        "AZURE_OPENAI_DIAGNOSIS_DEPLOYMENT", "gpt-5.4-pro"
    )
    if not base_url_raw or not api_key:
        print("Error: AZURE_OPENAI_BASE_URL and AZURE_OPENAI_API_KEY must be set.")
        sys.exit(1)
    base_url = _normalize_base_url(base_url_raw)
    return base_url, api_key, deployment


def extract_scores(text: str) -> dict[str, float]:
    """Extract dimension scores from a diagnosis file's rating table."""
    scores = {}
    dimension_names = ["引导性", "互动节奏", "练习充分性", "个性化适应", "情感支持", "教学连贯性"]

    for dim in dimension_names:
        pattern = rf"\|\s*{re.escape(dim)}\s*\|\s*([\d.]+)\s*\|"
        match = re.search(pattern, text)
        if match:
            scores[dim] = float(match.group(1))

    return scores


def compute_avg_score(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    return sum(scores.values()) / len(scores)


def extract_summary_section(text: str, max_chars: int = 1500) -> str:
    """Extract the rating table and key findings as a condensed summary."""
    lines = text.split("\n")
    summary_parts = []

    in_rating = False
    in_findings = False
    in_prompt_suggestions = False

    for line in lines:
        if "评分汇总" in line:
            in_rating = True
            in_findings = False
            in_prompt_suggestions = False
            summary_parts.append(line)
            continue
        if "关键发现" in line:
            in_rating = False
            in_findings = True
            in_prompt_suggestions = False
            summary_parts.append(line)
            continue
        if "Prompt 改进建议" in line or "Prompt改进建议" in line:
            in_rating = False
            in_findings = False
            in_prompt_suggestions = True
            summary_parts.append(line)
            continue

        if in_rating or in_findings or in_prompt_suggestions:
            summary_parts.append(line)

    summary = "\n".join(summary_parts)

    if len(summary) > max_chars:
        summary = summary[:max_chars] + "\n...(截断)"

    return summary


def load_diagnoses() -> list[dict]:
    """Load all diagnosis files and extract metadata + scores."""
    results = []
    diagnosis_files = sorted(DIAGNOSIS_DIR.glob("*.md"))

    for f in diagnosis_files:
        text = f.read_text(encoding="utf-8")
        scores = extract_scores(text)
        avg = compute_avg_score(scores)
        summary = extract_summary_section(text)
        results.append({
            "conversation_id": f.stem,
            "path": f,
            "full_text": text,
            "scores": scores,
            "avg_score": avg,
            "summary": summary,
        })

    return results


def build_summary_prompt(diagnoses: list[dict], agent_prompt: str) -> tuple[str, str]:
    """Build instructions and user input for the summarization call.

    Returns (instructions, user_input).
    """
    n = len(diagnoses)

    instructions = f"""你是一位资深的教育技术专家和教学设计师。

你将收到 {n} 段 AI 教学助手与学生的对话诊断结果。每段诊断由 GPT-5.4 完成，包含六维评分、关键发现和改进建议。

你的任务是综合分析所有诊断结果，撰写一份**全面的教学 Prompt 改善报告**。

报告必须包含以下部分：

1. **数据总览**：诊断覆盖的对话数量、评分分布统计（各维度的均值/中位数/最低分）
2. **共性问题排序**：按出现频率和严重程度排序的系统性问题，每个问题需说明：
   - 在多少段对话中出现
   - 具体表现（引用诊断中的典型案例）
   - 根本原因分析（追溯到 prompt 的哪条规则或缺失）
3. **分维度深度分析**：针对六个维度分别给出综合评价和改进方向
4. **Prompt 改善建议**：
   - 应**新增**的规则（含具体文本建议）
   - 应**修改**的现有规则（修改前后对比）
   - 应**删除**的规则及理由
   - 建议调整的**优先级排序**
5. **改善后的完整 Prompt**：给出修改后的完整 agent prompt，可以直接使用"""

    user_parts = []

    user_parts.append("## 当前教学 Agent 的 System Prompt\n")
    user_parts.append(f"```\n{agent_prompt}\n```\n")

    user_parts.append(f"\n## 全部 {n} 段对话诊断摘要\n")

    sorted_diags = sorted(diagnoses, key=lambda d: d["avg_score"])

    for i, d in enumerate(sorted_diags):
        score_str = ", ".join(f"{k}={v}" for k, v in d["scores"].items())
        user_parts.append(
            f"\n### 对话 {i+1}: {d['conversation_id']} (均分 {d['avg_score']:.1f})\n"
        )
        user_parts.append(f"评分: {score_str}\n")
        user_parts.append(d["summary"])
        user_parts.append("\n")

    worst_5 = sorted_diags[:5]
    user_parts.append("\n## 评分最低的 5 段对话完整诊断\n")
    user_parts.append("以下包含完整诊断内容（含原始对话上下文引用），供深入分析：\n")

    for d in worst_5:
        user_parts.append(f"\n### 完整诊断: {d['conversation_id']} (均分 {d['avg_score']:.1f})\n")
        user_parts.append(d["full_text"])
        user_parts.append("\n")

    user_parts.append("\n---\n")
    user_parts.append(
        "请基于以上全部诊断数据，按照要求的格式撰写综合改善报告。"
        "重点关注出现频率最高和影响最严重的问题。"
    )

    return instructions, "\n".join(user_parts)


async def async_main():
    base_url, api_key, deployment = load_env()

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    diagnoses = load_diagnoses()
    if not diagnoses:
        print("No diagnosis files found in", DIAGNOSIS_DIR)
        print("Run `poetry run apr-diagnose` first.")
        sys.exit(1)

    print(f"Loaded {len(diagnoses)} diagnosis files")

    agent_prompt = AGENT_PROMPT_PATH.read_text(encoding="utf-8")

    instructions, user_input = build_summary_prompt(diagnoses, agent_prompt)

    total_chars = len(instructions) + len(user_input)
    approx_tokens = total_chars // 2  # rough estimate for CJK
    print(f"Prompt size: ~{total_chars:,} chars (~{approx_tokens:,} tokens est.)")
    print(f"Using deployment: {deployment}")
    print(f"Base URL: {base_url}")
    print(f"Output: {FINAL_REPORT_PATH}")
    print("Calling summary model…")

    t0 = time.time()
    response = await client.responses.create(
        model=deployment,
        instructions=instructions,
        input=user_input,
        max_output_tokens=16384,
        store=False,
    )
    elapsed = time.time() - t0

    result = response.output_text

    if not result:
        print("Warning: output_text is empty. Inspecting response…", file=sys.stderr)
        print(f"  status: {response.status}", file=sys.stderr)
        print(f"  output count: {len(response.output)}", file=sys.stderr)
        if response.output:
            for i, item in enumerate(response.output):
                print(f"  output[{i}] type={item.type}", file=sys.stderr)
                if hasattr(item, "content"):
                    for j, c in enumerate(item.content):
                        print(f"    content[{j}] type={c.type}, text len={len(c.text) if hasattr(c, 'text') else 'N/A'}", file=sys.stderr)
        if hasattr(response, "incomplete_details") and response.incomplete_details:
            print(f"  incomplete_details: {response.incomplete_details}", file=sys.stderr)
        if hasattr(response, "error") and response.error:
            print(f"  error: {response.error}", file=sys.stderr)

        # Try to extract text manually
        for item in response.output:
            if hasattr(item, "content"):
                for c in item.content:
                    if hasattr(c, "text") and c.text:
                        result = c.text
                        print(f"  Found text via manual extraction ({len(result)} chars)", file=sys.stderr)
                        break
            if result:
                break

    if not result:
        print("Error: model returned no extractable content.", file=sys.stderr)
        sys.exit(1)

    usage = response.usage
    u_in = getattr(usage, "input_tokens", None) if usage else None
    u_out = getattr(usage, "output_tokens", None) if usage else None
    u_total = getattr(usage, "total_tokens", None) if usage else None
    usage_line = (
        f"input={u_in:,}, output={u_out:,}, total={u_total:,}"
        if u_in is not None and u_out is not None and u_total is not None
        else "usage n/a"
    )

    header = f"""# 教学 Prompt 综合改善报告

> 基于 {len(diagnoses)} 段对话的逐一诊断结果，由汇总模型（部署: {deployment}）综合分析生成。
> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
> 耗时: {elapsed:.1f}s
> Token 使用: {usage_line}

---

"""
    FINAL_REPORT_PATH.write_text(header + result, encoding="utf-8")
    print(f"\nDone! Report saved to {FINAL_REPORT_PATH}")
    print(f"  Time: {elapsed:.1f}s")
    if u_in is not None:
        print(f"  Tokens: input={u_in:,}, output={u_out:,}")

    await client.close()


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
