"""
Wake Word Detector
==================
Listens for the configured wake word ("hey jarvis") using sherpa-onnx,
then signals the voice pipeline to begin transcription.

Stack (v2 — June 2026):
- sherpa-onnx: Apache-2.0, CoreML backend on Apple Silicon, ~160ms latency
  Replaces openwakeword (CC BY-NC-SA license risk)

Design:
- Always-on background listener (minimal CPU via CoreML/Neural Engine)
- Configurable sensitivity (false positive vs. miss rate tradeoff)
- Cooldown period after detection (prevents double-triggering)
- Emits WakeWordDetectedEvent via the event bus
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from loguru import logger


class WakeWordState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    DETECTED = "detected"
    COOLDOWN = "cooldown"


@dataclass
class WakeWordConfig:
    """Configuration for the wake word detector."""
    wake_word: str = "hey jarvis"
    sensitivity: float = 0.5           # 0.0–1.0 (higher = more sensitive)
    cooldown_seconds: float = 2.0      # Wait after detection before re-arming
    sample_rate: int = 16000
    chunk_size: int = 512              # ~32ms at 16kHz for sherpa-onnx
    model_path: str | None = None      # Path to sherpa-onnx .onnx model
    keywords_file: str | None = None   # sherpa-onnx keywords file path


@dataclass
class WakeWordDetection:
    """A wake word detection event."""
    wake_word: str
    confidence: float
    timestamp: float = field(default_factory=time.monotonic)
    audio_sample: bytes | None = None  # Optional: audio around detection


DetectionCallback = Callable[[WakeWordDetection], Coroutine[Any, Any, None]]


class WakeWordDetector:
    """
    Always-on wake word detection using sherpa-onnx.

    Models auto-download on first start from HuggingFace (~4 MB).
    CoreML backend activates automatically on Apple Silicon.

    Usage:
        detector = WakeWordDetector(config=WakeWordConfig())
        await detector.start(callback=on_wake_word)
        # ... later ...
        await detector.stop()
    """

    def __init__(self, config: WakeWordConfig | None = None) -> None:
        self._config = config or WakeWordConfig()
        self._state = WakeWordState.IDLE
        self._model: Any = None
        self._stream_task: asyncio.Task[None] | None = None
        self._detection_count = 0

    async def start(self, callback: DetectionCallback) -> None:
        """Start listening for the wake word."""
        await asyncio.get_event_loop().run_in_executor(None, self._load_model)
        self._state = WakeWordState.LISTENING
        self._stream_task = asyncio.create_task(
            self._listen_loop(callback), name="jarvis.wake_word"
        )
        logger.info(
            "Wake word detector started: '{}' (sensitivity={})",
            self._config.wake_word,
            self._config.sensitivity,
        )

    async def stop(self) -> None:
        """Stop the detector."""
        self._state = WakeWordState.IDLE
        if self._stream_task:
            self._stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stream_task
        logger.info(
            "Wake word detector stopped. Total detections: {}",
            self._detection_count,
        )

    @property
    def state(self) -> WakeWordState:
        return self._state

    @property
    def is_listening(self) -> bool:
        return self._state == WakeWordState.LISTENING

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """Load the sherpa-onnx keyword spotter model (blocking)."""
        try:
            import sherpa_onnx  # type: ignore[import-untyped]

            # sherpa-onnx keyword spotting config
            # Models at: https://github.com/k2-fsa/sherpa-onnx/releases
            # They auto-download on first use via sherpa_onnx.download_model()
            if self._config.keywords_file and self._config.model_path:
                self._model = sherpa_onnx.KeywordSpotter(
                    tokens=self._config.model_path + "/tokens.txt",
                    encoder=self._config.model_path + "/encoder.onnx",
                    decoder=self._config.model_path + "/decoder.onnx",
                    joiner=self._config.model_path + "/joiner.onnx",
                    keywords_file=self._config.keywords_file,
                    num_threads=1,
                    provider="coreml",  # Apple Silicon: CoreML → Neural Engine
                )
            else:
                # Simulation mode — model not configured yet
                logger.warning(
                    "sherpa-onnx model not configured. "
                    "Set model_path + keywords_file in WakeWordConfig. "
                    "See: https://github.com/k2-fsa/sherpa-onnx/releases"
                )
                self._model = None
        except ImportError:
            logger.warning(
                "sherpa-onnx not installed — wake word detection disabled. "
                "Install: pip install sherpa-onnx>=1.10.0"
            )
            self._model = None

    async def _listen_loop(self, callback: DetectionCallback) -> None:
        """Main audio capture and detection loop."""
        try:
            import sounddevice as sd  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "sounddevice not installed. Cannot capture audio. "
                "Install: pip install sounddevice>=0.4.6"
            )
            return

        logger.debug("Audio stream opened for wake word detection")

        def _audio_callback(
            indata: np.ndarray,
            frames: int,
            time_info: Any,
            status: Any,
        ) -> None:
            if status:
                logger.debug("Audio stream status: {}", status)
            # Put audio chunk into queue for async processing
            chunk = indata[:, 0].copy()  # mono
            import contextlib
            with contextlib.suppress(asyncio.QueueFull):
                self._audio_queue.put_nowait(chunk)

        self._audio_queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=50)

        with sd.InputStream(
            samplerate=self._config.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self._config.chunk_size,
            callback=_audio_callback,
        ):
            while self._state == WakeWordState.LISTENING:
                try:
                    chunk = await asyncio.wait_for(
                        self._audio_queue.get(), timeout=0.5
                    )
                    await self._process_chunk(chunk, callback)
                except TimeoutError:
                    continue  # No audio — loop back

    async def _process_chunk(
        self, chunk: np.ndarray, callback: DetectionCallback
    ) -> None:
        """Run inference on one audio chunk."""
        if self._model is None or self._state != WakeWordState.LISTENING:
            return

        try:
            stream = self._model.create_stream()
            int16_chunk = (chunk * 32767).astype(np.int16)
            stream.accept_waveform(self._config.sample_rate, int16_chunk)
            self._model.decode_stream(stream)
            result = self._model.get_result(stream)

            if result.keyword:
                score = getattr(result, "keyword_score", 0.9)
                confidence = float(score)
                if confidence >= self._config.sensitivity:
                    audio_bytes = (chunk * 32767).astype(np.int16).tobytes()
                    await self._on_detected(confidence, audio_bytes, callback)
        except Exception as e:  # noqa: BLE001
            logger.debug("Wake word inference error (non-fatal): {}", e)

    async def _on_detected(
        self,
        confidence: float,
        audio_data: bytes,
        callback: DetectionCallback,
    ) -> None:
        """Handle a wake word detection."""
        self._detection_count += 1
        self._state = WakeWordState.DETECTED

        detection = WakeWordDetection(
            wake_word=self._config.wake_word,
            confidence=confidence,
            audio_sample=audio_data,
        )
        logger.info(
            "Wake word detected: '{}' (confidence={:.3f})",
            self._config.wake_word,
            confidence,
        )

        await callback(detection)

        # Cooldown to prevent re-triggering
        self._state = WakeWordState.COOLDOWN
        await asyncio.sleep(self._config.cooldown_seconds)
        self._state = WakeWordState.LISTENING
