#!/usr/bin/env bash
# ==============================================================================
# JARVIS OS — macOS Permissions Setup Guide
# Opens the correct System Settings panels for each permission JARVIS needs.
#
# Usage: bash scripts/grant_permissions.sh
# ==============================================================================

echo ""
echo "  JARVIS OS — macOS Permissions"
echo "  =============================="
echo ""
echo "  JARVIS needs 4 permissions on macOS."
echo "  Each one opens the correct System Settings panel."
echo "  Add 'Terminal' (or your IDE/Python) to each list."
echo ""
echo "  Press ENTER after granting each permission..."
echo ""

open_pref() {
    local name="$1"
    local pref="$2"
    local why="$3"

    echo "  [$name]"
    echo "  Why: $why"
    echo "  Opening System Settings..."
    open "x-apple.systempreferences:com.apple.preference.security?$pref" 2>/dev/null \
        || open "/System/Library/PreferencePanes/Security.prefPane"
    read -r -p "  Press ENTER once you've added Terminal to $name > "
    echo ""
}

open_pref \
    "Microphone" \
    "Privacy_Microphone" \
    "Lets JARVIS hear your voice for wake word detection and commands."

open_pref \
    "Accessibility" \
    "Privacy_Accessibility" \
    "Lets JARVIS control keyboard & mouse for desktop automation."

open_pref \
    "Screen Recording" \
    "Privacy_ScreenCapture" \
    "Lets JARVIS take screenshots and read text from your screen."

open_pref \
    "Full Disk Access" \
    "Privacy_AllFiles" \
    "Lets JARVIS navigate and read files across your entire filesystem."

echo ""
echo "  ✅ All permissions configured!"
echo ""
echo "  If JARVIS still can't access something, you may need to:"
echo "    1. Add the specific Python binary from .venv/bin/python"
echo "    2. Or run JARVIS from Terminal which already has permissions"
echo ""
