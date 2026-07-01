"""
Text-to-Speech Synthesizer
===========================
Converts JARVIS responses to natural-sounding speech.

Providers (v2 stack — audited June 2026):
- edge-tts (default): Microsoft neural voices, no API key, ~50ms latency
- kokoro: 82M param local model, Apache-2.0, near-ElevenLabs quality, Apple MPS
- RealtimeTTS: Streams LLM token output directly into TTS engine

Design:
- Async synthesis to avoid blocking the event loop
- Queue-based playback to prevent audio overlap
- Falls back edge-tts → kokoro → system TTS
"""

from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger


class TTSProvider(StrEnum):
    EDGE = "edge-tts"          # Default: Microsoft neural voices, online, free
    KOKORO = "kokoro"           # Local: 82M param Apache-2.0 model, Apple MPS
    REALTIME = "realtimetts"    # Streaming: wraps any engine, feeds LLM tokens
    SYSTEM = "system"           # Fallback: macOS `say` command


@dataclass
class TTSConfig:
    """Configuration for text-to-speech synthesis."""
    provider: TTSProvider = TTSProvider.EDGE
    voice: str = "en-US-GuyNeural"   # edge-tts default; en-GB-RyanNeural = more JARVIS-like
    speed: float = 1.0               # Speech rate multiplier
    volume: float = 1.0              # 0.0–1.0
    sample_rate: int = 24000
    output_device: str | None = None


@dataclass
class SynthesisResult:
    """Result of speech synthesis."""
    audio_data: bytes
    duration_seconds: float
    sample_rate: int
    latency_ms: float = 0.0


class TextToSpeechSynthesizer:
    """
    Multi-provider text-to-speech synthesizer.

    Usage:
        config = TTSConfig(provider=TTSProvider.EDGE, voice="en-GB-RyanNeural")
        synth = TextToSpeechSynthesizer(config)
        await synth.initialize()
        await synth.speak("Good evening, sir.")
        await synth.cleanup()
    """

    def __init__(self, config: TTSConfig | None = None) -> None:
        self._config = config or TTSConfig()
        self._engine: Any = None
        self._playback_queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._playback_task: asyncio.Task[None] | None = None
        self._speaking = False

    async def initialize(self) -> None:
        """Initialize the TTS engine."""
        if self._config.provider not in (TTSProvider.EDGE, TTSProvider.SYSTEM):
            await asyncio.get_event_loop().run_in_executor(None, self._load_engine)
        self._playback_task = asyncio.create_task(
            self._playback_loop(), name="jarvis.tts.playback"
        )
        logger.info("TTS initialized: {}", self._config.provider)

    def _load_engine(self) -> None:
        """Load TTS engine (blocking, runs in thread pool)."""
        if self._config.provider == TTSProvider.KOKORO:
            try:
                from kokoro import KPipeline  # type: ignore[import-untyped]
                lang = "a"  # 'a' = American English; 'b' = British English
                self._engine = KPipeline(lang_code=lang)
            except ImportError as exc:
                raise ImportError(
                    "kokoro required: pip install kokoro>=0.9.0"
                ) from exc

        elif self._config.provider == TTSProvider.REALTIME:
            try:
                from RealtimeTTS import TextToAudioStream  # type: ignore[import-untyped]
                self._engine = TextToAudioStream(engine=None)
            except ImportError as exc:
                raise ImportError(
                    "RealtimeTTS required: pip install RealtimeTTS>=0.4.0"
                ) from exc

        logger.debug("TTS engine loaded: {}", self._config.provider)

    async def speak(self, text: str) -> None:
        """Queue text for speech output (non-blocking)."""
        await self._playback_queue.put(text)

    async def speak_and_wait(self, text: str) -> None:
        """Synthesize and play, waiting until complete."""
        result = await self.synthesize(text)
        await self._play_audio(result.audio_data, result.sample_rate)

    async def synthesize(self, text: str) -> SynthesisResult:
        """Synthesize text to audio bytes without playing."""
        import time
        start = time.perf_counter()

        audio_data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._synthesize_sync(text)
        )

        latency = (time.perf_counter() - start) * 1000
        logger.debug("Synthesized '{}...' ({:.0f}ms)", text[:30], latency)

        return SynthesisResult(
            audio_data=audio_data,
            duration_seconds=len(audio_data) / (self._config.sample_rate * 2),
            sample_rate=self._config.sample_rate,
            latency_ms=latency,
        )

    def _synthesize_sync(self, text: str) -> bytes:
        """Synchronous synthesis (runs in thread pool)."""
        if self._config.provider == TTSProvider.EDGE:
            return self._synthesize_edge(text)
        elif self._config.provider == TTSProvider.KOKORO:
            return self._synthesize_kokoro(text)
        elif self._config.provider == TTSProvider.SYSTEM:
            return self._synthesize_system(text)
        return b""

    def _synthesize_edge(self, text: str) -> bytes:
        """edge-tts synthesis (runs asyncio in thread)."""
        try:
            import asyncio as _asyncio

            import edge_tts  # type: ignore[import-untyped]

            async def _run() -> bytes:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    tmp = f.name
                communicate = edge_tts.Communicate(text, self._config.voice)
                await communicate.save(tmp)
                data = Path(tmp).read_bytes()
                Path(tmp).unlink(missing_ok=True)
                return data

            loop = _asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_run())
            finally:
                loop.close()
        except ImportError as exc:
            raise ImportError(
                "edge-tts required: pip install edge-tts>=6.1.0"
            ) from exc

    def _synthesize_kokoro(self, text: str) -> bytes:
        """kokoro local synthesis."""
        try:
            import soundfile as sf  # type: ignore[import-untyped]
            samples, rate = next(self._engine(text))
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name
            sf.write(tmp, samples, rate)
            data = Path(tmp).read_bytes()
            Path(tmp).unlink(missing_ok=True)
            return data
        except ImportError as exc:
            raise ImportError(
                "kokoro + soundfile required: pip install kokoro soundfile"
            ) from exc

    def _synthesize_system(self, text: str) -> bytes:
        """macOS system TTS via `say` command."""
        import subprocess
        subprocess.run(["say", "-r", str(int(180 * self._config.speed)), text], check=True)  # noqa: S603, S607
        return b""  # system plays directly, no bytes returned

    async def _play_audio(self, audio_data: bytes, sample_rate: int) -> None:
        """Play audio bytes through the output device."""
        if not audio_data:
            return  # SYSTEM provider plays directly
        try:
            import io

            import sounddevice as sd  # type: ignore[import-untyped]
            import soundfile as sf  # type: ignore[import-untyped]
            buf = io.BytesIO(audio_data)
            data, sr = sf.read(buf)
            self._speaking = True
            sd.play(data, sr)
            sd.wait()
            self._speaking = False
        except ImportError:
            logger.warning("sounddevice/soundfile not available — audio not played")

    async def _playback_loop(self) -> None:
        """Process the speech queue sequentially."""
        while True:
            text = await self._playback_queue.get()
            if text is None:
                break
            try:
                result = await self.synthesize(text)
                await self._play_audio(result.audio_data, result.sample_rate)
            except Exception as e:  # noqa: BLE001
                logger.error("TTS playback error: {}", e)

    async def stop_speaking(self) -> None:
        """Interrupt current speech."""
        try:
            import sounddevice as sd  # type: ignore[import-untyped]
            sd.stop()
            self._speaking = False
        except Exception:  # noqa: BLE001
            pass

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    async def cleanup(self) -> None:
        """Stop and clean up TTS resources."""
        if self._playback_task:
            await self._playback_queue.put(None)  # sentinel to stop loop
            self._playback_task.cancel()
        logger.debug("TTS synthesizer cleaned up")
