"""STT 抽象接口。"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class STTResult:
    """一次 STT 识别结果。"""

    text: str
    is_final: bool


class STTBase(abc.ABC):
    """STT 服务的抽象基类。子类需实现 connect / send_audio / close。"""

    @abc.abstractmethod
    async def connect(self) -> None:
        """建立到 STT 服务的连接。"""

    @abc.abstractmethod
    async def send_audio(self, chunk: bytes) -> None:
        """发送一个音频块。"""

    @abc.abstractmethod
    async def results(self) -> AsyncIterator[STTResult]:
        """异步迭代 STT 识别结果。"""
        yield  # type: ignore[misc]

    @abc.abstractmethod
    async def close(self) -> None:
        """关闭连接。"""
