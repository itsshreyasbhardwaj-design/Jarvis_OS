"""
JARVIS OS — Main Entry Point
"""

from __future__ import annotations

from jarvis.core.application import JarvisOS


def main() -> None:
    """Production entry point (called by 'jarvis' CLI command)."""
    from dotenv import load_dotenv

    load_dotenv()  # let an ANTHROPIC_API_KEY in .env reach the LLM
    app = JarvisOS()
    app.run()


if __name__ == "__main__":
    main()
