"""
Audio Pipeline
==============
Orchestrates the complete voice interaction flow:

  [Microphone] → [Wake Word] → [Recording] → [VAD] → [STT] → [AI] → [TTS] → [Speaker]

The pipeline is event-driven and interruptible at any stage.
Users can interrupt JARVIS mid-sentence by saying the wake word again.

States:
  IDLE → LISTENING_FOR_WAKE_WORD → RECORDING → TRANSCRIBING → THINKING → SPEAKING
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from enum import Enum, auto
from typing import Any

from loguru import logger

from jarvis.voice.stt.transcriber import SpeechTranscriber, STTConfig
from jarvis.voice.tts.synthesizer import TextToSpeechSynthesizer, TTSConfig
from jarvis.voice.wake_word.detector import WakeWordConfig, WakeWordDetector


class PipelineState(Enum):
    IDLE = auto()
    LISTENING = auto()        # Waiting for wake word
    RECORDING = auto()        # Capturing user speech
    TRANSCRIBING = auto()     # Converting speech to text
    THINKING = auto()         # AI processing
    SPEAKING = auto()         # Playing TTS response


InputCallback = Callable[[str], Coroutine[Any, Any, str]]


class AudioPipeline:
    """
    Complete voice interaction pipeline.

    Usage:
        async def handle_input(text: str) -> str:
            return await ai.complete(text)

        pipeline = AudioPipeline()
        await pipeline.initialize()
        await pipeline.start(input_callback=handle_input)
    """

    MAX_RECORDING_SECONDS = 30.0
    SILENCE_TIMEOUT_SECONDS = 2.0

    def __init__(
        self,
        wake_word_config: WakeWordConfig | None = None,
        stt_config: STTConfig | None = None,
        tts_config: TTSConfig | None = None,
    ) -> None:
        self._wake_detector = WakeWordDetector(wake_word_config)
        self._transcriber = SpeechTranscriber(stt_config)
        self._synthesizer = TextToSpeechSynthesizer(tts_config)
        self._state = PipelineState.IDLE
        self._input_callback: InputCallback | None = None

    async def initialize(self) -> None:
        """Initialize all pipeline components."""
        logger.info("Initializing audio pipeline...")
        await self._transcriber.initialize()
        await self._synthesizer.initialize()
        logger.success("Audio pipeline initialized")

    async def start(self, input_callback: InputCallback) -> None:
        """Start the pipeline. Runs until stopped."""
        self._input_callback = input_callback
        self._state = PipelineState.LISTENING
        logger.info("Audio pipeline started. Listening for wake word...")
        await self._wake_detector.start(callback=self._on_wake_word)

    async def stop(self) -> None:
        """Stop the pipeline gracefully."""
        await self._wake_detector.stop()
        await self._synthesizer.cleanup()
        await self._transcriber.cleanup()
        self._state = PipelineState.IDLE
        logger.info("Audio pipeline stopped")

    async def speak(self, text: str) -> None:
        """Speak a response through the pipeline."""
        if self._state == PipelineState.SPEAKING:
            await self._synthesizer.stop_speaking()
        self._state = PipelineState.SPEAKING
        await self._synthesizer.speak(text)
        self._state = PipelineState.LISTENING

    # --- Internal Pipeline Stages ---

    async def _on_wake_word(self, detection: Any) -> None:
        """Handle wake word detection — begin recording."""
        logger.info("Wake word detected — recording user input")
        self._state = PipelineState.RECORDING

        # Interrupt any current speech
        if self._state == PipelineState.SPEAKING:
            await self._synthesizer.stop_speaking()

        audio_data = await self._record_utterance()
        if not audio_data:
            self._state = PipelineState.LISTENING
            return

        await self._process_utterance(audio_data)

    async def _record_utterance(self) -> bytes | None:
        """Record user speech until silence is detected."""
        try:
            import numpy as np
            import pyaudio
        except ImportError:
            logger.warning("pyaudio not available — cannot record")
            return None

        CHUNK = 1024
        SAMPLE_RATE = 16000
        SILENCE_THRESHOLD = 500
        MIN_SPEECH_CHUNKS = 5

        audio_frames: list[bytes] = []
        silent_chunks = 0
        speech_chunks = 0
        max_chunks = int(self.MAX_RECORDING_SECONDS * SAMPLE_RATE / CHUNK)
        silence_limit = int(
            self.SILENCE_TIMEOUT_SECONDS * SAMPLE_RATE / CHUNK
        )

        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        try:
            for _ in range(max_chunks):
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: stream.read(CHUNK, exception_on_overflow=False)
                )
                audio_frames.append(data)

                # RMS-based VAD
                samples = np.frombuffer(data, dtype=np.int16)
                rms = int(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))

                if rms > SILENCE_THRESHOLD:
                    speech_chunks += 1
                    silent_chunks = 0
                else:
                    silent_chunks += 1

                if speech_chunks >= MIN_SPEECH_CHUNKS and silent_chunks >= silence_limit:
                    break

        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

        if speech_chunks < MIN_SPEECH_CHUNKS:
            return None

        return b"".join(audio_frames)

    async def _process_utterance(self, audio_data: bytes) -> None:
        """Transcribe and send to AI."""
        self._state = PipelineState.TRANSCRIBING
        transcription = await self._transcriber.transcribe_audio(audio_data)

        if not transcription.text:
            logger.debug("No speech detected in recording")
            self._state = PipelineState.LISTENING
            return

        logger.info('User said: "{}"', transcription.text)

        if self._input_callback:
            self._state = PipelineState.THINKING
            try:
                response = await self._input_callback(transcription.text)
                await self.speak(response)
            except Exception as e:
                logger.error(f"Pipeline input callback error: {e}")
                self._state = PipelineState.LISTENING

    @property
    def state(self) -> PipelineState:
        return self._state
