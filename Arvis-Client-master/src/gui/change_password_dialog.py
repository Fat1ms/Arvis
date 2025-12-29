"""
Change Password Dialog
Диалог смены пароля пользователя
"""

import hashlib
import logging

import requests
from PyQt6.QtCore import Qt
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
from utils.security.remote_auth_client import RemoteAuthClient

logger = logging.getLogger(__name__)


class ChangePasswordDialog(QDialog):
    """Диалог для смены пароля пользователя"""

    def __init__(self, user_id: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.config = Config()
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Смена пароля")
        self.setFixedSize(450, 300)
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
        info_label = QLabel("Введите текущий и новый пароль:")
        info_label.setStyleSheet("color: white; font-size: 12px;")
        content_layout.addWidget(info_label)

        # Current password
        current_layout = QHBoxLayout()
        current_label = QLabel("Текущий пароль:")
        current_label.setFixedWidth(140)
        current_layout.addWidget(current_label)

        self.current_password_edit = QLineEdit()
        self.current_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_edit.setPlaceholderText("Введите текущий пароль")
        current_layout.addWidget(self.current_password_edit)

        content_layout.addLayout(current_layout)

        # New password
        new_layout = QHBoxLayout()
        new_label = QLabel("Новый пароль:")
        new_label.setFixedWidth(140)
        new_layout.addWidget(new_label)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_edit.setPlaceholderText("Введите новый пароль")
        new_layout.addWidget(self.new_password_edit)

        content_layout.addLayout(new_layout)

        # Confirm password
        confirm_layout = QHBoxLayout()
        confirm_label = QLabel("Подтверждение:")
        confirm_label.setFixedWidth(140)
        confirm_layout.addWidget(confirm_label)

        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_edit.setPlaceholderText("Подтвердите новый пароль")
        confirm_layout.addWidget(self.confirm_password_edit)

        content_layout.addLayout(confirm_layout)

        # Password requirements
        requirements_label = QLabel(
            "Требования к паролю:\n" "• Минимум 8 символов\n" "• Содержит буквы и цифры\n" "• Хотя бы одна заглавная буква"
        )
        requirements_label.setStyleSheet("color: #aaa; font-size: 10px; margin-top: 10px;")
        content_layout.addWidget(requirements_label)

        content_layout.addStretch()

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.change_password)
        buttons_layout.addWidget(self.save_button)

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

        title_label = QLabel("Смена пароля")
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

    def validate_password(self, password: str) -> tuple[bool, str]:
        """
        Валидация пароля
        
        Returns:
            (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Пароль должен содержать минимум 8 символов"

        if not any(c.isupper() for c in password):
            return False, "Пароль должен содержать хотя бы одну заглавную букву"

        if not any(c.islower() for c in password):
            return False, "Пароль должен содержать хотя бы одну строчную букву"

        if not any(c.isdigit() for c in password):
            return False, "Пароль должен содержать хотя бы одну цифру"

        return True, ""

    def change_password(self):
        """Выполнение смены пароля"""
        current_password = self.current_password_edit.text()
        new_password = self.new_password_edit.text()
        confirm_password = self.confirm_password_edit.text()

        # Валидация
        if not current_password:
            QMessageBox.warning(self, "Ошибка", "Введите текущий пароль")
            return

        if not new_password:
            QMessageBox.warning(self, "Ошибка", "Введите новый пароль")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return

        # Валидация нового пароля
        is_valid, error_msg = self.validate_password(new_password)
        if not is_valid:
            QMessageBox.warning(self, "Ошибка", error_msg)
            return

        # Отправка запроса на сервер
        try:
            auth_server = self.config.get_auth_server_url()
            url = f"{auth_server}/api/users/change-password"

            # Получаем токен из конфига или родительского окна
            access_token = None
            if self.parent():
                access_token = getattr(self.parent(), "access_token", None)
            if not access_token:
                try:
                    access_token = RemoteAuthClient.get().access_token
                except Exception:
                    access_token = None

            if not access_token:
                QMessageBox.warning(self, "Ошибка", "Необходима авторизация")
                return

            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            payload = {"current_password": current_password, "new_password": new_password}

            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                QMessageBox.information(self, "Успех", "Пароль успешно изменён")
                self.accept()
            elif response.status_code == 401:
                QMessageBox.warning(self, "Ошибка", "Неверный текущий пароль")
            else:
                error_detail = response.json().get("detail", "Неизвестная ошибка")
                QMessageBox.warning(self, "Ошибка", f"Не удалось изменить пароль:\n{error_detail}")

        except requests.RequestException as e:
            logger.error(f"Ошибка смены пароля: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу:\n{str(e)}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{str(e)}")
