"""OpenRouter Chat Completions API 客户端。"""

from __future__ import annotations

import json
import os
from typing import Any

import requests

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3.1-pro-preview"
DEFAULT_TIMEOUT = 120


class OpenRouterError(Exception):
    """API 或解析错误。"""


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise OpenRouterError(
            "未设置环境变量 OPENROUTER_API_KEY。请 export 该变量，或在项目根目录放置 .env 文件。"
        )
    return key


def chat_completions(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    调用 OpenRouter，返回助手文本内容。
    """
    api_key = get_api_key()
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # OpenRouter 建议的可选头，便于统计与展示
    referer = os.environ.get("OPENROUTER_HTTP_REFERER", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    title = os.environ.get("OPENROUTER_APP_TITLE", "course_develop_agent").strip()
    if title:
        headers["X-Title"] = title

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    try:
        resp = requests.post(
            OPENROUTER_CHAT_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise OpenRouterError(f"网络请求失败: {e}") from e

    if resp.status_code != 200:
        body_preview = (resp.text or "")[:800]
        raise OpenRouterError(
            f"OpenRouter 返回 HTTP {resp.status_code}。响应片段: {body_preview}"
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        raise OpenRouterError(f"无法解析 JSON 响应: {e}") from e

    choices = data.get("choices") or []
    if not choices:
        raise OpenRouterError(f"响应中无 choices 字段或为空: {json.dumps(data)[:500]}")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None or (isinstance(content, str) and not content.strip()):
        raise OpenRouterError("模型返回内容为空。")

    if isinstance(content, str):
        return content.strip()

    # 部分模型可能返回 content 为分段结构
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        merged = "\n".join(p for p in parts if p).strip()
        if not merged:
            raise OpenRouterError(f"无法从分段 content 中提取文本: {content!r}")
        return merged

    raise OpenRouterError(f"未知的 content 类型: {type(content)}")
