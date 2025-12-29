"""
Setup 2FA Dialog
Диалог настройки двухфакторной аутентификации
"""

import io
import logging

import pyotp
import qrcode
import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.config import Config

logger = logging.getLogger(__name__)


class Setup2FADialog(QDialog):
    """Диалог для настройки двухфакторной аутентификации"""

    def __init__(self, user_id: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.config = Config()
        self.secret = None
        self.qr_uri = None
        self.init_ui()
        self.load_2fa_setup()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Настройка 2FA")
        self.setFixedSize(500, 600)
        self.setModal(True)

        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)  # type: ignore[attr-defined]

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        self.create_title_bar()
        main_layout.addWidget(self.title_bar)

        # Content
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Info label
        info_label = QLabel("Двухфакторная аутентификация добавляет дополнительный уровень безопасности к вашему аккаунту.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: white; font-size: 12px;")
        content_layout.addWidget(info_label)

        # Step 1
        step1_label = QLabel("Шаг 1: Установите приложение-аутентификатор")
        step1_label.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")
        content_layout.addWidget(step1_label)

        apps_label = QLabel("• Google Authenticator\n• Microsoft Authenticator\n• Authy\n• или другое TOTP-приложение")
        apps_label.setStyleSheet("color: #aaa; font-size: 11px;")
        content_layout.addWidget(apps_label)

        # Step 2
        step2_label = QLabel("Шаг 2: Отсканируйте QR-код")
        step2_label.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")
        content_layout.addWidget(step2_label)

        # QR Code
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore[attr-defined]
        self.qr_label.setMinimumSize(250, 250)
        self.qr_label.setStyleSheet("background-color: white; border-radius: 10px; padding: 10px;")
        content_layout.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignCenter)  # type: ignore[arg-type]

        # Secret key (manual entry)
        secret_layout = QHBoxLayout()
        secret_label = QLabel("Или введите код вручную:")
        secret_label.setStyleSheet("color: #aaa; font-size: 10px;")
        secret_layout.addWidget(secret_label)

        self.secret_edit = QLineEdit()
        self.secret_edit.setReadOnly(True)
        self.secret_edit.setStyleSheet(
            "background-color: rgb(50, 50, 50); color: white; font-family: monospace; padding: 5px;"
        )
        secret_layout.addWidget(self.secret_edit)

        copy_button = QPushButton("📋")
        copy_button.setFixedWidth(40)
        copy_button.setToolTip("Копировать секретный ключ")
        copy_button.clicked.connect(self.copy_secret)
        secret_layout.addWidget(copy_button)

        content_layout.addLayout(secret_layout)

        # Step 3
        step3_label = QLabel("Шаг 3: Введите код из приложения")
        step3_label.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")
        content_layout.addWidget(step3_label)

        verify_layout = QHBoxLayout()
        verify_label = QLabel("Код подтверждения:")
        verify_label.setFixedWidth(140)
        verify_layout.addWidget(verify_label)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Введите 6-значный код")
        self.code_edit.setMaxLength(6)
        verify_layout.addWidget(self.code_edit)

        content_layout.addLayout(verify_layout)

        content_layout.addStretch()

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.verify_button = QPushButton("Подтвердить и включить 2FA")
        self.verify_button.clicked.connect(self.verify_and_enable)
        buttons_layout.addWidget(self.verify_button)

        self.disable_button = QPushButton("Отключить 2FA")
        self.disable_button.clicked.connect(self.disable_2fa)
        self.disable_button.setVisible(False)
        buttons_layout.addWidget(self.disable_button)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        content_layout.addLayout(buttons_layout)

        content.setLayout(content_layout)
        main_layout.addWidget(content)

        self.setLayout(main_layout)

        # Styling
        self.setStyleSheet(
            """
            QDialog {
                background-color: rgb(43, 43, 43);
                color: white;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: rgb(50, 50, 50);
                border: 1px solid rgb(70, 70, 70);
                border-radius: 5px;
                padding: 8px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid rgb(0, 120, 215);
            }
            QPushButton {
                background-color: rgb(60, 60, 60);
                color: white;
                border: 1px solid rgb(80, 80, 80);
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: rgb(70, 70, 70);
            }
            QPushButton:pressed {
                background-color: rgb(50, 50, 50);
            }
        """
        )

    def create_title_bar(self):
        """Создание кастомного заголовка"""
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet(
            """
            QWidget {
                background-color: rgb(43, 43, 43);
                border-bottom: 1px solid rgb(60, 60, 60);
            }
        """
        )

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 0, 0, 0)

        title_label = QLabel("Настройка 2FA")
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px; border: none;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgb(43, 43, 43);
                color: rgb(80, 80, 80);
                border: none;
                font-size: 16px;
                font-weight: bold;
                width: 30px;
                height: 30px;
                min-width: 30px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgb(200, 50, 50);
                color: white;
            }
        """
        )
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)

        self.title_bar.setLayout(title_layout)

        # Draggable
        self.title_bar.mousePressEvent = self.title_bar_mouse_press  # type: ignore[assignment]
        self.title_bar.mouseMoveEvent = self.title_bar_mouse_move  # type: ignore[assignment]

    def title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "drag_pos"):  # type: ignore[attr-defined]
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def load_2fa_setup(self):
        """Загрузка настроек 2FA с сервера"""
        try:
            auth_server = self.config.get("security.auth.server_url", "http://192.168.0.107:8000")
            url = f"{auth_server}/api/users/2fa/setup"

            # Получаем токен
            access_token = None
            if self.parent():
                access_token = getattr(self.parent(), "access_token", None)

            if not access_token:
                QMessageBox.warning(self, "Ошибка", "Необходима авторизация")
                self.reject()
                return

            headers = {"Authorization": f"Bearer {access_token}"}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Если 2FA уже включена
                if data.get("enabled", False):
                    self.show_2fa_enabled()
                    return

                # Получаем секретный ключ и URI для QR-кода
                self.secret = data.get("secret")
                self.qr_uri = data.get("qr_uri")

                if self.secret:
                    self.secret_edit.setText(self.secret)
                    self.generate_qr_code()

            else:
                error_detail = response.json().get("detail", "Неизвестная ошибка")
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить настройки 2FA:\n{error_detail}")
                self.reject()

        except requests.RequestException as e:
            logger.error(f"Ошибка загрузки 2FA: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу:\n{str(e)}")
            self.reject()
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{str(e)}")
            self.reject()

    def generate_qr_code(self):
        """Генерация QR-кода"""
        try:
            if not self.qr_uri:
                return

            # Генерируем QR-код
            import qrcode.constants as qr_const
            
            qr = qrcode.QRCode(version=1, error_correction=qr_const.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(self.qr_uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Конвертируем в QPixmap
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())

            # Масштабируем
            scaled_pixmap = pixmap.scaled(230, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore[attr-defined]
            self.qr_label.setPixmap(scaled_pixmap)

        except Exception as e:
            logger.error(f"Ошибка генерации QR-кода: {e}")

    def copy_secret(self):
        """Копирование секретного ключа в буфер обмена"""
        from PyQt6.QtWidgets import QApplication

        if self.secret:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(self.secret)
                QMessageBox.information(self, "Скопировано", "Секретный ключ скопирован в буфер обмена")

    def verify_and_enable(self):
        """Подтверждение и включение 2FA"""
        code = self.code_edit.text().strip()

        if len(code) != 6:
            QMessageBox.warning(self, "Ошибка", "Введите 6-значный код")
            return

        try:
            auth_server = self.config.get("security.auth.server_url", "http://192.168.0.107:8000")
            url = f"{auth_server}/api/users/2fa/enable"

            access_token = None
            if self.parent():
                access_token = getattr(self.parent(), "access_token", None)

            if not access_token:
                QMessageBox.warning(self, "Ошибка", "Необходима авторизация")
                return

            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            payload = {"totp_code": code}

            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                QMessageBox.information(
                    self, "Успех", "Двухфакторная аутентификация успешно включена!\n\nТеперь при входе потребуется код из приложения."
                )
                self.accept()
            elif response.status_code == 400:
                QMessageBox.warning(self, "Ошибка", "Неверный код подтверждения. Попробуйте ещё раз.")
            else:
                error_detail = response.json().get("detail", "Неизвестная ошибка")
                QMessageBox.warning(self, "Ошибка", f"Не удалось включить 2FA:\n{error_detail}")

        except requests.RequestException as e:
            logger.error(f"Ошибка включения 2FA: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу:\n{str(e)}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{str(e)}")

    def disable_2fa(self):
        """Отключение 2FA"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите отключить двухфакторную аутентификацию?\n\nЭто снизит безопасность вашего аккаунта.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            auth_server = self.config.get("security.auth.server_url", "http://192.168.0.107:8000")
            url = f"{auth_server}/api/users/2fa/disable"

            access_token = None
            if self.parent():
                access_token = getattr(self.parent(), "access_token", None)

            if not access_token:
                QMessageBox.warning(self, "Ошибка", "Необходима авторизация")
                return

            headers = {"Authorization": f"Bearer {access_token}"}

            response = requests.post(url, headers=headers, timeout=10)

            if response.status_code == 200:
                QMessageBox.information(self, "Успех", "Двухфакторная аутентификация отключена")
                self.accept()
            else:
                error_detail = response.json().get("detail", "Неизвестная ошибка")
                QMessageBox.warning(self, "Ошибка", f"Не удалось отключить 2FA:\n{error_detail}")

        except requests.RequestException as e:
            logger.error(f"Ошибка отключения 2FA: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу:\n{str(e)}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{str(e)}")

    def show_2fa_enabled(self):
        """Показать, что 2FA уже включена"""
        self.qr_label.hide()
        self.secret_edit.hide()
        self.code_edit.hide()
        self.verify_button.hide()

        self.disable_button.setVisible(True)

        enabled_label = QLabel(
            "✓ Двухфакторная аутентификация уже включена\n\n"
            "Вы можете отключить её, если больше не хотите использовать дополнительную защиту."
        )
        enabled_label.setStyleSheet("color: #00ff00; font-size: 14px; padding: 20px;")
        enabled_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore[attr-defined]
        enabled_label.setWordWrap(True)

        # Добавляем label в layout
        content_layout = self.findChild(QWidget, "").layout()
        if content_layout:
            content_layout.insertWidget(2, enabled_label)
