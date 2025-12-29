"""
Splash Screen for Arvis
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional, cast

from PyQt6.QtCore import QPropertyAnimation, QRect
from PyQt6.QtCore import Qt as QtCoreQt
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPixmap
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QProgressBar, QVBoxLayout, QWidget

# Добавляем путь к корню проекта для импорта version
sys.path.append(str(Path(__file__).parent.parent.parent))
from version import get_version

Qt = cast(Any, QtCoreQt)


class AnimatedOrb(QSvgWidget):
    """Animated Arvis orb widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        # Ensure no visible square/background around orb
        self.setStyleSheet("background: transparent; border: none;")
        self.current_state = "norm"
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_orb)
        self.load_orb()

    def load_orb(self):
        """Load orb SVG"""
        orb_path = Path("UXUI/Orb/Orb_norm.svg")
        if orb_path.exists():
            try:
                self.load(str(orb_path))
            except Exception as e:
                print(f"Error loading SVG: {e}")
                self.create_placeholder()
        else:
            print(f"SVG file not found: {orb_path}")
            self.create_placeholder()

    def create_placeholder(self):
        """Create a simple placeholder if SVG loading fails"""
        self.setStyleSheet(
            """
            QSvgWidget {
                background-color: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5,
                                                fx: 0.3, fy: 0.3,
                                                stop: 0 #4a9eff,
                                                stop: 1 #1a5eff);
                border-radius: 60px;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
        """
        )

    def start_animation(self):
        """Start orb animation"""
        self.animation_timer.start(2000)  # Change state every 2 seconds

    def stop_animation(self):
        """Stop orb animation"""
        self.animation_timer.stop()

    def animate_orb(self):
        """Animate orb between states"""
        if self.current_state == "norm":
            orb_path = Path("UXUI/Orb/Orb_thinkin.svg")
            self.current_state = "thinking"
        else:
            orb_path = Path("UXUI/Orb/Orb_norm.svg")
            self.current_state = "norm"

        if orb_path.exists():
            self.load(str(orb_path))


class SplashScreen(QWidget):
    """Splash screen with animated orb and progress bar"""

    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.progress_value = 0
        self.init_ui()
        self.setup_animations()

    def init_ui(self):
        """Initialize UI components"""
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        # Убираем прозрачный фон, который может вызывать проблемы в Windows
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # Match provided mockup size
        self.setFixedSize(455, 455)

        # Устанавливаем тёмный фон
        self.setStyleSheet(
            """
            QWidget {
                background-color: rgb(43, 43, 43);
                border-radius: 15px;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
        """
        )

        # Center the window
        self.center_window()

        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Title and version
        title_label = QLabel("Arvis")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-size: 32px;
                font-weight: bold;
                background: transparent;
            }
        """
        )

        version_label = QLabel(f"v{get_version()}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.7);
                font-size: 14px;
                background: transparent;
            }
        """
        )

        # Animated orb
        self.orb = AnimatedOrb()
        orb_layout = QVBoxLayout()
        orb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orb_layout.addWidget(self.orb)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(250)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                background-color: rgba(43, 43, 43, 0.8);
                text-align: center;
                color: white;
                font-weight: bold;
            }

            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #4a9eff, stop: 1 #1a5eff);
                border-radius: 8px;
            }
        """
        )

        # Status label
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                background: transparent;
            }
        """
        )

        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(version_label)
        # Space before orb
        layout.addSpacing(24)
        layout.addLayout(orb_layout)
        # Space between orb and progress bar
        layout.addSpacing(40)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        # Space before status
        layout.addSpacing(12)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # Убираем эффект тени, который может вызывать проблемы в Windows
        # shadow = QGraphicsDropShadowEffect()
        # shadow.setBlurRadius(20)
        # shadow.setColor(QColor(0, 0, 0, 160))
        # shadow.setOffset(0, 5)
        # self.setGraphicsEffect(shadow)

    def center_window(self):
        """Center window on screen"""
        from PyQt6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen is None:
            return
        try:
            geom = screen.availableGeometry()
        except Exception:
            geom = screen.geometry()
        size = self.frameGeometry()
        size.moveCenter(geom.center())
        self.move(size.topLeft())

    def setup_animations(self):
        """Setup progress bar animation"""
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)

    def show(self):
        """Show splash screen and start animations"""
        super().show()
        self.orb.start_animation()
        self.progress_timer.start(100)  # Update every 100ms instead of 50ms

    def update_progress(self):
        """Update progress bar"""
        # Защита от бесконечного цикла
        if not hasattr(self, "progress_timer") or not self.progress_timer.isActive():
            return

        self.progress_value += 1

        # Ограничиваем максимальное значение
        if self.progress_value > 110:  # Дополнительная защита
            self.progress_timer.stop()
            self.orb.stop_animation()
            return

        self.progress_bar.setValue(min(self.progress_value, 100))

        # Update status messages
        if self.progress_value < 20:
            self.status_label.setText("Загрузка конфигурации...")
        elif self.progress_value < 40:
            self.status_label.setText("Инициализация модулей...")
        elif self.progress_value < 60:
            self.status_label.setText("Подключение к Ollama...")
        elif self.progress_value < 80:
            self.status_label.setText("Настройка TTS/STT...")
        elif self.progress_value < 100:
            self.status_label.setText("Финализация...")
        else:
            self.status_label.setText("Готово!")
            self.progress_timer.stop()
            self.orb.stop_animation()
            QTimer.singleShot(500, self.finished.emit)

    def force_close(self):
        """Принудительно закрыть сплэш"""
        try:
            if hasattr(self, "progress_timer") and self.progress_timer.isActive():
                self.progress_timer.stop()
            if hasattr(self, "orb"):
                self.orb.stop_animation()
            self.close()
        except Exception as e:
            print(f"Error closing splash: {e}")

    def set_status(self, text: Optional[str] = None, progress: Optional[int] = None):
        """Update status message and optionally progress value externally."""
        if text is not None:
            try:
                self.status_label.setText(str(text))
            except Exception:
                pass
        if progress is not None:
            try:
                value = max(0, min(100, int(progress)))
                self.progress_bar.setValue(value)
            except Exception:
                pass

    def paintEvent(self, event):
        """Custom paint event - убираем кастомную отрисовку, используем CSS стили"""
        # Оставляем стандартную отрисовку через CSS стили
        super().paintEvent(event)
