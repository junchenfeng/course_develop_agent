"""火山引擎 SeedASR 大模型流式语音识别。

协议文档: https://www.volcengine.com/docs/6561/1354869
使用 WebSocket 二进制协议进行双向流式通信。
"""

from __future__ import annotations

import contextlib
import gzip
import json
import logging
import struct
import uuid
from collections.abc import AsyncIterator

import websockets
from websockets.asyncio.client import ClientConnection

from simclass.config import SeedASRConfig
from simclass.services.stt.base import STTBase, STTResult

logger = logging.getLogger(__name__)

# SeedASR 二进制协议常量
PROTOCOL_VERSION = 0b0001
HEADER_SIZE = 0b0001  # 1 * 4 bytes
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
FULL_SERVER_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR = 0b1111
NO_SEQUENCE = 0b0000
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_WITH_SEQUENCE = 0b0011
NO_COMPRESSION = 0b0000
GZIP_COMPRESSION = 0b0001
JSON_SERIALIZATION = 0b0001


def _build_header(message_type: int, flags: int, serialization: int, compression: int) -> bytes:
    header = (PROTOCOL_VERSION << 28) | (HEADER_SIZE << 24) | (message_type << 20)
    header |= (flags << 16) | (serialization << 12) | (compression << 8)
    return struct.pack(">I", header)


def _build_full_client_request(payload: dict) -> bytes:
    payload_bytes = json.dumps(payload).encode("utf-8")
    payload_gz = gzip.compress(payload_bytes)
    header = _build_header(FULL_CLIENT_REQUEST, POS_SEQUENCE, JSON_SERIALIZATION, GZIP_COMPRESSION)
    return header + struct.pack(">I", len(payload_gz)) + payload_gz


def _build_audio_only_request(audio: bytes, is_last: bool = False) -> bytes:
    flags = NEG_WITH_SEQUENCE if is_last else POS_SEQUENCE
    header = _build_header(AUDIO_ONLY_REQUEST, flags, NO_COMPRESSION, NO_COMPRESSION)
    return header + struct.pack(">I", len(audio)) + audio


def _parse_response(data: bytes) -> STTResult | None:
    if len(data) < 4:
        return None

    header = struct.unpack(">I", data[:4])[0]
    message_type = (header >> 20) & 0xF
    compression = (header >> 8) & 0xF

    if message_type == SERVER_ACK:
        return None

    if message_type == SERVER_ERROR:
        logger.error("SeedASR server error: %s", data[8:].decode("utf-8", errors="replace"))
        return None

    if message_type != FULL_SERVER_RESPONSE:
        return None

    # Skip header (4 bytes), read sequence (4 bytes), payload size (4 bytes)
    if len(data) < 12:
        return None

    payload_size = struct.unpack(">I", data[8:12])[0]
    payload_bytes = data[12:12 + payload_size]

    if compression == GZIP_COMPRESSION:
        payload_bytes = gzip.decompress(payload_bytes)

    payload = json.loads(payload_bytes)
    text = payload.get("result", {}).get("text", "")
    is_final = payload.get("is_final", False)

    if not text:
        return None

    return STTResult(text=text, is_final=is_final)


class SeedASRService(STTBase):
    """火山引擎 SeedASR WebSocket 流式 STT。"""

    def __init__(self, config: SeedASRConfig) -> None:
        self.config = config
        self._ws: ClientConnection | None = None
        self._session_id = str(uuid.uuid4())

    async def connect(self) -> None:
        ws_url = self.config.ws_url
        headers = {
            "X-Api-App-Key": self.config.app_id,
            "X-Api-Access-Key": self.config.token,
            "X-Api-Resource-Id": "volc.seedasr.sauc.duration",
            "X-Api-Request-Id": self._session_id,
        }
        self._ws = await websockets.connect(ws_url, additional_headers=headers)

        # 发送 full client request（初始化）
        init_payload = {
            "user": {"uid": self._session_id},
            "audio": {
                "format": "pcm",
                "sample_rate": self.config.sample_rate,
                "bits": 16,
                "channel": 1,
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punctuation": True,
                "result_type": "single",
            },
        }
        await self._ws.send(_build_full_client_request(init_payload))
        logger.info("SeedASR connected, session=%s", self._session_id)

    async def send_audio(self, chunk: bytes) -> None:
        if self._ws is None:
            raise RuntimeError("SeedASR not connected")
        await self._ws.send(_build_audio_only_request(chunk, is_last=False))

    async def results(self) -> AsyncIterator[STTResult]:
        if self._ws is None:
            raise RuntimeError("SeedASR not connected")
        async for message in self._ws:
            if isinstance(message, bytes):
                result = _parse_response(message)
                if result:
                    yield result
            else:
                logger.debug("SeedASR text message: %s", message)

    async def close(self) -> None:
        if self._ws:
            # 发送最后一包（标记结束）
            with contextlib.suppress(Exception):
                await self._ws.send(_build_audio_only_request(b"", is_last=True))
            await self._ws.close()
            self._ws = None
            logger.info("SeedASR disconnected")
