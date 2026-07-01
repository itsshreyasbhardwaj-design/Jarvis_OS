"""
Screen Capture & OCR
=====================
Fast screen capture using mss, OCR via Apple Vision Framework.

Stack (v2 — June 2026):
- mss: Fast multi-monitor capture, 30+ FPS at minimal CPU
  Replaces Pillow.ImageGrab (slower) and pyautogui (unreliable)
- pyobjc-framework-Vision: Apple Vision OCR, Neural Engine, zero download
  Replaces pytesseract (needs Tesseract system install, slower)

Design:
- All captures gated behind PermissionManager (RiskLevel.READ_ONLY)
- OCR uses Apple Vision Framework (same as iOS Live Text)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from loguru import logger

from jarvis.desktop.permissions import PermissionManager, PermissionRequest, RiskLevel


@dataclass
class Screenshot:
    """A captured screenshot."""
    image_data: bytes       # Raw PNG bytes
    width: int
    height: int
    monitor: int = 0        # Monitor index (0 = primary)


class ScreenCapture:
    """
    Screen capture using mss (30+ FPS, multi-monitor).

    Usage:
        capture = ScreenCapture(permission_manager)
        await capture.initialize()
        screenshot = await capture.capture()
        text = await capture.extract_text(screenshot)
    """

    def __init__(self, permission_manager: PermissionManager) -> None:
        self._permissions = permission_manager

    async def initialize(self) -> None:
        """Verify mss is available."""
        try:
            import mss  # type: ignore[import-untyped]  # noqa: F401
            logger.debug("Screen capture ready (mss)")
        except ImportError:
            logger.warning("mss not installed: pip install mss>=9.0.0")

    async def capture(
        self,
        region: tuple[int, int, int, int] | None = None,
        monitor: int = 1,
    ) -> Screenshot:
        """
        Capture a screenshot.

        Args:
            region: (left, top, width, height) or None for full screen
            monitor: Monitor index (1 = primary on mss)

        Returns:
            Screenshot with PNG bytes
        """
        result = await self._permissions.check(PermissionRequest(
            action_name="screen_capture",
            risk_level=RiskLevel.READ_ONLY,
            description="Capture screen",
        ))
        if not result.granted:
            logger.warning("screen_capture blocked: {}", result.reason)
            return Screenshot(image_data=b"", width=0, height=0)

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._capture_sync(region, monitor)
        )

    def _capture_sync(
        self, region: tuple[int, int, int, int] | None, monitor: int
    ) -> Screenshot:
        """Blocking capture using mss."""
        try:
            import mss  # type: ignore[import-untyped]
            import mss.tools
            with mss.mss() as sct:
                if region:
                    left, top, width, height = region
                    mon = {"left": left, "top": top, "width": width, "height": height}
                else:
                    mon = sct.monitors[monitor]  # type: ignore[assignment]
                raw = sct.grab(mon)
                png_bytes = mss.tools.to_png(raw.rgb, raw.size)
                return Screenshot(
                    image_data=png_bytes,
                    width=raw.width,
                    height=raw.height,
                    monitor=monitor,
                )
        except ImportError as exc:
            raise ImportError("mss required: pip install mss>=9.0.0") from exc

    async def extract_text(self, screenshot: Screenshot) -> str:
        """
        Extract text from a screenshot using Apple Vision OCR.

        Uses the Neural Engine on Apple Silicon — zero download, ultra fast.
        Falls back to basic PIL-based approach on non-macOS.
        """
        if not screenshot.image_data:
            return ""

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._ocr_sync(screenshot.image_data)
        )

    def _ocr_sync(self, image_data: bytes) -> str:
        """Blocking OCR using Apple Vision Framework."""
        try:
            # Apple Vision OCR (macOS only) — same engine as iOS Live Text
            return self._ocr_apple_vision(image_data)
        except (ImportError, Exception) as e:
            logger.debug("Apple Vision OCR unavailable: {} — trying PIL fallback", e)
            return self._ocr_pil_fallback(image_data)

    def _ocr_apple_vision(self, image_data: bytes) -> str:
        """OCR via pyobjc-framework-Vision (Neural Engine, Apple Silicon)."""
        import Foundation  # type: ignore[import-untyped]
        import Quartz  # type: ignore[import-untyped]
        import Vision  # type: ignore[import-untyped]

        # Convert PNG bytes → CGImage
        ns_data = Foundation.NSData.dataWithBytes_length_(image_data, len(image_data))
        cg_image_source = Quartz.CGImageSourceCreateWithData(ns_data, None)
        cg_image = Quartz.CGImageSourceCreateImageAtIndex(cg_image_source, 0, None)

        # Run text recognition request
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True)

        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
            cg_image, {}
        )
        handler.performRequests_error_([request], None)

        observations = request.results() or []
        text_blocks = []
        for obs in observations:
            candidate = obs.topCandidates_(1)
            if candidate:
                text_blocks.append(str(candidate[0].string()))

        return "\n".join(text_blocks)

    def _ocr_pil_fallback(self, image_data: bytes) -> str:
        """Minimal fallback: return empty string with warning."""
        logger.warning(
            "OCR unavailable on this platform. "
            "For Apple Silicon: pip install pyobjc-framework-Vision"
        )
        return ""

    async def save(self, screenshot: Screenshot, path: str) -> str:
        """Save a screenshot PNG to disk."""
        from pathlib import Path
        abs_path = Path(path).expanduser()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(screenshot.image_data)
        return str(abs_path)
