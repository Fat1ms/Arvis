"""
Two-Factor Authentication Verification Dialog
Диалог верификации двухфакторной аутентификации

Phase 2 Day 5: 2FA Implementation
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from i18n import _
from utils.logger import ModuleLogger
from utils.security import AuditEventType, AuditLogger, User, UserStorage, get_totp_manager


class TwoFactorVerificationDialog(QDialog):
    """Dialog for verifying TOTP token during login"""

    def __init__(self, parent=None, user: Optional[User] = None, storage: Optional[UserStorage] = None):
        super().__init__(parent)
        self.logger = ModuleLogger("TwoFactorVerificationDialog")
        self.user = user
        self.storage = storage
        self.totp = get_totp_manager()
        self.audit = AuditLogger()

        # Timer for TOTP countdown
        self.remaining_seconds = 30
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)

        # Backup code mode
        self.backup_mode = False

        if not user:
            raise ValueError("User is required for 2FA verification")

        self.logger.info(f"2FA verification dialog opened for user: {user.username}")

        self.init_ui()
        self._start_timer()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(_("Двухфакторная аутентификация"))
        self.setFixedSize(450, 350)
        self.setModal(True)

        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Custom title bar
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Content
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Icon and title
        icon_label = QLabel("🔐")
        icon_label.setStyleSheet(
            """
            QLabel {
                font-size: 48px;
                padding: 10px;
            }
        """
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(icon_label)

        title_label = QLabel(_("Введите код аутентификации"))
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)

        # Description
        self.description_label = QLabel(_("Введите 6-значный код из приложения аутентификатора"))
        self.description_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
            }
        """
        )
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label.setWordWrap(True)
        content_layout.addWidget(self.description_label)

        # Timer label
        self.timer_label = QLabel()
        self.timer_label.setStyleSheet(
            """
            QLabel {
                color: rgba(74, 158, 255, 1.0);
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
        """
        )
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.timer_label)
        self._update_timer()

        # Token input
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText(_("000 000"))
        self.token_input.setMaxLength(7)  # 6 digits + 1 space
        self.token_input.setStyleSheet(
            """
            QLineEdit {
                background-color: rgba(60, 60, 60, 1.0);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                padding: 15px;
                font-size: 20px;
                font-weight: bold;
                text-align: center;
                letter-spacing: 5px;
            }
            QLineEdit:focus {
                border: 2px solid rgba(74, 158, 255, 1.0);
            }
        """
        )
        self.token_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.token_input.textChanged.connect(self._format_token_input)
        self.token_input.returnPressed.connect(self._verify_token)
        content_layout.addWidget(self.token_input)

        # Backup code button
        self.backup_btn = QPushButton(_("📝 Использовать резервный код"))
        self.backup_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: rgba(255, 154, 74, 1.0);
                border: none;
                padding: 8px;
                font-size: 11px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: rgba(255, 154, 74, 0.8);
            }
        """
        )
        self.backup_btn.clicked.connect(self._toggle_backup_mode)
        content_layout.addWidget(self.backup_btn)

        content_widget.setLayout(content_layout)
        content_widget.setStyleSheet("background-color: rgb(43, 43, 43);")
        main_layout.addWidget(content_widget)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 10, 20, 20)

        cancel_btn = QPushButton(_("Отмена"))
        cancel_btn.setFixedHeight(35)
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(150, 150, 150, 0.8);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 30px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(150, 150, 150, 1.0);
            }
        """
        )
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()

        self.verify_btn = QPushButton(_("✓ Подтвердить"))
        self.verify_btn.setFixedHeight(35)
        self.verify_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(74, 158, 255, 0.8);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 30px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(74, 158, 255, 1.0);
            }
            QPushButton:disabled {
                background-color: rgba(100, 100, 100, 0.5);
                color: rgba(255, 255, 255, 0.3);
            }
        """
        )
        self.verify_btn.clicked.connect(self._verify_token)
        button_layout.addWidget(self.verify_btn)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # Focus on token input
        self.token_input.setFocus()

    def _create_title_bar(self) -> QWidget:
        """Create custom title bar"""
        title_bar = QWidget()
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet("background-color: rgb(43, 43, 43);")

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 4, 4, 4)

        title_label = QLabel(_("🔐 Двухфакторная аутентификация"))
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
        """
        )
        layout.addWidget(title_label)
        layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 74, 74, 0.8);
                border-radius: 3px;
            }
        """
        )
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

        title_bar.setLayout(layout)
        return title_bar

    def _start_timer(self):
        """Start TOTP countdown timer"""
        import time

        # Calculate remaining seconds in current 30-second window
        current_time = int(time.time())
        self.remaining_seconds = 30 - (current_time % 30)
        self.timer.start(1000)  # Update every second

    def _update_timer(self):
        """Update timer display"""
        self.remaining_seconds -= 1

        if self.remaining_seconds <= 0:
            self.remaining_seconds = 30

        # Color changes based on remaining time
        if self.remaining_seconds <= 5:
            color = "rgba(255, 74, 74, 1.0)"  # Red
        elif self.remaining_seconds <= 10:
            color = "rgba(255, 154, 74, 1.0)"  # Orange
        else:
            color = "rgba(74, 158, 255, 1.0)"  # Blue

        self.timer_label.setText(f"⏱️ {self.remaining_seconds}s")
        self.timer_label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }}
        """
        )

    def _format_token_input(self, text: str):
        """Format token input with space after 3 digits"""
        if self.backup_mode:
            return  # No formatting for backup codes

        # Remove all non-digit characters
        digits_only = "".join(c for c in text if c.isdigit())

        # Limit to 6 digits
        digits_only = digits_only[:6]

        # Add space after 3rd digit
        if len(digits_only) > 3:
            formatted = f"{digits_only[:3]} {digits_only[3:]}"
        else:
            formatted = digits_only

        # Update without triggering textChanged again
        if formatted != text:
            cursor_pos = self.token_input.cursorPosition()
            self.token_input.blockSignals(True)
            self.token_input.setText(formatted)
            self.token_input.setCursorPosition(min(cursor_pos, len(formatted)))
            self.token_input.blockSignals(False)

    def _toggle_backup_mode(self):
        """Toggle between TOTP and backup code mode"""
        self.backup_mode = not self.backup_mode

        if self.backup_mode:
            self.description_label.setText(_("Введите один из резервных кодов восстановления"))
            self.token_input.setPlaceholderText(_("XXXX-XXXX-XXXX"))
            self.token_input.setMaxLength(14)  # 12 chars + 2 dashes
            self.backup_btn.setText(_("🔢 Использовать код из приложения"))
            self.timer_label.hide()
            self.timer.stop()
        else:
            self.description_label.setText(_("Введите 6-значный код из приложения аутентификатора"))
            self.token_input.setPlaceholderText(_("000 000"))
            self.token_input.setMaxLength(7)
            self.backup_btn.setText(_("📝 Использовать резервный код"))
            self.timer_label.show()
            self._start_timer()

        self.token_input.clear()
        self.token_input.setFocus()

    def _verify_token(self):
        """Verify TOTP token or backup code"""
        code = self.token_input.text().strip().replace(" ", "").replace("-", "")

        if not code:
            QMessageBox.warning(self, _("Ошибка"), _("Введите код для подтверждения"))
            return

        if self.backup_mode:
            self._verify_backup_code(code)
        else:
            self._verify_totp_code(code)

    def _verify_totp_code(self, token: str):
        """Verify TOTP token"""
        if len(token) != 6 or not token.isdigit():
            QMessageBox.warning(self, _("Ошибка"), _("Код должен содержать 6 цифр"))
            return

        try:
            # Get encrypted secret from database
            if not self.storage:
                raise ValueError("Storage not provided")

            totp_data = self.storage.get_two_factor_data(self.user.user_id)
            if not totp_data or not totp_data.get("encrypted_secret"):
                self.logger.error("2FA data not found in database")
                QMessageBox.critical(self, _("Ошибка"), _("Данные двухфакторной аутентификации не найдены"))
                return

            # Decrypt secret
            secret = self.totp.decrypt_secret(totp_data["encrypted_secret"])

            # Verify token
            if self.totp.verify_token(secret, token):
                self.logger.info(f"2FA token verified for user: {self.user.username}")
                self.audit.log_event(
                    AuditEventType.TWO_FACTOR_VERIFIED, self.user.user_id, success=True, details={"method": "totp"}
                )
                self.accept()
            else:
                self.logger.warning(f"Invalid 2FA token for user: {self.user.username}")
                self.audit.log_event(
                    AuditEventType.TWO_FACTOR_FAILED,
                    self.user.user_id,
                    success=False,
                    details={"method": "totp", "reason": "invalid_token"},
                )
                QMessageBox.warning(
                    self, _("Ошибка"), _("Неверный код. Проверьте время на устройстве\n" "и попробуйте снова.")
                )
        except Exception as e:
            self.logger.error(f"Error verifying TOTP token: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Ошибка при проверке кода"))

    def _verify_backup_code(self, code: str):
        """Verify backup code"""
        # Format: XXXX-XXXX-XXXX (12 hex characters with dashes)
        code = code.upper().replace("-", "")

        if len(code) != 12:
            QMessageBox.warning(self, _("Ошибка"), _("Резервный код должен содержать 12 символов"))
            return

        try:
            # Get backup codes from database
            if not self.storage:
                raise ValueError("Storage not provided")

            totp_data = self.storage.get_two_factor_data(self.user.user_id)
            if not totp_data or not totp_data.get("backup_codes"):
                self.logger.error("Backup codes not found in database")
                QMessageBox.critical(self, _("Ошибка"), _("Резервные коды не найдены"))
                return

            # Deserialize backup codes
            hashed_codes = self.totp.deserialize_backup_codes(totp_data["backup_codes"])

            # Format code with dashes for verification
            formatted_code = f"{code[:4]}-{code[4:8]}-{code[8:]}"

            # Verify backup code (returns valid, remaining_codes)
            valid, remaining_codes = self.totp.verify_backup_code(formatted_code, hashed_codes)

            if valid:
                # Update database with remaining codes
                serialized_codes = self.totp.serialize_backup_codes(remaining_codes)
                self.storage.update_backup_codes(self.user.user_id, serialized_codes)

                self.logger.info(f"Backup code verified for user: {self.user.username}")
                self.audit.log_event(
                    AuditEventType.BACKUP_CODE_USED,
                    self.user.user_id,
                    success=True,
                    details={"remaining_codes": len(remaining_codes)},
                )

                # Warn if running low on backup codes
                if len(remaining_codes) <= 3:
                    QMessageBox.warning(
                        self,
                        _("Внимание"),
                        _(f"Осталось {len(remaining_codes)} резервных кодов.\n" f"Рекомендуется создать новые коды."),
                    )

                self.accept()
            else:
                self.logger.warning(f"Invalid backup code for user: {self.user.username}")
                self.audit.log_event(
                    AuditEventType.TWO_FACTOR_FAILED,
                    self.user.user_id,
                    success=False,
                    details={"method": "backup_code", "reason": "invalid_code"},
                )
                QMessageBox.warning(self, _("Ошибка"), _("Неверный резервный код или код уже использован"))
        except Exception as e:
            self.logger.error(f"Error verifying backup code: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Ошибка при проверке резервного кода"))

    def closeEvent(self, event):
        """Handle dialog close"""
        self.timer.stop()
        super().closeEvent(event)

    # Window dragging
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "drag_position"):
            self.move(event.globalPos() - self.drag_position)
            event.accept()
