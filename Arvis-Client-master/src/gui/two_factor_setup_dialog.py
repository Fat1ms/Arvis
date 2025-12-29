"""
Two-Factor Authentication Setup Dialog
Диалог настройки двухфакторной аутентификации

Phase 2 Day 5: 2FA Implementation
"""

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from i18n import _
from utils.logger import ModuleLogger
from utils.security import get_totp_manager


class TwoFactorSetupDialog(QDialog):
    """Dialog for setting up 2FA with QR code and backup codes"""

    def __init__(self, parent=None, username: str = "user"):
        super().__init__(parent)
        self.logger = ModuleLogger("TwoFactorSetupDialog")
        self.username = username
        self.totp = get_totp_manager()

        # Generate TOTP secret and backup codes
        self.secret = self.totp.generate_secret()
        self.backup_codes = self.totp.generate_backup_codes()

        self.logger.info(f"2FA setup initiated for user: {username}")

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(_("Настройка двухфакторной аутентификации"))
        self.setFixedSize(600, 750)
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
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Instructions
        instructions = QLabel(_("Шаг 1: Отсканируйте QR-код в приложении аутентификатора"))
        instructions.setStyleSheet(
            """
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: rgba(74, 158, 255, 0.2);
                border-radius: 5px;
            }
        """
        )
        instructions.setWordWrap(True)
        content_layout.addWidget(instructions)

        # QR Code and recommendations
        qr_layout = QHBoxLayout()

        # QR Code
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(250, 250)
        self.qr_label.setStyleSheet(
            """
            QLabel {
                background-color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                padding: 10px;
            }
        """
        )
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._generate_qr_code()
        qr_layout.addWidget(self.qr_label)

        # Recommendations
        recommendations = QLabel(
            _(
                "Рекомендуемые приложения:\n\n"
                "• Google Authenticator\n"
                "• Microsoft Authenticator\n"
                "• Authy\n"
                "• 1Password\n\n"
                "Установите одно из приложений\n"
                "и отсканируйте QR-код"
            )
        )
        recommendations.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                padding: 10px;
            }
        """
        )
        recommendations.setWordWrap(True)
        qr_layout.addWidget(recommendations)

        content_layout.addLayout(qr_layout)

        # Manual secret entry
        secret_label = QLabel(_("Или введите секрет вручную:"))
        secret_label.setStyleSheet("color: white; font-size: 12px;")
        content_layout.addWidget(secret_label)

        self.secret_input = QLineEdit(self.secret)
        self.secret_input.setReadOnly(True)
        self.secret_input.setStyleSheet(
            """
            QLineEdit {
                background-color: rgba(60, 60, 60, 1.0);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """
        )
        content_layout.addWidget(self.secret_input)

        # Copy secret button
        copy_secret_btn = QPushButton(_("📋 Копировать секрет"))
        copy_secret_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(74, 158, 255, 0.8);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(74, 158, 255, 1.0);
            }
        """
        )
        copy_secret_btn.clicked.connect(self._copy_secret)
        content_layout.addWidget(copy_secret_btn)

        # Verification step
        verify_label = QLabel(_("Шаг 2: Введите 6-значный код из приложения для проверки"))
        verify_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: rgba(74, 158, 255, 0.2);
                border-radius: 5px;
                margin-top: 10px;
            }
        """
        )
        verify_label.setWordWrap(True)
        content_layout.addWidget(verify_label)

        # Token input
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText(_("Введите 6-значный код"))
        self.token_input.setMaxLength(6)
        self.token_input.setStyleSheet(
            """
            QLineEdit {
                background-color: rgba(60, 60, 60, 1.0);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
            }
            QLineEdit:focus {
                border: 2px solid rgba(74, 158, 255, 1.0);
            }
        """
        )
        self.token_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.token_input)

        # Backup codes section
        backup_label = QLabel(_("⚠️ Резервные коды восстановления (сохраните в безопасном месте!)"))
        backup_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 154, 74, 1.0);
                font-size: 13px;
                font-weight: bold;
                padding: 10px;
                background-color: rgba(255, 154, 74, 0.1);
                border-radius: 5px;
                margin-top: 10px;
            }
        """
        )
        backup_label.setWordWrap(True)
        content_layout.addWidget(backup_label)

        # Backup codes display
        self.backup_codes_text = QTextEdit()
        self.backup_codes_text.setReadOnly(True)
        self.backup_codes_text.setFixedHeight(120)
        self._format_backup_codes()
        self.backup_codes_text.setStyleSheet(
            """
            QTextEdit {
                background-color: rgba(60, 60, 60, 1.0);
                color: rgba(255, 154, 74, 1.0);
                border: 1px solid rgba(255, 154, 74, 0.5);
                border-radius: 5px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """
        )
        content_layout.addWidget(self.backup_codes_text)

        # Backup codes buttons
        backup_btn_layout = QHBoxLayout()

        copy_codes_btn = QPushButton(_("📋 Копировать коды"))
        copy_codes_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 154, 74, 0.8);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 154, 74, 1.0);
            }
        """
        )
        copy_codes_btn.clicked.connect(self._copy_backup_codes)
        backup_btn_layout.addWidget(copy_codes_btn)

        save_codes_btn = QPushButton(_("💾 Сохранить в файл"))
        save_codes_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 154, 74, 0.8);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 154, 74, 1.0);
            }
        """
        )
        save_codes_btn.clicked.connect(self._save_backup_codes_to_file)
        backup_btn_layout.addWidget(save_codes_btn)

        content_layout.addLayout(backup_btn_layout)

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

        self.enable_btn = QPushButton(_("✓ Включить 2FA"))
        self.enable_btn.setFixedHeight(35)
        self.enable_btn.setStyleSheet(
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
        self.enable_btn.clicked.connect(self._verify_and_enable)
        button_layout.addWidget(self.enable_btn)

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

        title_label = QLabel(_("🔐 Настройка двухфакторной аутентификации"))
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

    def _generate_qr_code(self):
        """Generate and display QR code"""
        try:
            uri = self.totp.get_provisioning_uri(self.secret, self.username)
            qr_bytes = self.totp.generate_qr_code(uri)

            pixmap = QPixmap()
            pixmap.loadFromData(qr_bytes)

            # Scale to fit
            scaled_pixmap = pixmap.scaled(230, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            self.qr_label.setPixmap(scaled_pixmap)
            self.logger.debug("QR code generated and displayed")
        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
            self.qr_label.setText(_("❌ Ошибка генерации QR-кода"))

    def _format_backup_codes(self):
        """Format backup codes for display"""
        # Display in 2 columns
        lines = []
        for i in range(0, len(self.backup_codes), 2):
            left = f"{i+1:2d}. {self.backup_codes[i]}"
            if i + 1 < len(self.backup_codes):
                right = f"{i+2:2d}. {self.backup_codes[i+1]}"
                lines.append(f"{left:25s}  {right}")
            else:
                lines.append(left)

        self.backup_codes_text.setPlainText("\n".join(lines))

    def _copy_secret(self):
        """Copy TOTP secret to clipboard"""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self.secret)

        self.logger.info("TOTP secret copied to clipboard")
        QMessageBox.information(self, _("Скопировано"), _("Секрет скопирован в буфер обмена"))

    def _copy_backup_codes(self):
        """Copy backup codes to clipboard"""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(self.backup_codes))

        self.logger.info("Backup codes copied to clipboard")
        QMessageBox.information(self, _("Скопировано"), _("Резервные коды скопированы в буфер обмена"))

    def _save_backup_codes_to_file(self):
        """Save backup codes to text file"""
        from datetime import datetime

        from PyQt6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            _("Сохранить резервные коды"),
            f"arvis_backup_codes_{self.username}_{datetime.now().strftime('%Y%m%d')}.txt",
            _("Text Files (*.txt)"),
        )

        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"Arvis - Резервные коды двухфакторной аутентификации\n")
                    f.write(f"Пользователь: {self.username}\n")
                    f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"\n{'='*50}\n\n")
                    f.write("⚠️ ВАЖНО: Храните эти коды в безопасном месте!\n")
                    f.write("Каждый код можно использовать только один раз.\n\n")
                    for i, code in enumerate(self.backup_codes, 1):
                        f.write(f"{i:2d}. {code}\n")
                    f.write(f"\n{'='*50}\n")

                self.logger.info(f"Backup codes saved to file: {filename}")
                QMessageBox.information(self, _("Сохранено"), _("Резервные коды сохранены в файл"))
            except Exception as e:
                self.logger.error(f"Failed to save backup codes: {e}")
                QMessageBox.warning(self, _("Ошибка"), _("Не удалось сохранить файл"))

    def _verify_and_enable(self):
        """Verify token and enable 2FA"""
        token = self.token_input.text().strip()

        if not token:
            QMessageBox.warning(self, _("Ошибка"), _("Введите 6-значный код из приложения"))
            return

        if len(token) != 6 or not token.isdigit():
            QMessageBox.warning(self, _("Ошибка"), _("Код должен содержать 6 цифр"))
            return

        # Verify token
        if self.totp.verify_token(self.secret, token):
            self.logger.info("2FA token verified successfully")
            QMessageBox.information(
                self,
                _("Успешно"),
                _("Двухфакторная аутентификация настроена!\n\n" "Обязательно сохраните резервные коды."),
            )
            self.accept()
        else:
            self.logger.warning("2FA token verification failed")
            QMessageBox.warning(
                self, _("Ошибка"), _("Неверный код. Проверьте время на устройстве\n" "и попробуйте снова.")
            )

    def get_secret(self) -> str:
        """Get generated TOTP secret"""
        return self.secret

    def get_backup_codes(self) -> List[str]:
        """Get generated backup codes"""
        return self.backup_codes

    def get_encrypted_secret(self) -> str:
        """Get encrypted TOTP secret for storage"""
        return self.totp.encrypt_secret(self.secret)

    def get_hashed_backup_codes(self) -> List[str]:
        """Get hashed backup codes for storage"""
        return self.totp.hash_backup_codes(self.backup_codes)

    # Window dragging
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if event.buttons() == Qt.LeftButton and hasattr(self, "drag_position"):
            self.move(event.globalPos() - self.drag_position)
            event.accept()
