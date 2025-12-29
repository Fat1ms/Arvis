"""
Loading Screen for Arvis - показывается после логина
Отображает прогресс загрузки моделей и инициализации компонентов
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from version import get_version


class AnimatedOrb(QSvgWidget):
    """Animated Arvis orb widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
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
        self.animation_timer.start(2000)

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


class LoadingScreen(QWidget):
    """Loading screen показывается после логина для загрузки компонентов"""

    loading_complete = pyqtSignal()  # Сигнал завершения загрузки

    def __init__(self):
        super().__init__()
        self.progress_value = 0
        self.init_ui()

    def init_ui(self):
        """Initialize UI components"""
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        # Match provided mockup size
        self.setFixedSize(455, 455)

        # Тёмный фон
        self.setStyleSheet(
            """
            QWidget {
                background-color: rgb(43, 43, 43);
                border-radius: 15px;
                border: none;
            }
        """
        )

        # Center the window
        self.center_window()

        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title_label = QLabel("Arvis")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-size: 26px;
                font-weight: bold;
                background: transparent;
                margin-bottom: 6px;
            }
        """
        )

        # Animated orb
        self.orb = AnimatedOrb()
        orb_container = QWidget()
        orb_container.setStyleSheet("background: transparent;")
        orb_layout = QVBoxLayout()
        orb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orb_layout.addWidget(self.orb)
        orb_container.setLayout(orb_layout)

        # Status label
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 15px;
                background: transparent;
                min-height: 44px;
                max-width: 360px;
            }
        """
        )

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                text-align: center;
                background-color: rgba(60, 60, 60, 0.8);
                color: white;
                font-size: 13px;
                font-weight: bold;
                min-height: 28px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a9eff, stop:1 #5aa9ff);
                border-radius: 6px;
            }
        """
        )

        # Detailed step label
        self.step_label = QLabel("")
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step_label.setWordWrap(True)
        self.step_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
                background: transparent;
                min-height: 30px;
            }
        """
        )

        # Version
        version_label = QLabel(f"v{get_version()}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 11px;
                background: transparent;
                margin-top: 10px;
            }
        """
        )

        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(orb_container)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.step_label)
        layout.addStretch(1)
        layout.addWidget(version_label)

        self.setLayout(layout)

        # Start orb animation
        self.orb.start_animation()

    def center_window(self):
        """Center window on screen"""
        from PyQt6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def set_status(self, message: str, progress: Optional[int] = None, step: str = ""):
        """Update loading status"""
        try:
            self.status_label.setText(message)

            if progress is not None:
                self.progress_value = max(0, min(100, progress))
                self.progress_bar.setValue(self.progress_value)

            if step:
                self.step_label.setText(step)

            # Process events to update UI
            from PyQt6.QtWidgets import QApplication

            QApplication.processEvents()

        except Exception as e:
            print(f"Error updating loading status: {e}")

    def complete_loading(self):
        """Mark loading as complete"""
        try:
            self.set_status("Загрузка завершена!", 100, "")
            self.orb.stop_animation()

            # Emit signal after short delay
            QTimer.singleShot(500, self._emit_complete)

        except Exception as e:
            print(f"Error completing loading: {e}")

    def _emit_complete(self):
        """Emit loading complete signal and close"""
        try:
            self.loading_complete.emit()
            self.close()
        except Exception as e:
            print(f"Error emitting complete signal: {e}")

    def closeEvent(self, event):
        """Handle close event"""
        try:
            self.orb.stop_animation()
        except Exception:
            pass
        event.accept()
