"""
JARVIS OS Design System — Colors
==================================
A professional dark-mode color palette inspired by high-end developer tools.

Design principles:
- Dark by default (eyes on screen for hours)
- High contrast text (WCAG AA minimum)
- Purple accent (intelligence, premium feel)
- Red for destructive/danger states
- Green for success/safe states
- Yellow for warnings/pending confirmation

Usage:
    from jarvis.ui.design_system.colors import JarvisColors
    bg = JarvisColors.SURFACE_PRIMARY   # "#0F0F13"
    accent = JarvisColors.ACCENT        # "#7C3AED"
"""


class JarvisColors:
    """All JARVIS OS colors as hex strings."""

    # --- Backgrounds (darkest to lightest) ---
    BACKGROUND = "#0A0A0F"          # App background (deepest)
    SURFACE_PRIMARY = "#0F0F13"     # Main surface
    SURFACE_SECONDARY = "#141419"   # Elevated surface
    SURFACE_TERTIARY = "#1A1A22"    # Cards, panels
    SURFACE_HOVER = "#1F1F2A"       # Hover state

    # --- Borders ---
    BORDER_SUBTLE = "#252530"       # Very subtle dividers
    BORDER_DEFAULT = "#2E2E3D"      # Default borders
    BORDER_STRONG = "#3D3D52"       # Prominent borders

    # --- Text ---
    TEXT_PRIMARY = "#F0F0F8"        # Main text (near-white)
    TEXT_SECONDARY = "#9B9BB8"      # Secondary/muted text
    TEXT_TERTIARY = "#6B6B8A"       # Placeholder, hints
    TEXT_DISABLED = "#3F3F58"       # Disabled state

    # --- Accent (Purple) ---
    ACCENT = "#7C3AED"              # Primary accent
    ACCENT_HOVER = "#8B5CF6"        # Hover state
    ACCENT_LIGHT = "#A78BFA"        # Light variant (text on dark)
    ACCENT_SUBTLE = "#1E1340"       # Accent background tint

    # --- Status: Success ---
    SUCCESS = "#10B981"
    SUCCESS_LIGHT = "#34D399"
    SUCCESS_SUBTLE = "#0D2B20"

    # --- Status: Warning ---
    WARNING = "#F59E0B"
    WARNING_LIGHT = "#FCD34D"
    WARNING_SUBTLE = "#2D2010"

    # --- Status: Error/Danger ---
    DANGER = "#EF4444"
    DANGER_HOVER = "#F87171"
    DANGER_SUBTLE = "#2D1010"

    # --- Status: Info ---
    INFO = "#3B82F6"
    INFO_LIGHT = "#60A5FA"
    INFO_SUBTLE = "#0D1F3D"

    # --- Voice Visualization ---
    VOICE_IDLE = TEXT_TERTIARY
    VOICE_LISTENING = ACCENT_LIGHT
    VOICE_SPEAKING = SUCCESS_LIGHT
    VOICE_THINKING = WARNING_LIGHT

    # --- Scrollbar ---
    SCROLLBAR_TRACK = SURFACE_PRIMARY
    SCROLLBAR_THUMB = BORDER_DEFAULT
    SCROLLBAR_THUMB_HOVER = BORDER_STRONG

    @classmethod
    def all_colors(cls) -> dict[str, str]:
        return {
            k: v for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str)
        }
