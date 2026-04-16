"""录制模块 — 音频采集 + 屏幕录制。"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import threading
import time
import wave
from pathlib import Path

from simclass.config import RecorderConfig

logger = logging.getLogger(__name__)


class AudioRecorder:
    """麦克风音频录制（PCM 16kHz mono）。同时提供音频流供 STT 使用。"""

    def __init__(self, config: RecorderConfig) -> None:
        self.config = config
        self._frames: list[bytes] = []
        self._stream = None
        self._running = False
        self._on_chunk: list[asyncio.Queue] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def subscribe(self) -> asyncio.Queue[bytes]:
        """订阅音频块，返回一个 Queue，录制期间会持续向其中放入音频数据。"""
        q: asyncio.Queue[bytes] = asyncio.Queue()
        self._on_chunk.append(q)
        return q

    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice 的回调，在音频线程中执行。"""
        if status:
            logger.warning("Audio status: %s", status)
        chunk = bytes(indata)
        self._frames.append(chunk)
        for q in self._on_chunk:
            if self._loop:
                self._loop.call_soon_threadsafe(q.put_nowait, chunk)

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        try:
            import sounddevice as sd
        except OSError as e:
            logger.warning("无法初始化音频设备: %s — 音频录制已禁用。", e)
            self._running = False
            return

        self._loop = loop
        self._running = True
        try:
            self._stream = sd.RawInputStream(
                samplerate=self.config.audio_sample_rate,
                channels=self.config.audio_channels,
                dtype="int16",
                blocksize=int(self.config.audio_sample_rate * 0.2),  # 200ms chunks
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            logger.warning("无法打开麦克风: %s — 音频录制已禁用。", e)
            self._running = False
            self._stream = None
            return

        logger.info(
            "Audio recording started (rate=%d, channels=%d)",
            self.config.audio_sample_rate,
            self.config.audio_channels,
        )

    def stop(self) -> None:
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        for q in self._on_chunk:
            q.put_nowait(b"")  # sentinel
        logger.info("Audio recording stopped, %d chunks captured", len(self._frames))

    def save_wav(self, path: Path) -> Path | None:
        """将录制的音频保存为 WAV 文件。"""
        if not self._frames:
            logger.info("No audio frames captured, skipping WAV save")
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(self.config.audio_channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.config.audio_sample_rate)
            wf.writeframes(b"".join(self._frames))
        logger.info("Audio saved to %s", path)
        return path


class ScreenRecorder:
    """屏幕录制 — 截屏序列通过 ffmpeg 编码为 MP4。"""

    def __init__(self, config: RecorderConfig) -> None:
        self.config = config
        self._running = False
        self._thread: threading.Thread | None = None
        self._frames_dir: Path | None = None

    def start(self, output_dir: Path) -> None:
        self._frames_dir = output_dir / "_screen_frames"
        self._frames_dir.mkdir(parents=True, exist_ok=True)
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Screen recording started (fps=%d)", self.config.screen_fps)

    def _capture_loop(self) -> None:
        import mss
        from PIL import Image

        interval = 1.0 / self.config.screen_fps
        frame_idx = 0

        with mss.mss() as sct:
            monitor = sct.monitors[0]  # 全部屏幕
            while self._running:
                start = time.time()
                img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                pil_img = pil_img.resize(
                    (pil_img.width // 2, pil_img.height // 2),
                    Image.LANCZOS,
                )
                pil_img.save(self._frames_dir / f"frame_{frame_idx:06d}.jpg", quality=70)
                frame_idx += 1
                elapsed = time.time() - start
                sleep_time = max(0, interval - elapsed)
                time.sleep(sleep_time)

        logger.info("Screen capture stopped, %d frames", frame_idx)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def encode_video(self, output_path: Path) -> Path | None:
        """用 ffmpeg 将截屏序列编码为 MP4。"""
        if not self._frames_dir or not self._frames_dir.exists():
            logger.warning("No screen frames to encode")
            return None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.config.ffmpeg_path,
            "-y",
            "-framerate", str(self.config.screen_fps),
            "-i", str(self._frames_dir / "frame_%06d.jpg"),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            logger.info("Screen video saved to %s", output_path)
            return output_path
        except FileNotFoundError:
            logger.error("ffmpeg not found at '%s'", self.config.ffmpeg_path)
            return None
        except subprocess.CalledProcessError as e:
            logger.error("ffmpeg failed: %s", e.stderr.decode())
            return None
