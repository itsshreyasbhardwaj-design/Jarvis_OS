"""
JARVIS OS Design System — Typography
======================================
Consistent type scale used across all UI components.

Primary font: Inter (modern, readable, free)
Monospace font: JetBrains Mono (code, terminal output)
"""

from typing import NamedTuple


class FontSpec(NamedTuple):
    family: str
    size: int
    weight: str = "normal"   # normal | bold


class JarvisTypography:
    """Standard type scale for JARVIS OS."""

    FONT_FAMILY = "Inter"
    FONT_MONO = "JetBrains Mono"
    FONT_FALLBACK = "Helvetica Neue"

    # Display
    DISPLAY_LARGE = FontSpec(FONT_FAMILY, 32, "bold")
    DISPLAY = FontSpec(FONT_FAMILY, 24, "bold")

    # Headings
    H1 = FontSpec(FONT_FAMILY, 20, "bold")
    H2 = FontSpec(FONT_FAMILY, 16, "bold")
    H3 = FontSpec(FONT_FAMILY, 14, "bold")

    # Body
    BODY_LARGE = FontSpec(FONT_FAMILY, 15, "normal")
    BODY = FontSpec(FONT_FAMILY, 13, "normal")
    BODY_SMALL = FontSpec(FONT_FAMILY, 12, "normal")

    # Monospace (code, terminal, transcripts)
    CODE = FontSpec(FONT_MONO, 13, "normal")
    CODE_SMALL = FontSpec(FONT_MONO, 11, "normal")

    # Labels & UI
    LABEL = FontSpec(FONT_FAMILY, 11, "bold")
    CAPTION = FontSpec(FONT_FAMILY, 11, "normal")
    BUTTON = FontSpec(FONT_FAMILY, 13, "bold")

    @classmethod
    def to_ctk(cls, spec: FontSpec) -> tuple:
        """Convert to CustomTkinter font tuple."""
        return (spec.family, spec.size, spec.weight)
