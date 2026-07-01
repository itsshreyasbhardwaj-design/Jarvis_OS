"""
Main JARVIS Window (PySide6)
=============================
The primary floating window. Minimal, professional, always accessible.

Layout:
  ┌─────────────────────────┐
  │  JARVIS   [●] [⚙] [×]  │  ← Title bar with status
  ├─────────────────────────┤
  │                         │
  │   Conversation area     │  ← Scrollable chat log
  │                         │
  ├─────────────────────────┤
  │  [🎤] [          ] [▶]  │  ← Input row (voice + text)
  └─────────────────────────┘
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger

from jarvis.ui.design_system.colors import JarvisColors


class MainWindow:
    """
    Main JARVIS OS window built with PySide6 (Qt6).

    Usage:
        window = MainWindow(on_input=handle_user_input)
        window.build()
        window.show()
        window.add_message("assistant", "Good evening, sir.")
    """

    WINDOW_WIDTH = 520
    WINDOW_HEIGHT = 680
    MIN_WIDTH = 400
    MIN_HEIGHT = 500

    def __init__(
        self,
        on_input: Callable[[str], None] | None = None,
        on_voice_toggle: Callable[[], None] | None = None,
    ) -> None:
        self._on_input = on_input
        self._on_voice_toggle = on_voice_toggle
        self._app: Any = None
        self._window: Any = None
        self._conversation: Any = None
        self._input_entry: Any = None
        self._voice_btn: Any = None
        self._status_label: Any = None
        self._listening = False

    def build(self) -> None:
        """Build the window (call from main thread)."""
        try:
            from PySide6.QtWidgets import (
                QApplication,
                QHBoxLayout,
                QLabel,
                QLineEdit,
                QMainWindow,
                QPushButton,
                QScrollArea,
                QVBoxLayout,
                QWidget,
            )
        except ImportError as exc:
            raise ImportError(
                "PySide6 required: pip install PySide6>=6.7.0"
            ) from exc

        self._app = QApplication.instance() or QApplication([])

        self._window = QMainWindow()
        self._window.setWindowTitle("JARVIS OS")
        self._window.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self._window.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        # Apply dark stylesheet
        self._window.setStyleSheet(f"""
            QMainWindow {{ background-color: {JarvisColors.BACKGROUND}; }}
            QWidget {{
                background-color: {JarvisColors.BACKGROUND};
                color: {JarvisColors.TEXT_PRIMARY};
            }}
            QScrollArea {{ border: none; }}
            QLineEdit {{
                background-color: {JarvisColors.SURFACE};
                color: {JarvisColors.TEXT_PRIMARY};
                border: 1px solid {JarvisColors.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {JarvisColors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {JarvisColors.PRIMARY_HOVER}; }}
        """)

        central = QWidget()
        self._window.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title bar
        titlebar = self._build_titlebar(QWidget, QHBoxLayout, QLabel, QPushButton)
        layout.addWidget(titlebar)

        # Conversation area
        self._conversation, scroll = self._build_conversation(
            QScrollArea, QWidget, QVBoxLayout
        )
        layout.addWidget(scroll, stretch=1)

        # Input row
        input_row = self._build_input_row(QWidget, QHBoxLayout, QLineEdit, QPushButton)
        layout.addWidget(input_row)

        logger.debug("Main window built (PySide6)")

    def _build_titlebar(
        self, Widget: Any, HBox: Any, Label: Any, Button: Any
    ) -> Any:
        bar = Widget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"background-color: {JarvisColors.SURFACE};")
        layout = HBox(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        title = Label("⬡ JARVIS")
        title.setStyleSheet(
            f"color: {JarvisColors.PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)
        layout.addStretch()

        self._status_label = Label("●")
        self._status_label.setStyleSheet(f"color: {JarvisColors.SUCCESS}; font-size: 20px;")
        layout.addWidget(self._status_label)
        return bar

    def _build_conversation(
        self, ScrollArea: Any, Widget: Any, VBox: Any
    ) -> tuple[Any, Any]:
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        content = Widget()
        layout = VBox(content)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addStretch()
        scroll.setWidget(content)
        return layout, scroll

    def _build_input_row(
        self, Widget: Any, HBox: Any, LineEdit: Any, Button: Any
    ) -> Any:
        row = Widget()
        row.setFixedHeight(64)
        row.setStyleSheet(f"background-color: {JarvisColors.SURFACE}; border-top: 1px solid {JarvisColors.BORDER};")  # noqa: E501
        layout = HBox(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self._voice_btn = Button("🎤")
        self._voice_btn.setFixedSize(40, 40)
        self._voice_btn.setStyleSheet(
            f"background-color: {JarvisColors.SURFACE}; border: 1px solid {JarvisColors.BORDER}; border-radius: 20px;"  # noqa: E501
        )
        if self._on_voice_toggle:
            self._voice_btn.clicked.connect(self._on_voice_toggle)
        layout.addWidget(self._voice_btn)

        self._input_entry = LineEdit()
        self._input_entry.setPlaceholderText("Ask JARVIS anything…")
        if self._on_input:
            self._input_entry.returnPressed.connect(self._handle_input)
        layout.addWidget(self._input_entry, stretch=1)

        send_btn = Button("▶")
        send_btn.setFixedSize(40, 40)
        send_btn.clicked.connect(self._handle_input)
        layout.addWidget(send_btn)
        return row

    def _handle_input(self) -> None:
        if self._input_entry and self._on_input:
            text = self._input_entry.text().strip()
            if text:
                self._on_input(text)
                self._input_entry.clear()

    def add_message(self, role: str, content: str) -> None:
        """Add a chat bubble to the conversation area."""
        if not self._conversation:
            return
        try:
            from PySide6.QtWidgets import QLabel
            label = QLabel(f"{'You' if role == 'user' else 'JARVIS'}: {content}")
            label.setWordWrap(True)
            color = JarvisColors.TEXT_SECONDARY if role == "user" else JarvisColors.TEXT_PRIMARY
            label.setStyleSheet(
                f"color: {color}; padding: 8px 12px; background: {JarvisColors.SURFACE};"
                " border-radius: 8px; margin: 2px 0;"
            )
            # Insert before stretch (last item)
            count = self._conversation.count()
            self._conversation.insertWidget(count - 1, label)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not add message to UI: {}", e)

    def set_status(self, listening: bool) -> None:
        """Update the status indicator dot."""
        self._listening = listening
        if self._status_label:
            color = JarvisColors.WARNING if listening else JarvisColors.SUCCESS
            self._status_label.setStyleSheet(f"color: {color}; font-size: 20px;")

    def show(self) -> None:
        """Show the window."""
        if self._window:
            self._window.show()

    def mainloop(self) -> None:
        """Enter the Qt event loop."""
        if self._app:
            self._app.exec()
