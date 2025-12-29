from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from PyQt6.QtSvg import QSvgRenderer

from src.gui.status_panel import ArvisOrb
from i18n import _

class SvgButton(QPushButton):
    """Custom button with SVG icons"""

    def __init__(self, svg_normal: str, svg_active: Optional[str] = None, size=(40, 40), parent=None):
        super().__init__(parent)
        self.svg_normal = svg_normal
        self.svg_active = svg_active or svg_normal
        self.setFixedSize(*size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("border: none; background: transparent;")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Determine which SVG to use
        is_active = self.isChecked() or self.isDown() or self.underMouse()
        svg_path = Path(self.svg_active if is_active else self.svg_normal)
        
        if svg_path.exists():
            renderer = QSvgRenderer(str(svg_path))
            # Draw centered
            renderer.render(painter, QRectF(self.rect()))

class CompactWidget(QWidget):
    """
    Compact mode widget containing the Orb and control buttons.
    """
    open_chat_clicked = pyqtSignal()
    mic_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(0)
        
        # 1. Orb Container (Centered, taking most space)
        orb_container = QWidget()
        orb_layout = QHBoxLayout(orb_container)
        orb_layout.setContentsMargins(0, 0, 0, 0)
        
        self.orb = ArvisOrb()
        self.orb.setFixedSize(200, 200)  # Slightly larger orb
        
        orb_layout.addStretch()
        orb_layout.addWidget(self.orb)
        orb_layout.addStretch()
        
        layout.addWidget(orb_container, 1) # Stretch factor 1
        
        # 2. Bottom Control Bar
        # Container for the rounded rectangle background
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 10, 0, 10)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # The actual bar with background
        self.control_bar = QFrame()
        self.control_bar.setFixedSize(180, 70) # Reduced size since one button is gone
        self.control_bar.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 240);
                border-radius: 35px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        # Layout inside the bar
        bar_layout = QHBoxLayout(self.control_bar)
        bar_layout.setContentsMargins(20, 5, 20, 5)
        bar_layout.setSpacing(30) # Space between icons
        bar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Buttons
        # Mic
        self.btn_mic = SvgButton(
            "UXUI/Button/Button_micr_norm.svg",
            "UXUI/Button/Button_micr_act.svg",
            size=(55, 55) # Mic is slightly larger usually
        )
        self.btn_mic.setCheckable(True)
        self.btn_mic.clicked.connect(self.mic_clicked)
        self.btn_mic.setToolTip(_("Микрофон"))
        
        # Settings
        self.btn_settings = SvgButton(
            "UXUI/Button/Button_setings_norm.svg",
            "UXUI/Button/Button_setings_act.svg",
            size=(45, 45)
        )
        self.btn_settings.clicked.connect(self.settings_clicked)
        self.btn_settings.setToolTip(_("Настройки"))
        
        bar_layout.addWidget(self.btn_mic)
        bar_layout.addWidget(self.btn_settings)
        
        bottom_layout.addWidget(self.control_bar)
        layout.addWidget(bottom_container)
        
        # Chat open button is now in MainWindow title bar.
        # Keep this widget clean (no duplicate overlay button).
        self.btn_chat = None
        
        self.setLayout(layout)
        
        # Global Style for this widget
        self.setStyleSheet("background-color: transparent;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # No overlay button to reposition.

    def set_orb_state(self, state):
        self.orb.set_state(state)
        
    def set_mic_active(self, active: bool):
        self.btn_mic.setChecked(active)
