# Debug Voice Pipeline

Diagnose issues with the JARVIS voice pipeline.

## Pipeline stages (check in order)

### Stage 1 — Microphone & Audio
```bash
# Check microphone is recognized
python3 -c "import sounddevice as sd; print(sd.query_devices())"

# Test recording
python3 -c "
import sounddevice as sd, numpy as np, time
print('Recording 3s...')
data = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='int16')
sd.wait()
rms = int(np.sqrt(np.mean(data.astype(np.float32)**2)))
print(f'RMS: {rms} (need >500 for speech detection)')
"
```

### Stage 2 — Wake Word (sherpa-onnx)
```bash
# Verify sherpa-onnx installed and CoreML available
python3 -c "
import sherpa_onnx
print('sherpa-onnx:', sherpa_onnx.__version__)
# Check CoreML (Apple Silicon)
import platform
print('Arch:', platform.machine())
"
```

### Stage 3 — STT (RealtimeSTT / Whisper)
```bash
# Test transcription directly
python3 -c "
from RealtimeSTT import AudioToTextRecorder
print('RealtimeSTT loaded — model will download if not cached')
recorder = AudioToTextRecorder(model='distil-large-v3', spinner=False)
print('Recording — say something...')
text = recorder.text()
print(f'Transcribed: {text}')
recorder.stop()
"
```

### Stage 4 — TTS (RealtimeTTS + Kokoro)
```bash
# Test TTS playback
python3 -c "
from RealtimeTTS import TextToAudioStream, KokoroEngine
engine = KokoroEngine()
stream = TextToAudioStream(engine)
stream.feed('JARVIS online. Voice pipeline functional.')
stream.play()
print('TTS test complete')
"

# Fallback to edge-tts if kokoro fails
python3 -c "
import asyncio, edge_tts
async def test():
    communicate = edge_tts.Communicate('JARVIS online', 'en-US-GuyNeural')
    await communicate.save('/tmp/test.mp3')
    import subprocess; subprocess.run(['afplay', '/tmp/test.mp3'])
asyncio.run(test())
"
```

### Stage 5 — Full Pipeline
```bash
# Run with verbose logging
JARVIS_LOG_LEVEL=DEBUG make dev
# Then say "hey jarvis" and watch the log output
```

## Common fixes
- **No audio input:** `bash scripts/grant_permissions.sh` (Microphone privacy)
- **Wake word not triggering:** Lower sensitivity in `.env`: `JARVIS_VOICE_WAKE_SENSITIVITY=0.3`
- **Whisper slow:** Ensure `brew install llama.cpp` for Metal acceleration
- **Kokoro fails:** Set `JARVIS_VOICE_TTS_ENGINE=edge-tts` in `.env`
- **TTS choppy:** Increase buffer: `JARVIS_VOICE_TTS_BUFFER_SIZE=4096`
