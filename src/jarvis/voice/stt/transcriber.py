"""
Speech-to-Text Transcriber
===========================
Converts spoken audio to text using RealtimeSTT (whisper.cpp backend).

Stack (v2 — June 2026):
- RealtimeSTT: Streaming STT, wraps whisper.cpp for Metal GPU on Apple Silicon
  Replaces faster-whisper (no Metal GPU support on macOS, CPU-only)
- whisper.cpp backend: 4–8× faster than faster-whisper on M-series via Metal

Design:
- Streaming transcription: partial results as user speaks
- Async interface: non-blocking, thread-pool execution
- VAD built-in: RealtimeSTT handles silence detection
"""

from __future__ import annotations

import asyncio
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class TranscriptionResult:
    """Result of a speech transcription."""
    text: str
    language: str
    confidence: float                     # 0.0–1.0
    segments: list[dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    latency_ms: float = 0.0


@dataclass
class STTConfig:
    """Configuration for the speech-to-text engine."""
    model_size: str = "base"             # tiny, base, small, medium, large
    language: str | None = None          # None = auto-detect
    device: str = "cpu"                  # cpu | mps (Metal, Apple Silicon)
    compute_type: str = "int8"
    beam_size: int = 5
    vad_filter: bool = True              # Voice activity detection
    vad_threshold: float = 0.5
    min_silence_ms: int = 500            # Silence to end speech segment
    sample_rate: int = 16000
    use_realtime_stt: bool = True        # Use RealtimeSTT streaming mode


class SpeechTranscriber:
    """
    Async speech-to-text using RealtimeSTT (whisper.cpp backend).

    Usage:
        config = STTConfig(model_size="base", device="mps")  # Metal on Apple Silicon
        transcriber = SpeechTranscriber(config=config)
        await transcriber.initialize()

        result = await transcriber.transcribe_audio(audio_bytes)
        print(result.text)   # "open the terminal"

        await transcriber.cleanup()
    """

    def __init__(self, config: STTConfig | None = None) -> None:
        self._config = config or STTConfig()
        self._model: Any = None
        self._recorder: Any = None
        self._initialized = False

    async def initialize(self) -> None:
        """Load the Whisper model (done once at startup)."""
        logger.info(
            "Loading Whisper model: {} on {}",
            self._config.model_size,
            self._config.device,
        )
        await asyncio.get_event_loop().run_in_executor(None, self._load_model)
        self._initialized = True
        logger.success("Whisper model ready: {}", self._config.model_size)

    def _load_model(self) -> None:
        """Load model (blocking — called from thread pool)."""
        if self._config.use_realtime_stt:
            self._load_realtime_stt()
        else:
            self._load_whisper_fallback()

    def _load_realtime_stt(self) -> None:
        """Load RealtimeSTT (preferred — Metal backend on Apple Silicon)."""
        try:
            from RealtimeSTT import AudioToTextRecorder  # type: ignore[import-untyped]
            self._recorder = AudioToTextRecorder(
                model=self._config.model_size,
                language=self._config.language or "",
                compute_type=self._config.compute_type,
                beam_size=self._config.beam_size,
                silero_sensitivity=self._config.vad_threshold,
                post_speech_silence_duration=self._config.min_silence_ms / 1000,
                # Use Metal on Apple Silicon automatically
                device=self._config.device,
            )
            logger.debug("RealtimeSTT loaded (whisper.cpp backend)")
        except ImportError:
            logger.warning(
                "RealtimeSTT not installed — falling back to file-based transcription. "
                "Install: pip install RealtimeSTT>=0.3.104"
            )
            self._load_whisper_fallback()

    def _load_whisper_fallback(self) -> None:
        """Fallback: file-based whisper transcription."""
        try:
            # Test RealtimeSTT availability without importing the heavy class
            import importlib.util
            if importlib.util.find_spec("RealtimeSTT") is not None:
                self._recorder = None  # Use file-based transcribe path
                self._model = "realtime_stt_available"
            else:
                raise ImportError("RealtimeSTT not found")
        except ImportError:
            # Last resort: direct whisper (no Metal, CPU only)
            try:
                import whisper  # type: ignore[import-untyped]
                self._model = whisper.load_model(self._config.model_size)
                logger.debug("Loaded openai-whisper (CPU only — no Metal)")
            except ImportError as exc:
                raise ImportError(
                    "STT requires RealtimeSTT or openai-whisper. "
                    "Install: pip install RealtimeSTT>=0.3.104"
                ) from exc

    async def transcribe_audio(
        self,
        audio_data: bytes,
        *,
        sample_rate: int | None = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio bytes to text.

        Args:
            audio_data: Raw PCM bytes (16-bit, mono, 16kHz by default)
            sample_rate: Override sample rate if different from config
        """
        import time
        start = time.perf_counter()

        sr = sample_rate or self._config.sample_rate
        result_text = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._transcribe_sync(audio_data, sr)
        )

        latency = (time.perf_counter() - start) * 1000
        duration = len(audio_data) / (sr * 2)

        logger.debug(
            "Transcribed {:.1f}s audio in {:.0f}ms: '{}'",
            duration,
            latency,
            result_text[:50],
        )

        return TranscriptionResult(
            text=result_text.strip(),
            language=self._config.language or "en",
            confidence=0.9,  # RealtimeSTT doesn't expose per-word confidence
            duration_seconds=duration,
            latency_ms=latency,
        )

    def _transcribe_sync(self, audio_data: bytes, sample_rate: int) -> str:
        """Synchronous transcription (runs in thread pool)."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            with wave.open(tmp_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)

            return self._run_transcription(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _run_transcription(self, wav_path: str) -> str:
        """Run the actual transcription model on a WAV file."""
        if self._model == "realtime_stt_available" or self._recorder:
            # RealtimeSTT file-based mode
            try:
                from RealtimeSTT import AudioToTextRecorder  # type: ignore[import-untyped]
                recorder = AudioToTextRecorder(
                    model=self._config.model_size,
                    device=self._config.device,
                )
                result = recorder.text(wav_path) if hasattr(recorder, "text") else ""
                return str(result) if result else ""
            except Exception as e:  # noqa: BLE001
                logger.warning("RealtimeSTT file transcription failed: {}", e)
                return ""
        elif self._model:
            # openai-whisper fallback
            result = self._model.transcribe(wav_path, fp16=False)
            return str(result.get("text", ""))
        return ""

    async def start_streaming(
        self,
        on_partial: Any,
        on_final: Any,
    ) -> None:
        """
        Start streaming transcription with live partial results.
        Uses RealtimeSTT's native streaming mode.

        Args:
            on_partial: Callback(text: str) for partial results
            on_final: Callback(text: str) for final committed result
        """
        if self._recorder is None:
            logger.warning("Streaming STT requires RealtimeSTT to be initialized")
            return

        def _on_realtime(text: str) -> None:
            asyncio.run_coroutine_threadsafe(on_partial(text), asyncio.get_event_loop())

        def _on_final(text: str) -> None:
            asyncio.run_coroutine_threadsafe(on_final(text), asyncio.get_event_loop())

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._recorder.text(_on_final, on_realtime_transcription_update=_on_realtime),
        )

    async def cleanup(self) -> None:
        """Clean up STT resources."""
        if self._recorder:
            import contextlib
            with contextlib.suppress(Exception):
                self._recorder.stop()
        self._model = None
        self._initialized = False
        logger.debug("STT transcriber cleaned up")
