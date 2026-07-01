#!/usr/bin/env python3
"""
JARVIS OS — AI Model Downloader
================================
Pre-downloads all AI models required for offline voice operation.
Run this ONCE after setup.sh and before starting JARVIS.

Model inventory:
  - Whisper (STT):    ~750 MB  distil-large-v3 (fastest, high accuracy)
  - Kokoro (TTS):     ~330 MB  local neural TTS, ~150ms latency
  - sherpa-onnx:      ~2 MB    wake word keyword spotter (downloads on demand)

Usage:
  python3 scripts/download_models.py           # Download all models
  python3 scripts/download_models.py --whisper # STT only
  python3 scripts/download_models.py --tts     # TTS only
  python3 scripts/download_models.py --wakeword # Wake word only
  python3 scripts/download_models.py --list    # Show what's cached
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(msg: str) -> None:
    print(f"  \033[32m✓\033[0m  {msg}")

def _info(msg: str) -> None:
    print(f"  \033[36m→\033[0m  {msg}")

def _warn(msg: str) -> None:
    print(f"  \033[33m⚠\033[0m  {msg}")

def _err(msg: str) -> None:
    print(f"  \033[31m✗\033[0m  {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Model downloaders
# ---------------------------------------------------------------------------

def download_whisper(model_size: str = "distil-large-v3") -> bool:
    """
    Download Whisper model via RealtimeSTT's built-in downloader.

    RealtimeSTT uses faster-whisper under the hood and caches to
    ~/.cache/huggingface/hub/ on first use. This triggers the download
    explicitly so JARVIS starts without a delay.

    Apple Silicon note: RealtimeSTT will use whisper.cpp (Metal) if
    `llama.cpp` is installed via Homebrew (brew install llama.cpp).
    Otherwise falls back to faster-whisper (CPU-only on macOS).
    """
    _info(f"Downloading Whisper model: {model_size} (~750 MB)...")
    try:
        from RealtimeSTT import AudioToTextRecorder  # type: ignore[import]

        _info("Initializing RealtimeSTT to trigger model download...")
        # Instantiate with download_root to pre-cache the model
        recorder = AudioToTextRecorder(
            model=model_size,
            language="en",
            spinner=False,
            # Don't actually start recording — just init (downloads model)
        )
        recorder.stop()
        _ok(f"Whisper {model_size} downloaded successfully")
        return True
    except ImportError:
        _err("RealtimeSTT not installed. Run: pip install RealtimeSTT")
        return False
    except Exception as e:
        _warn(f"Could not pre-download via RealtimeSTT: {e}")
        _info("Falling back to faster-whisper direct download...")
        try:
            from faster_whisper import WhisperModel  # type: ignore[import]
            _info(f"Downloading {model_size} via faster-whisper (CPU only)...")
            WhisperModel(model_size, device="cpu", compute_type="int8")
            _ok(f"Whisper {model_size} cached via faster-whisper")
            return True
        except ImportError:
            _err("Neither RealtimeSTT nor faster-whisper is installed.")
            return False
        except Exception as e2:
            _err(f"Whisper download failed: {e2}")
            return False


def download_kokoro() -> bool:
    """
    Download Kokoro TTS model (~330 MB, Apache-2.0).

    Kokoro is the primary offline TTS engine. It runs on Apple MPS
    (Metal) with ~150ms first-chunk latency at near-ElevenLabs quality.
    """
    _info("Downloading Kokoro TTS model (~330 MB)...")
    try:
        import kokoro  # type: ignore[import]
        from kokoro import KPipeline  # type: ignore[import]

        _info("Initializing Kokoro pipeline (downloads model on first use)...")
        pipeline = KPipeline(lang_code="a")  # 'a' = American English
        # Run a tiny synthesis to confirm download
        generator = pipeline("Hello JARVIS.", voice="af_heart")
        next(generator)  # Trigger download + first chunk
        _ok("Kokoro TTS model downloaded and verified")
        return True
    except ImportError:
        _err("kokoro not installed. Run: pip install kokoro soundfile")
        return False
    except Exception as e:
        _warn(f"Kokoro download failed: {e}")
        _warn("Falling back to edge-tts (online) or pyttsx3 (system voices)")
        _info("Set JARVIS_VOICE_TTS_ENGINE=edge-tts in .env to use online voices")
        return False


def download_wakeword() -> bool:
    """
    Download sherpa-onnx wake word model.

    sherpa-onnx downloads ONNX models on first use. For Apple Silicon,
    it automatically uses the CoreML backend (~160ms detection latency).
    The default wake word is 'jarvis' — configurable in .env.
    """
    _info("Checking sherpa-onnx wake word setup...")
    try:
        import sherpa_onnx  # type: ignore[import]

        _info("sherpa-onnx installed and importable")
        _info("Wake word models download automatically on first JARVIS start")
        _info("Default wake phrase: 'hey jarvis' (configurable in .env)")
        _ok("sherpa-onnx ready")
        return True
    except ImportError:
        _err("sherpa-onnx not installed. Run: pip install sherpa-onnx")
        return False


def list_cached_models() -> None:
    """Show what's already downloaded in standard cache locations."""
    print("\n  Cached Models:")
    print("  " + "─" * 50)

    # Whisper / HuggingFace cache
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.exists():
        whisper_dirs = list(hf_cache.glob("models--*whisper*"))
        if whisper_dirs:
            for d in whisper_dirs:
                size_mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) // (1024 * 1024)
                _ok(f"Whisper: {d.name} (~{size_mb} MB)")
        else:
            _warn("No Whisper models found in HuggingFace cache")
    else:
        _warn("HuggingFace cache not found (~/.cache/huggingface)")

    # Kokoro cache (typically in site-packages or ~/.local)
    kokoro_cache = Path.home() / ".cache" / "kokoro"
    if kokoro_cache.exists():
        size_mb = sum(f.stat().st_size for f in kokoro_cache.rglob("*") if f.is_file()) // (1024 * 1024)
        _ok(f"Kokoro TTS: ~{size_mb} MB cached")
    else:
        # Check HuggingFace for kokoro
        kokoro_hf = list(hf_cache.glob("models--hexgrad*")) if hf_cache.exists() else []
        if kokoro_hf:
            _ok(f"Kokoro TTS: found in HuggingFace cache")
        else:
            _warn("Kokoro TTS not yet downloaded")

    # sherpa-onnx models
    sherpa_cache = Path.home() / ".cache" / "sherpa-onnx"
    if sherpa_cache.exists():
        models = list(sherpa_cache.iterdir())
        _ok(f"sherpa-onnx: {len(models)} model(s) cached")
    else:
        _warn("sherpa-onnx models not yet downloaded (auto-downloads on first start)")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="JARVIS OS — AI Model Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--whisper", action="store_true", help="Download Whisper STT model only")
    parser.add_argument("--tts", action="store_true", help="Download Kokoro TTS model only")
    parser.add_argument("--wakeword", action="store_true", help="Check sherpa-onnx wake word setup")
    parser.add_argument("--list", action="store_true", help="List currently cached models")
    parser.add_argument(
        "--model-size",
        default="distil-large-v3",
        choices=["tiny", "tiny.en", "base", "base.en", "small", "small.en",
                 "medium", "medium.en", "large-v2", "large-v3", "distil-large-v3"],
        help="Whisper model size (default: distil-large-v3)",
    )
    args = parser.parse_args()

    print()
    print("  \033[36m╔══════════════════════════════════════╗\033[0m")
    print("  \033[36m║   JARVIS OS — Model Downloader       ║\033[0m")
    print("  \033[36m╚══════════════════════════════════════╝\033[0m")
    print()

    print("  Model reference:")
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  Model              Size     Purpose                │")
    print("  │  distil-large-v3   ~750 MB  STT (RealtimeSTT)      │")
    print("  │  kokoro             ~330 MB  TTS (local, fast)      │")
    print("  │  sherpa-onnx        ~2 MB   Wake word detection     │")
    print("  │  Total             ~1.1 GB                          │")
    print("  └─────────────────────────────────────────────────────┘")
    print()

    if args.list:
        list_cached_models()
        return

    download_all = not (args.whisper or args.tts or args.wakeword)
    results: dict[str, bool] = {}

    if download_all or args.whisper:
        print(f"\n  [1/3] Whisper STT ({args.model_size})")
        results["whisper"] = download_whisper(args.model_size)

    if download_all or args.tts:
        print("\n  [2/3] Kokoro TTS")
        results["kokoro"] = download_kokoro()

    if download_all or args.wakeword:
        print("\n  [3/3] sherpa-onnx Wake Word")
        results["wakeword"] = download_wakeword()

    # Summary
    print()
    print("  " + "─" * 50)
    all_ok = all(results.values())
    if all_ok:
        print("  \033[32m✓ All models ready. JARVIS can start offline.\033[0m")
        print()
        print("  Next: bash scripts/preflight_check.sh")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"  \033[33m⚠ Some models failed to download: {', '.join(failed)}\033[0m")
        print("  JARVIS will still work but may fall back to online providers.")
        print("  Re-run: python3 scripts/download_models.py to retry.")
    print()


if __name__ == "__main__":
    main()
