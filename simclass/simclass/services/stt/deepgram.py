"""Deepgram Nova-3 流式 STT（fallback 方案）。

文档: https://developers.deepgram.com/docs/getting-started-with-live-streaming-audio
"""

from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import AsyncIterator

import websockets
from websockets.asyncio.client import ClientConnection

from simclass.config import DeepgramConfig
from simclass.services.stt.base import STTBase, STTResult

logger = logging.getLogger(__name__)

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramService(STTBase):
    """Deepgram WebSocket 流式 STT。"""

    def __init__(self, config: DeepgramConfig) -> None:
        self.config = config
        self._ws: ClientConnection | None = None

    async def connect(self) -> None:
        params = (
            f"?model={self.config.model}"
            f"&language={self.config.language}"
            f"&encoding=linear16"
            f"&sample_rate=16000"
            f"&channels=1"
            f"&punctuate=true"
            f"&interim_results=true"
            f"&endpointing=300"
        )
        headers = {"Authorization": f"Token {self.config.api_key}"}
        self._ws = await websockets.connect(
            DEEPGRAM_WS_URL + params,
            additional_headers=headers,
        )
        logger.info("Deepgram connected")

    async def send_audio(self, chunk: bytes) -> None:
        if self._ws is None:
            raise RuntimeError("Deepgram not connected")
        await self._ws.send(chunk)

    async def results(self) -> AsyncIterator[STTResult]:
        if self._ws is None:
            raise RuntimeError("Deepgram not connected")
        async for message in self._ws:
            if isinstance(message, str):
                data = json.loads(message)
                transcript = (
                    data.get("channel", {})
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
                if transcript:
                    is_final = data.get("is_final", False)
                    yield STTResult(text=transcript, is_final=is_final)

    async def close(self) -> None:
        if self._ws:
            with contextlib.suppress(Exception):
                await self._ws.send(json.dumps({"type": "CloseStream"}))
            await self._ws.close()
            self._ws = None
            logger.info("Deepgram disconnected")
