"""
Activation Dialog - ввод ключа активации
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QMessageBox,
)
from PyQt6.QtGui import QFont

from ...styles import COLORS, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE

if TYPE_CHECKING:
    from ...activation import ActivationManager


class ActivationWorker(QThread):
    """Background worker for activation validation"""
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, manager: "ActivationManager", key: str, email: Optional[str] = None):
        super().__init__()
        self.manager = manager
        self.key = key
        self.email = email
    
    def run(self):
        success, message = self.manager.activate(self.key, self.email)
        self.finished.emit(success, message)


class ActivationDialog(QDialog):
    """Dialog for entering activation key"""
    
    def __init__(
        self,
        activation_manager: "ActivationManager",
        error_message: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.activation = activation_manager
        self.error_message = error_message
        self._worker: Optional[ActivationWorker] = None
        
        self.setWindowTitle("Активация Arvis")
        self.setFixedSize(500, 380)
        self.setModal(True)
        
        # Disable close button if activation required
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_primary']};
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
            QLineEdit {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """)
        
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Logo/Title section
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)
        
        # Icon
        icon_label = QLabel("🔐")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        title_layout.addWidget(icon_label)
        
        # Title
        title = QLabel("Активация Arvis")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 22px;
            font-weight: bold;
        """)
        title_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Введите ваш ключ активации")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        title_layout.addWidget(subtitle)
        
        layout.addLayout(title_layout)
        
        # Error message (if any)
        if self.error_message:
            error_frame = QFrame()
            error_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(200, 50, 50, 0.2);
                    border: 1px solid {COLORS['error']};
                    border-radius: 6px;
                    padding: 8px;
                }}
            """)
            error_layout = QHBoxLayout(error_frame)
            error_layout.setContentsMargins(12, 8, 12, 8)
            
            error_icon = QLabel("⚠️")
            error_layout.addWidget(error_icon)
            
            error_text = QLabel(self.error_message)
            error_text.setStyleSheet(f"color: {COLORS['error']}; font-size: 12px;")
            error_text.setWordWrap(True)
            error_layout.addWidget(error_text, 1)
            
            layout.addWidget(error_frame)
        
        # Key input
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("ARVIS-XXXX-XXXXXXXX")
        self.key_input.setMaxLength(50)
        layout.addWidget(self.key_input)
        
        # Email input (optional)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (необязательно)")
        self.email_input.setMaxLength(100)
        layout.addWidget(self.email_input)
        
        # Key format hint
        hint = QLabel(
            "Поддерживаемые форматы ключей:\n"
            "• ARVIS-BETA-XXXXXXXX — бета-тестирование\n"
            "• ARVIS-MNTH-XXXXXXXX-YYMM — месячная подписка\n"
            "• ARVIS-PERM-XXXXXXXX-XXXX — постоянная лицензия\n"
            "• ARVIS-TRIAL-XXXXXXXX — пробный период"
        )
        hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(hint)
        
        layout.addStretch(1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_activate = QPushButton("Активировать")
        self.btn_activate.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_activate.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_activate, 2)
        
        self.btn_exit = QPushButton("Выход")
        self.btn_exit.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_exit.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_exit, 1)
        
        layout.addLayout(btn_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(self.status_label)
    
    def _connect_signals(self):
        self.btn_activate.clicked.connect(self._on_activate)
        self.btn_exit.clicked.connect(self._on_exit)
        self.key_input.returnPressed.connect(self._on_activate)
        self.email_input.returnPressed.connect(self._on_activate)
    
    def _on_activate(self):
        """Handle activation button click"""
        key = self.key_input.text().strip()
        email = self.email_input.text().strip() or None
        
        if not key:
            self._show_error("Введите ключ активации")
            return
        
        # Validate format locally first
        format_valid, format_error, _ = self.activation.validate_key_format(key)
        if not format_valid:
            self._show_error(format_error)
            return
        
        # Start activation in background
        self._set_loading(True)
        self.status_label.setText("Проверка ключа...")
        
        self._worker = ActivationWorker(self.activation, key, email)
        self._worker.finished.connect(self._on_activation_result)
        self._worker.start()
    
    def _on_activation_result(self, success: bool, message: str):
        """Handle activation result"""
        self._set_loading(False)
        
        if success:
            self.status_label.setText("")
            self.accept()
        else:
            self._show_error(message)
    
    def _on_exit(self):
        """Handle exit button - close application"""
        reply = QMessageBox.question(
            self,
            "Выход",
            "Без активации Arvis не будет работать.\nВы уверены, что хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.reject()
    
    def _set_loading(self, loading: bool):
        """Set loading state"""
        self.btn_activate.setEnabled(not loading)
        self.btn_exit.setEnabled(not loading)
        self.key_input.setEnabled(not loading)
        self.email_input.setEnabled(not loading)
        
        if loading:
            self.btn_activate.setText("Проверка...")
        else:
            self.btn_activate.setText("Активировать")
    
    def _show_error(self, message: str):
        """Show error message"""
        self.status_label.setText(f"❌ {message}")
        self.status_label.setStyleSheet(f"color: {COLORS['error']}; font-size: 12px;")


class ActivationStatusWidget(QFrame):
    """Widget displaying activation status (for settings/account page)"""
    
    deactivate_requested = pyqtSignal()
    
    def __init__(self, activation_manager: "ActivationManager", parent=None):
        super().__init__(parent)
        self.activation = activation_manager
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        self._build_ui()
        self.refresh()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("🔐 Лицензия")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 15px;
            font-weight: bold;
        """)
        header.addWidget(title)
        header.addStretch(1)
        
        self.status_badge = QLabel()
        header.addWidget(self.status_badge)
        
        layout.addLayout(header)
        
        # Info grid
        self.info_layout = QVBoxLayout()
        self.info_layout.setSpacing(6)
        layout.addLayout(self.info_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.btn_refresh = QPushButton("🔄 Обновить")
        self.btn_refresh.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_refresh.clicked.connect(self.refresh)
        btn_layout.addWidget(self.btn_refresh)
        
        self.btn_deactivate = QPushButton("Деактивировать")
        self.btn_deactivate.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {COLORS['error']};
            }}
        """)
        self.btn_deactivate.clicked.connect(self._on_deactivate)
        btn_layout.addWidget(self.btn_deactivate)
        
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)
    
    def refresh(self):
        """Refresh activation status"""
        status = self.activation.get_status()
        
        # Update badge
        if status["activated"]:
            self.status_badge.setText("✅ Активировано")
            self.status_badge.setStyleSheet(f"""
                color: {COLORS['success']};
                background-color: rgba(80, 200, 120, 0.2);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            """)
        else:
            self.status_badge.setText("❌ Не активировано")
            self.status_badge.setStyleSheet(f"""
                color: {COLORS['error']};
                background-color: rgba(200, 50, 50, 0.2);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            """)
        
        # Clear old info
        while self.info_layout.count():
            item = self.info_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
        
        # Add info rows
        if status["activated"]:
            info_items = []
            
            if status["key_type_name"]:
                info_items.append(("Тип лицензии:", status["key_type_name"]))
            
            if status["key_preview"]:
                info_items.append(("Ключ:", status["key_preview"]))
            
            if status["email"]:
                info_items.append(("Email:", status["email"]))
            
            if status["days_remaining"] is not None:
                if status["days_remaining"] > 0:
                    info_items.append(("Осталось дней:", str(status["days_remaining"])))
                elif status["days_remaining"] == 0:
                    info_items.append(("Статус:", "Истекает сегодня"))
            
            if status["offline_mode"]:
                info_items.append(("Режим:", "Офлайн (проверка при подключении)"))
            
            for label, value in info_items:
                row = QHBoxLayout()
                
                lbl = QLabel(label)
                lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
                row.addWidget(lbl)
                
                val = QLabel(value)
                val.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
                row.addWidget(val)
                
                row.addStretch(1)
                self.info_layout.addLayout(row)
        else:
            msg = QLabel(status.get("message", "Требуется активация"))
            msg.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            self.info_layout.addWidget(msg)
    
    def _on_deactivate(self):
        """Handle deactivate button"""
        reply = QMessageBox.question(
            self,
            "Деактивация",
            "Вы уверены, что хотите деактивировать?\n"
            "Потребуется повторный ввод ключа.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.activation.deactivate()
            self.refresh()
            self.deactivate_requested.emit()
