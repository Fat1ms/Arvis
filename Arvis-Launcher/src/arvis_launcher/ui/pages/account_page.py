"""
Account page - Login and user management
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QGroupBox,
    QStackedWidget,
    QMessageBox,
    QFrame,
)

from ...session import SessionManager, UserSession
from ...activation import ActivationManager
from ...styles import (
    COLORS,
    PAGE_TITLE_STYLE,
    PAGE_SUBTITLE_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    LINE_EDIT_STYLE,
    GROUP_BOX_STYLE,
)


from ..dialogs import ActivationStatusWidget


class AccountPage(QWidget):
    """Account management page"""
    
    def __init__(
        self,
        session_manager: SessionManager,
        activation_manager: ActivationManager = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.session_manager = session_manager
        self.activation_manager = activation_manager
        
        self._build_ui()
        self._connect_signals()
        self._update_view()
    
    def _build_ui(self):
        """Build the account page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # Header
        title = QLabel("Аккаунт")
        title.setStyleSheet(PAGE_TITLE_STYLE)
        layout.addWidget(title)
        
        subtitle = QLabel("Управление учётной записью и синхронизация")
        subtitle.setStyleSheet(PAGE_SUBTITLE_STYLE)
        layout.addWidget(subtitle)
        
        # Activation status widget (if activation manager provided)
        self.activation_widget = None
        if self.activation_manager:
            self.activation_widget = ActivationStatusWidget(self.activation_manager, self)
            self.activation_widget.deactivate_requested.connect(self._on_deactivate_requested)
            layout.addWidget(self.activation_widget)
        
        # Stacked widget for login/profile views (hidden - not used currently)
        self.stack = QStackedWidget()
        self.stack.setVisible(False)  # Hide login/profile stack
        
        # Login view
        self.login_widget = self._build_login_view()
        self.stack.addWidget(self.login_widget)
        
        # Profile view (when logged in)
        self.profile_widget = self._build_profile_view()
        self.stack.addWidget(self.profile_widget)
        
        # Guest profile view
        self.guest_widget = self._build_guest_view()
        self.stack.addWidget(self.guest_widget)
        
        layout.addWidget(self.stack)
        layout.addStretch()
    
    def _build_login_view(self) -> QWidget:
        """Build login form"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Login form group
        group = QGroupBox("Вход в аккаунт")
        group.setStyleSheet(GROUP_BOX_STYLE)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(20, 24, 20, 20)
        group_layout.setSpacing(16)
        
        # Server URL
        server_layout = QVBoxLayout()
        server_layout.setSpacing(6)
        
        server_label = QLabel("Сервер:")
        server_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        server_layout.addWidget(server_label)
        
        self.edit_server = QLineEdit()
        self.edit_server.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_server.setPlaceholderText("http://127.0.0.1:8000")
        self.edit_server.setText("http://127.0.0.1:8000")
        server_layout.addWidget(self.edit_server)
        
        group_layout.addLayout(server_layout)
        
        # Username
        user_layout = QVBoxLayout()
        user_layout.setSpacing(6)
        
        user_label = QLabel("Имя пользователя:")
        user_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        user_layout.addWidget(user_label)
        
        self.edit_username = QLineEdit()
        self.edit_username.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_username.setPlaceholderText("username")
        user_layout.addWidget(self.edit_username)
        
        group_layout.addLayout(user_layout)
        
        # Password
        pass_layout = QVBoxLayout()
        pass_layout.setSpacing(6)
        
        pass_label = QLabel("Пароль:")
        pass_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        pass_layout.addWidget(pass_label)
        
        self.edit_password = QLineEdit()
        self.edit_password.setStyleSheet(LINE_EDIT_STYLE)
        self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_password.setPlaceholderText("••••••••")
        pass_layout.addWidget(self.edit_password)
        
        group_layout.addLayout(pass_layout)
        
        # Error label
        self.login_error = QLabel()
        self.login_error.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
        self.login_error.hide()
        group_layout.addWidget(self.login_error)
        
        # Login button
        self.btn_login = QPushButton("🔐  Войти")
        self.btn_login.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.btn_login.setMinimumHeight(44)
        group_layout.addWidget(self.btn_login)
        
        layout.addWidget(group)
        
        # Guest mode section
        guest_group = QGroupBox("Гостевой режим")
        guest_group.setStyleSheet(GROUP_BOX_STYLE)
        guest_layout = QVBoxLayout(guest_group)
        guest_layout.setContentsMargins(20, 20, 20, 16)
        guest_layout.setSpacing(12)
        
        guest_info = QLabel(
            "⏱️ Гостевой режим позволяет использовать Arvis без регистрации.\n"
            "Сессия ограничена 30 минутами."
        )
        guest_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        guest_info.setWordWrap(True)
        guest_layout.addWidget(guest_info)
        
        self.btn_guest = QPushButton("👤  Войти как гость")
        self.btn_guest.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_guest.setMinimumHeight(40)
        guest_layout.addWidget(self.btn_guest)
        
        layout.addWidget(guest_group)
        
        # Info text
        info = QLabel(
            "💡 Аккаунт позволяет синхронизировать настройки между устройствами\n"
            "и получить доступ к расширенным функциям Arvis Server."
        )
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addStretch()
        return widget
    
    def _build_profile_view(self) -> QWidget:
        """Build profile view (when logged in)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Profile card
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        
        # Avatar and name
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        # Avatar circle
        avatar = QLabel("👤")
        avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['accent']};
                border-radius: 32px;
                font-size: 32px;
                padding: 8px;
            }}
        """)
        avatar.setFixedSize(64, 64)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(avatar)
        
        # User info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.profile_name = QLabel("Username")
        self.profile_name.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: bold;")
        info_layout.addWidget(self.profile_name)
        
        self.profile_role = QLabel("Роль: user")
        self.profile_role.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        info_layout.addWidget(self.profile_role)
        
        self.profile_server = QLabel("Сервер: localhost")
        self.profile_server.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        info_layout.addWidget(self.profile_server)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        card_layout.addLayout(header_layout)
        
        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        card_layout.addWidget(sep)
        
        # Session info
        self.session_info = QLabel("Авторизован")
        self.session_info.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
        card_layout.addWidget(self.session_info)
        
        # Logout button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_logout = QPushButton("🚪  Выйти")
        self.btn_logout.setStyleSheet(DANGER_BUTTON_STYLE)
        self.btn_logout.setMinimumWidth(120)
        btn_layout.addWidget(self.btn_logout)
        
        card_layout.addLayout(btn_layout)
        
        layout.addWidget(card)
        
        # Sync status
        sync_group = QGroupBox("Синхронизация")
        sync_group.setStyleSheet(GROUP_BOX_STYLE)
        sync_layout = QVBoxLayout(sync_group)
        sync_layout.setContentsMargins(16, 20, 16, 16)
        
        self.sync_status = QLabel("✓ Настройки синхронизированы")
        self.sync_status.setStyleSheet(f"color: {COLORS['text_secondary']};")
        sync_layout.addWidget(self.sync_status)
        
        self.btn_sync = QPushButton("🔄  Синхронизировать")
        self.btn_sync.setStyleSheet(SECONDARY_BUTTON_STYLE)
        sync_layout.addWidget(self.btn_sync)
        
        layout.addWidget(sync_group)
        
        layout.addStretch()
        return widget
    
    def _build_guest_view(self) -> QWidget:
        """Build guest profile view with timer"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Guest card
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['warning']};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        
        # Guest header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        guest_icon = QLabel("👤")
        guest_icon.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['warning']};
                border-radius: 32px;
                font-size: 32px;
                padding: 8px;
            }}
        """)
        guest_icon.setFixedSize(64, 64)
        guest_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(guest_icon)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        guest_title = QLabel("Гостевой режим")
        guest_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: bold;")
        info_layout.addWidget(guest_title)
        
        self.guest_timer_label = QLabel("⏱️ Осталось: 30:00")
        self.guest_timer_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 14px; font-weight: bold;")
        info_layout.addWidget(self.guest_timer_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        card_layout.addLayout(header_layout)
        
        # Progress bar for time
        self.guest_progress = QFrame()
        self.guest_progress.setFixedHeight(6)
        self.guest_progress.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['warning']};
                border-radius: 3px;
            }}
        """)
        card_layout.addWidget(self.guest_progress)
        
        # Warning
        warning = QLabel(
            "⚠️ В гостевом режиме некоторые функции ограничены.\n"
            "Войдите в аккаунт для полного доступа."
        )
        warning.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        warning.setWordWrap(True)
        card_layout.addWidget(warning)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_guest_login = QPushButton("🔐  Войти в аккаунт")
        self.btn_guest_login.setStyleSheet(PRIMARY_BUTTON_STYLE)
        btn_layout.addWidget(self.btn_guest_login)
        
        self.btn_guest_logout = QPushButton("🚪  Завершить")
        self.btn_guest_logout.setStyleSheet(DANGER_BUTTON_STYLE)
        btn_layout.addWidget(self.btn_guest_logout)
        
        card_layout.addLayout(btn_layout)
        
        layout.addWidget(card)
        layout.addStretch()
        return widget
    
    def _connect_signals(self):
        """Connect signals"""
        self.btn_login.clicked.connect(self._on_login)
        self.btn_guest.clicked.connect(self._on_guest_login)
        self.btn_logout.clicked.connect(self._on_logout)
        self.btn_sync.clicked.connect(self._on_sync)
        self.btn_guest_login.clicked.connect(self._on_guest_switch_to_login)
        self.btn_guest_logout.clicked.connect(self._on_logout)
        
        # Enter key to submit
        self.edit_password.returnPressed.connect(self._on_login)
        
        # Session manager signals
        self.session_manager.login_success.connect(self._on_login_success)
        self.session_manager.login_failed.connect(self._on_login_failed)
        self.session_manager.logout_complete.connect(self._update_view)
        self.session_manager.guest_session_started.connect(self._on_guest_started)
        self.session_manager.guest_session_tick.connect(self._on_guest_tick)
        self.session_manager.guest_session_expired.connect(self._on_guest_expired)
    
    def _update_view(self):
        """Update view based on login state"""
        if self.session_manager.is_logged_in:
            session = self.session_manager.session
            self.profile_name.setText(session.username)
            self.profile_role.setText(f"Роль: {session.role}")
            self.profile_server.setText(f"Сервер: {session.server_url}")
            if session.logged_in_at:
                self.session_info.setText(f"✓ Авторизован с {session.logged_in_at[:10]}")
            self.stack.setCurrentWidget(self.profile_widget)
        elif self.session_manager.is_guest:
            remaining = self.session_manager.get_guest_time_remaining()
            if remaining:
                self._update_guest_timer(remaining)
            self.stack.setCurrentWidget(self.guest_widget)
        else:
            self.stack.setCurrentWidget(self.login_widget)
    
    def _on_login(self):
        """Handle login button click"""
        server = self.edit_server.text().strip()
        username = self.edit_username.text().strip()
        password = self.edit_password.text()
        
        if not server:
            self._show_login_error("Введите адрес сервера")
            return
        if not username:
            self._show_login_error("Введите имя пользователя")
            return
        if not password:
            self._show_login_error("Введите пароль")
            return
        
        self.btn_login.setEnabled(False)
        self.btn_login.setText("⏳  Вход...")
        self.login_error.hide()
        
        self.session_manager.login(server, username, password)
    
    def _on_login_success(self, username: str):
        """Handle successful login"""
        self.btn_login.setEnabled(True)
        self.btn_login.setText("🔐  Войти")
        self.edit_password.clear()
        self._update_view()
        QMessageBox.information(self, "Успешно", f"Добро пожаловать, {username}!")
    
    def _on_login_failed(self, error: str):
        """Handle failed login"""
        self.btn_login.setEnabled(True)
        self.btn_login.setText("🔐  Войти")
        self._show_login_error(error)
    
    def _show_login_error(self, message: str):
        """Show error message in login form"""
        self.login_error.setText(f"⚠ {message}")
        self.login_error.show()
    
    def _on_logout(self):
        """Handle logout"""
        reply = QMessageBox.question(
            self,
            "Выход",
            "Вы уверены, что хотите выйти из аккаунта?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.session_manager.logout()
    
    def _on_sync(self):
        """Handle sync button"""
        # TODO: Implement settings sync
        QMessageBox.information(
            self,
            "Синхронизация",
            "Настройки синхронизированы с сервером."
        )
    
    def _on_guest_login(self):
        """Handle guest login button"""
        self.session_manager.start_guest_session()
    
    def _on_guest_started(self, remaining: int):
        """Handle guest session start"""
        self._update_guest_timer(remaining)
        self.stack.setCurrentWidget(self.guest_widget)
    
    def _on_guest_tick(self, remaining: int):
        """Handle guest timer tick"""
        self._update_guest_timer(remaining)
    
    def _on_guest_expired(self):
        """Handle guest session expiration"""
        QMessageBox.warning(
            self,
            "Сессия истекла",
            "Гостевая сессия завершена (30 минут).\n"
            "Войдите в аккаунт для продолжения работы."
        )
        self._update_view()
    
    def _on_guest_switch_to_login(self):
        """Switch from guest to login view"""
        self.session_manager.logout()
        self.stack.setCurrentWidget(self.login_widget)
    
    def _update_guest_timer(self, seconds: int):
        """Update guest timer display"""
        minutes = seconds // 60
        secs = seconds % 60
        self.guest_timer_label.setText(f"⏱️ Осталось: {minutes:02d}:{secs:02d}")
        
        # Update progress bar width based on remaining time (30 min = 1800 sec)
        max_time = 30 * 60
        progress_pct = (seconds / max_time) * 100
        
        # Change color when time is low
        if seconds < 300:  # Less than 5 minutes
            color = COLORS['danger']
        elif seconds < 600:  # Less than 10 minutes
            color = COLORS['warning']
        else:
            color = COLORS['success']
        
        self.guest_timer_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        self.guest_progress.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
    
    def refresh_activation(self):
        """Refresh activation widget status"""
        if self.activation_widget:
            self.activation_widget.refresh()
    
    def _on_deactivate_requested(self):
        """Handle deactivation request from activation widget"""
        # Get main window and show activation dialog
        main_window = self.window()
        if hasattr(main_window, 'show_activation_dialog'):
            main_window.show_activation_dialog()
