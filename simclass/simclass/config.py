"""全局配置：从环境变量 / .env 文件加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass
class LLMConfig:
    """OpenRouter LLM 配置（兼容 openai SDK）。"""

    base_url: str = field(
        default_factory=lambda: _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )
    api_key: str = field(default_factory=lambda: _env("OPENROUTER_API_KEY"))
    agent_model: str = field(
        default_factory=lambda: _env("SIMCLASS_AGENT_MODEL", "openai/gpt-4o-mini")
    )
    analyzer_model: str = field(
        default_factory=lambda: _env("SIMCLASS_ANALYZER_MODEL", "openai/gpt-4o")
    )


@dataclass
class SeedASRConfig:
    """火山引擎 SeedASR 配置。"""

    app_id: str = field(default_factory=lambda: _env("SEED_ASR_APP_ID"))
    token: str = field(default_factory=lambda: _env("SEED_ASR_TOKEN"))
    cluster_id: str = field(
        default_factory=lambda: _env("SEED_ASR_CLUSTER_ID", "volcengine_streaming_common")
    )
    ws_url: str = field(default_factory=lambda: _env(
        "SEED_ASR_WS_URL",
        "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel",
    ))
    sample_rate: int = 16000
    chunk_duration_ms: int = 200


@dataclass
class DeepgramConfig:
    """Deepgram STT 配置（fallback）。"""

    api_key: str = field(default_factory=lambda: _env("DEEPGRAM_API_KEY"))
    model: str = "nova-3"
    language: str = "zh"


@dataclass
class RecorderConfig:
    """录制模块配置。"""

    audio_sample_rate: int = 16000
    audio_channels: int = 1
    screen_fps: int = 5
    ffmpeg_path: str = field(default_factory=lambda: _env("FFMPEG_PATH", "ffmpeg"))


@dataclass
class AppConfig:
    """应用顶层配置。"""

    llm: LLMConfig = field(default_factory=LLMConfig)
    seed_asr: SeedASRConfig = field(default_factory=SeedASRConfig)
    deepgram: DeepgramConfig = field(default_factory=DeepgramConfig)
    recorder: RecorderConfig = field(default_factory=RecorderConfig)

    sessions_dir: Path = field(
        default_factory=lambda: Path(_env("SIMCLASS_SESSIONS_DIR", "./sessions"))
    )
    stt_provider: str = field(default_factory=lambda: _env("SIMCLASS_STT_PROVIDER", "seedasr"))

    def __post_init__(self) -> None:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    """加载配置。优先读环境变量，也可从 .env 手动 source。"""
    return AppConfig()
