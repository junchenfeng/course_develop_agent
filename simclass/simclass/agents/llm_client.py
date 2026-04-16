"""LLM 调用客户端 — 统一封装 OpenRouter（兼容 openai SDK）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from simclass.config import LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMClient:
    """通过 OpenRouter 调用 LLM。使用 openai SDK 的 chat completions 接口。"""

    config: LLMConfig
    _client: AsyncOpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            default_headers={
                "HTTP-Referer": "https://simclass.dev",
                "X-Title": "SimClass",
            },
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.8,
        max_tokens: int = 256,
    ) -> str:
        """发送聊天请求，返回 assistant 回复文本。"""
        model = model or self.config.agent_model
        try:
            resp = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content or ""
            return content.strip()
        except Exception:
            logger.exception("LLM call failed (model=%s)", model)
            raise

    async def analyze(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """用于课后分析的调用，使用更强的模型和更长的输出。"""
        model = model or self.config.analyzer_model
        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
