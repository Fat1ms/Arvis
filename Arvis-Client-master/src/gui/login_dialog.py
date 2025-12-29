"""
Login Dialog for Arvis Authentication System
Диалог входа в систему с поддержкой создания аккаунтов
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import _
from utils.logger import ModuleLogger
from utils.security import Role, UserStorage, get_auth_manager
from utils.security.hybrid_auth import HybridAuthManager
from config.config import Config


class LoginDialog(QDialog):
    """Dialog for user authentication"""

    # Signals
    login_successful = pyqtSignal(str, str)  # user_id, username

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = ModuleLogger("LoginDialog")
        # Используем HybridAuthManager для поддержки удалённого сервера
        config = Config()
        self.auth_manager = HybridAuthManager(config)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(_("Вход в систему"))
        self.setFixedSize(400, 350)
        self.setModal(True)

        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(15)

        # Logo/Icon
        logo_label = QLabel("🔐")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet(
            """
            QLabel {
                color: #4a9eff;
                font-size: 48px;
                background: transparent;
            }
        """
        )
        content_layout.addWidget(logo_label)

        # Title
        title_label = QLabel(_("Вход в Arvis"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                background: transparent;
                margin-bottom: 10px;
            }
        """
        )
        content_layout.addWidget(title_label)

        # Username field
        username_layout = QVBoxLayout()
        username_layout.setSpacing(5)
        username_label = QLabel(_("Имя пользователя:"))
        username_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(_("Введите имя пользователя"))
        self.username_input.returnPressed.connect(self.handle_login)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        content_layout.addLayout(username_layout)

        # Password field
        password_layout = QVBoxLayout()
        password_layout.setSpacing(5)
        password_label = QLabel(_("Пароль:"))
        password_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(_("Введите пароль"))
        self.password_input.returnPressed.connect(self.handle_login)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        content_layout.addLayout(password_layout)

        # Remember me checkbox
        self.remember_checkbox = QCheckBox(_("Запомнить меня"))
        self.remember_checkbox.setChecked(True)
        self.remember_checkbox.setStyleSheet(
            """
            QCheckBox {
                color: rgba(255, 255, 255, 0.7);
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 3px;
                background: rgba(60, 60, 60, 0.5);
            }
            QCheckBox::indicator:checked {
                background: #4a9eff;
                border-color: #4a9eff;
            }
        """
        )
        content_layout.addWidget(self.remember_checkbox)

        content_layout.addSpacing(10)

        # Login button
        self.login_button = QPushButton(_("Войти"))
        self.login_button.setFixedHeight(40)
        self.login_button.clicked.connect(self.handle_login)
        content_layout.addWidget(self.login_button)

        # Create account button
        self.create_account_button = QPushButton(_("Создать аккаунт"))
        self.create_account_button.setFixedHeight(35)
        self.create_account_button.clicked.connect(self.show_create_account)
        content_layout.addWidget(self.create_account_button)

        # Guest mode button
        self.guest_button = QPushButton(_("Войти как гость"))
        self.guest_button.setFixedHeight(30)
        self.guest_button.clicked.connect(self.handle_guest_login)
        content_layout.addWidget(self.guest_button)

        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        self.setLayout(main_layout)

        # Apply styles
        self.apply_styles()

    def _create_title_bar(self) -> QWidget:
        """Create custom title bar"""
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet(
            """
            QWidget {
                background-color: rgb(43, 43, 43);
                border-bottom: 1px solid rgb(60, 60, 60);
            }
        """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)

        # Title
        title_label = QLabel(_("Аутентификация"))
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
            }
        """
        )

        layout.addWidget(title_label)
        layout.addStretch()

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgb(43, 43, 43);
                color: rgb(180, 180, 180);
                border: none;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgb(232, 17, 35);
                color: white;
            }
            QPushButton:pressed {
                background-color: rgb(180, 30, 30);
            }
        """
        )
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

        title_bar.setLayout(layout)

        # Make draggable
        title_bar.mousePressEvent = self._title_bar_mouse_press
        title_bar.mouseMoveEvent = self._title_bar_mouse_move

        return title_bar

    def _title_bar_mouse_press(self, event):
        """Handle title bar mouse press"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _title_bar_mouse_move(self, event):
        """Handle title bar mouse move"""
        if event.buttons() == Qt.LeftButton and hasattr(self, "drag_pos"):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def apply_styles(self):
        """Apply dialog styles"""
        self.setStyleSheet(
            """
            QDialog {
                background-color: rgb(43, 43, 43);
            }

            QLineEdit {
                background-color: rgba(60, 60, 60, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid #4a9eff;
                background-color: rgba(60, 60, 60, 0.8);
            }

            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #3a8eff;
            }

            QPushButton:pressed {
                background-color: #2a7eff;
            }

            QPushButton#create_account_button {
                background-color: rgba(74, 158, 255, 0.3);
            }

            QPushButton#create_account_button:hover {
                background-color: rgba(74, 158, 255, 0.5);
            }

            QPushButton#guest_button {
                background-color: transparent;
                color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            QPushButton#guest_button:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.8);
            }
        """
        )

        # Set object names for specific styling
        self.create_account_button.setObjectName("create_account_button")
        self.guest_button.setObjectName("guest_button")

    def handle_login(self):
        """Handle login button click"""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, _("Ошибка"), _("Пожалуйста, заполните все поля"))
            return

        try:
            # Authenticate using HybridAuthManager (returns tuple)
            success, error, user = self.auth_manager.authenticate(username, password)

            if success and user:
                self.logger.info(f"User authenticated: {username}")

                # Check if 2FA is enabled (Phase 2 Day 5)
                if user.require_2fa:
                    self.logger.debug(f"2FA required for user: {username}")

                    # Import here to avoid circular imports
                    from src.gui.two_factor_verification_dialog import TwoFactorVerificationDialog

                    # Show 2FA verification dialog
                    storage = UserStorage()
                    verify_dialog = TwoFactorVerificationDialog(self, user, storage)

                    if verify_dialog.exec() == QDialog.DialogCode.Accepted:
                        # 2FA verified, proceed with login
                        self.logger.info(f"2FA verification successful for user: {username}")

                        # Session managed by HybridAuthManager internally
                        
                        # Emit success signal
                        self.login_successful.emit(user.user_id, username)
                        self.accept()
                    else:
                        # 2FA verification failed or cancelled
                        self.logger.warning(f"2FA verification failed for user: {username}")
                        self.password_input.clear()
                        self.password_input.setFocus()
                else:
                    # No 2FA, direct login (existing flow)
                    # Session managed by HybridAuthManager internally
                    
                    # Emit success signal
                    self.login_successful.emit(user.user_id, username)
                    self.accept()

            else:
                error_msg = error if error else _("Неверное имя пользователя или пароль")
                QMessageBox.warning(self, _("Ошибка входа"), error_msg)
                self.password_input.clear()
                self.password_input.setFocus()

        except Exception as e:
            self.logger.error(f"Login error: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Не удалось выполнить вход:\n{error}").format(error=e))

    def handle_guest_login(self):
        """Handle guest mode login"""
        try:
            self.logger.info("Guest mode login")
            # Emit guest signal (no user_id)
            self.login_successful.emit("", "Guest")
            self.accept()

        except Exception as e:
            self.logger.error(f"Guest login error: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Не удалось войти в гостевом режиме:\n{error}").format(error=e))

    def show_create_account(self):
        """Show create account dialog"""
        try:
            dialog = CreateAccountDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Account created, try to login
                user_id, username = dialog.get_credentials()
                if user_id:
                    self.login_successful.emit(user_id, username)
                    self.accept()

        except Exception as e:
            self.logger.error(f"Create account error: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Не удалось создать аккаунт:\n{error}").format(error=e))


class CreateAccountDialog(QDialog):
    """Dialog for creating new user account"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = ModuleLogger("CreateAccountDialog")
        # Используем HybridAuthManager для поддержки удалённого сервера
        config = Config()
        self.auth_manager = HybridAuthManager(config)
        self.created_user_id = None
        self.created_username = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(_("Создание аккаунта"))
        self.setFixedSize(500, 550)
        self.setModal(True)

        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Content
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(15)

        # Title
        title_label = QLabel(_("Создать новый аккаунт"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
            }
        """
        )
        content_layout.addWidget(title_label)

        # Username field
        username_layout = QVBoxLayout()
        username_layout.setSpacing(5)
        username_label = QLabel(_("Имя пользователя:"))
        username_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(_("Минимум 3 символа"))
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        content_layout.addLayout(username_layout)

        # Password field
        password_layout = QVBoxLayout()
        password_layout.setSpacing(5)
        password_label = QLabel(_("Пароль:"))
        password_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(_("Минимум 8 символов"))
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        content_layout.addLayout(password_layout)

        # Confirm password field
        confirm_layout = QVBoxLayout()
        confirm_layout.setSpacing(5)
        confirm_label = QLabel(_("Подтвердите пароль:"))
        confirm_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText(_("Повторите пароль"))
        confirm_layout.addWidget(confirm_label)
        confirm_layout.addWidget(self.confirm_input)
        content_layout.addLayout(confirm_layout)

        # Информация о роли (автоматически User)
        role_info = QLabel(
            _(
                "ℹ️ Новые аккаунты создаются с ролью 'Пользователь'.\nДоступ к административным функциям выдается администратором."
            )
        )
        role_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        role_info.setWordWrap(True)
        role_info.setStyleSheet(
            "color: rgba(255, 255, 255, 0.6); "
            "font-size: 11px; "
            "background: rgba(74, 158, 255, 0.1); "
            "padding: 10px; "
            "border-radius: 5px; "
            "border: 1px solid rgba(74, 158, 255, 0.3);"
        )
        content_layout.addWidget(role_info)

        # Password strength indicator
        self.strength_label = QLabel("")
        self.strength_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.strength_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px; background: transparent;")
        content_layout.addWidget(self.strength_label)

        # Connect password field to strength checker
        self.password_input.textChanged.connect(self.check_password_strength)

        content_layout.addSpacing(10)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.cancel_button = QPushButton(_("Отмена"))
        self.cancel_button.clicked.connect(self.reject)

        self.create_button = QPushButton(_("Создать аккаунт"))
        self.create_button.clicked.connect(self.handle_create_account)

        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.create_button)
        content_layout.addLayout(buttons_layout)

        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        self.setLayout(main_layout)

        # Apply styles
        self.apply_styles()

    def _create_title_bar(self) -> QWidget:
        """Create custom title bar"""
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet(
            """
            QWidget {
                background-color: rgb(43, 43, 43);
                border-bottom: 1px solid rgb(60, 60, 60);
            }
        """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)

        title_label = QLabel(_("Регистрация"))
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
            }
        """
        )

        layout.addWidget(title_label)
        layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgb(43, 43, 43);
                color: rgb(180, 180, 180);
                border: none;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgb(232, 17, 35);
                color: white;
            }
            QPushButton:pressed {
                background-color: rgb(180, 30, 30);
            }
        """
        )
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

        title_bar.setLayout(layout)

        # Make draggable
        title_bar.mousePressEvent = self._title_bar_mouse_press
        title_bar.mouseMoveEvent = self._title_bar_mouse_move

        return title_bar

    def _title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _title_bar_mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "drag_pos"):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def apply_styles(self):
        """Apply dialog styles"""
        self.setStyleSheet(
            """
            QDialog {
                background-color: rgb(43, 43, 43);
            }

            QLineEdit, QComboBox {
                background-color: rgba(60, 60, 60, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #4a9eff;
                background-color: rgba(60, 60, 60, 0.8);
            }

            QComboBox::drop-down {
                border: none;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
            }

            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }

            QPushButton:hover {
                background-color: #3a8eff;
            }

            QPushButton:pressed {
                background-color: #2a7eff;
            }

            QPushButton#cancel_button {
                background-color: rgba(255, 255, 255, 0.1);
            }

            QPushButton#cancel_button:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """
        )

        self.cancel_button.setObjectName("cancel_button")

    def check_password_strength(self):
        """Check password strength and update indicator"""
        password = self.password_input.text()

        if len(password) == 0:
            self.strength_label.setText("")
            return

        strength = 0
        if len(password) >= 8:
            strength += 1
        if any(c.isupper() for c in password):
            strength += 1
        if any(c.islower() for c in password):
            strength += 1
        if any(c.isdigit() for c in password):
            strength += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            strength += 1

        if strength <= 2:
            self.strength_label.setText(_("⚠️ Слабый пароль"))
            self.strength_label.setStyleSheet("color: #ff4a4a; font-size: 11px; background: transparent;")
        elif strength <= 3:
            self.strength_label.setText(_("🔶 Средний пароль"))
            self.strength_label.setStyleSheet("color: #ff9a4a; font-size: 11px; background: transparent;")
        else:
            self.strength_label.setText(_("✅ Надёжный пароль"))
            self.strength_label.setStyleSheet("color: #4aff4a; font-size: 11px; background: transparent;")

    def handle_create_account(self):
        """Handle account creation"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        # Validation
        if not username or not password or not confirm:
            QMessageBox.warning(self, _("Ошибка"), _("Пожалуйста, заполните все поля"))
            return

        if len(username) < 3:
            QMessageBox.warning(self, _("Ошибка"), _("Имя пользователя должно содержать минимум 3 символа"))
            return

        if len(password) < 8:
            QMessageBox.warning(self, _("Ошибка"), _("Пароль должен содержать минимум 8 символов"))
            return

        if password != confirm:
            QMessageBox.warning(self, _("Ошибка"), _("Пароли не совпадают"))
            return

        try:
            # Попробуем создать пользователя через Client API (на сервере)
            from utils.security.client_api import ArvisClientAPI
            from config.config import Config
            
            config = Config()
            use_remote = config.get("security.auth.use_remote_server", False)
            server_url = config.get("security.auth.server_url", "")
            
            user_created_on_server = False
            
            if use_remote and server_url:
                try:
                    self.logger.info(f"Attempting to register user on server: {username}")
                    client = ArvisClientAPI(str(server_url), timeout=10)
                    
                    # Генерируем email из username если нужно
                    email = f"{username}@arvis.local"
                    
                    result = client.register(username, email, password, full_name=username)
                    
                    if result.get("success"):
                        self.logger.info(f"User registered on server: {username}")
                        user_created_on_server = True
                        
                        # Пробуем сразу войти
                        login_result = client.login(username, password)
                        if login_result.get("success"):
                            user_data = login_result.get("user", {})
                            self.created_user_id = user_data.get("id", user_data.get("user_id"))
                            self.created_username = username
                        
                        QMessageBox.information(
                            self,
                            _("Успех"),
                            _("Аккаунт успешно создан на сервере!\nТеперь вы можете войти."),
                        )
                        self.accept()
                        return
                    else:
                        error = result.get("error", "Unknown error")
                        self.logger.warning(f"Server registration failed: {error}")
                        # Продолжим локальное создание
                except Exception as e:
                    self.logger.warning(f"Server registration error: {e}, falling back to local")
                    # Продолжим локальное создание
            
            # Если сервер не доступен или не настроен - создаём локально
            if not user_created_on_server:
                self.logger.info(f"Creating user locally: {username}")
                
                # Create user locally через локальный auth manager
                user = self.auth_manager.local_auth.create_user(username, password, Role.USER)

                if user:
                    self.logger.info(f"User created locally: {username} with role {user.role.name}")
                    self.created_user_id = user.user_id
                    self.created_username = username

                    QMessageBox.information(
                        self,
                        _("Успех"),
                        _("Аккаунт успешно создан локально!\nТеперь вы можете войти."),
                    )
                    self.accept()

                else:
                    QMessageBox.warning(self, _("Ошибка"), _("Не удалось создать аккаунт"))

        except ValueError as e:
            # User already exists
            QMessageBox.warning(self, _("Ошибка"), str(e))

        except Exception as e:
            self.logger.error(f"Account creation error: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Не удалось создать аккаунт:\n{error}").format(error=e))

    def get_credentials(self):
        """Get created user credentials"""
        return self.created_user_id, self.created_username
