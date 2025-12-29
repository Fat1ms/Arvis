"""Floating notification widget for unobtrusive status messages."""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton, QWidget


class FloatingNotification(QFrame):
    """Lightweight floating popup to display temporary notifications."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FloatingNotification")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._setup_ui()

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_notification)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(220)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_anim.finished.connect(self._on_fade_finished)

        self._pending_hide = False
        self.hide()

    def _setup_ui(self) -> None:
        self.setStyleSheet(
            """
            QFrame#FloatingNotification {
                background-color: rgba(25, 25, 25, 230);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 40);
            }
            QFrame#FloatingNotification QLabel {
                color: rgba(255, 255, 255, 0.95);
                font-size: 13px;
            }
            QFrame#FloatingNotification QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.6);
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 0 4px;
            }
            QFrame#FloatingNotification QPushButton:hover {
                color: rgba(255, 255, 255, 0.9);
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 12, 14)
        layout.setSpacing(12)

        self._label = QLabel("", self)
        self._label.setWordWrap(True)
        self._label.setMinimumWidth(200)
        self._label.setMaximumWidth(360)
        layout.addWidget(self._label, 1)

        self._close_btn = QPushButton("×", self)
        self._close_btn.clicked.connect(self.hide_notification)
        layout.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignTop)  # type: ignore[attr-defined]

    # Public API -----------------------------------------------------------------
    def show_message(self, message: str, duration_ms: int = 6000) -> None:
        """Display a notification with optional auto-dismiss."""
        self._hide_timer.stop()
        self._fade_anim.stop()
        self._pending_hide = False

        self._label.setText(message)
        self.adjustSize()
        self._reposition()

        self._opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()
        self._start_fade(0.0, 1.0)

        if duration_ms > 0:
            self._hide_timer.start(duration_ms)

    def hide_notification(self) -> None:
        """Hide the notification with fade-out animation."""
        if not self.isVisible():
            return

        self._hide_timer.stop()
        self._fade_anim.stop()
        current_opacity = self._opacity_effect.opacity()
        self._start_fade(current_opacity, 0.0)

    def reposition(self) -> None:
        """Recalculate widget position relative to its parent."""
        self._reposition()

    # Internal helpers -----------------------------------------------------------
    def _start_fade(self, start: float, end: float) -> None:
        self._pending_hide = end <= 0.0
        self._fade_anim.setStartValue(start)
        self._fade_anim.setEndValue(end)
        self._fade_anim.start()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return

        parent_rect = parent.rect()
        self.adjustSize()

        x = parent_rect.right() - self.width() - 24
        y = parent_rect.bottom() - self.height() - 120
        x = max(16, x)
        y = max(60, y)
        self.move(int(x), int(y))

    def _on_fade_finished(self) -> None:
        if self._pending_hide:
            self._pending_hide = False
            self.hide()
        else:
            self._opacity_effect.setOpacity(1.0)
