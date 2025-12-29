"""
User Management Dialog for Arvis Security System
Admin panel for managing users, roles, and permissions
"""

from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from i18n import _
from utils.logger import ModuleLogger
from utils.security import (
    AuditEventType,
    Permission,
    Role,
    UserStorage,
    get_audit_logger,
    get_auth_manager,
    get_rbac_manager,
    get_totp_manager,
)
from utils.security.hybrid_auth import get_hybrid_auth_manager
from utils.security.remote_auth_client import RemoteAuthClient
from config.config import Config


class UserManagementDialog(QDialog):
    """Dialog for managing users (Admin only)"""

    # Signals
    user_updated = pyqtSignal()

    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.logger = ModuleLogger("UserManagementDialog")
        self.current_user_id = current_user_id
        # Гибридный менеджер (удалённый + локальный)
        cfg = Config()
        self.auth_manager = get_hybrid_auth_manager({
            "auth.use_remote_server": bool(cfg.get("security.auth.use_remote_server", False)),
            "auth.remote_server_url": cfg.get("security.auth.server_url", "http://127.0.0.1:8000"),
        })
        self.rbac_manager = get_rbac_manager()
        self.audit_logger = get_audit_logger(None)  # Global audit logger
        self.storage = UserStorage()  # Storage for 2FA operations (Phase 2 Day 5)
        self.totp = get_totp_manager()  # TOTP manager for 2FA (Phase 2 Day 5)

        # Check admin permission
        if not self._check_admin_permission():
            QMessageBox.warning(
                parent,
                _("Доступ запрещён"),
                _("У вас нет прав для управления пользователями.\nТребуется роль администратора."),
            )
            self.reject()
            return

        self.init_ui()
        self.load_users()

    def _check_admin_permission(self) -> bool:
        """Check if current user has admin permissions"""
        try:
            # Set current user for RBAC check
            self.rbac_manager.set_current_user(self.current_user_id)

            # Check if user has user management permission
            # Разрешаем доступ если есть права управления безопасностью/ролями или явная админская роль
            has_permission = self.rbac_manager.has_any_permission(
                [
                    Permission.SECURITY_MANAGE,
                    Permission.USER_ROLE_MANAGE,
                    Permission.USER_EDIT,
                    Permission.USER_DELETE,
                    Permission.USER_CREATE,
                ]
            )
            self.logger.info(f"Admin permission check for {self.current_user_id}: {has_permission}")

            return has_permission

        except Exception as e:
            self.logger.error(f"Admin permission check failed: {e}")
            return False

    def init_ui(self):
        """Initialize user management UI"""
        self.setWindowTitle(_("Управление пользователями"))
        self.setFixedSize(900, 600)
        self.setModal(True)

        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)  # type: ignore[attr-defined]

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 15, 20, 20)
        content_layout.setSpacing(15)

        # Header section
        header_layout = QHBoxLayout()

        title_label = QLabel("👥 " + _("Управление пользователями"))
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
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Action buttons
        self.create_user_button = QPushButton("➕ " + _("Создать пользователя"))
        self.create_user_button.clicked.connect(self.create_user)

        self.refresh_button = QPushButton("🔄 " + _("Обновить"))
        self.refresh_button.clicked.connect(self.load_users)

        header_layout.addWidget(self.create_user_button)
        header_layout.addWidget(self.refresh_button)

        content_layout.addLayout(header_layout)

        # Search/Filter section
        filter_layout = QHBoxLayout()

        search_label = QLabel(_("Поиск:"))
        search_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        filter_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_("Введите имя пользователя..."))
        self.search_input.textChanged.connect(self.filter_users)
        filter_layout.addWidget(self.search_input, 1)

        role_filter_label = QLabel(_("Роль:"))
        role_filter_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        filter_layout.addWidget(role_filter_label)

        self.role_filter = QComboBox()
        self.role_filter.addItems(
            [_("Все"), _("Гость"), _("Пользователь"), _("Опытный пользователь"), _("Администратор")]
        )
        self.role_filter.currentIndexChanged.connect(self.filter_users)
        filter_layout.addWidget(self.role_filter)

        content_layout.addLayout(filter_layout)

        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(7)  # +1 для 2FA колонки
        self.users_table.setHorizontalHeaderLabels(
            [_("ID"), _("Имя пользователя"), _("Роль"), _("Статус"), _("2FA"), _("Последний вход"), _("Действия")]
        )

        # Table styling
        try:
            header = self.users_table.horizontalHeader()
            if header is not None:  # type: ignore[truthy-bool]
                header.setSectionResizeMode(QHeaderView.Interactive)
                header.setStretchLastSection(True)
        except Exception:
            # Может отсутствовать в некоторых окружениях анализа
            pass

        # Set column widths
        self.users_table.setColumnWidth(0, 80)  # ID
        self.users_table.setColumnWidth(1, 150)  # Username
        self.users_table.setColumnWidth(2, 130)  # Role
        self.users_table.setColumnWidth(3, 90)  # Status
        self.users_table.setColumnWidth(4, 60)  # 2FA
        self.users_table.setColumnWidth(5, 130)  # Last login

        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)

        content_layout.addWidget(self.users_table, 1)

        # Statistics section
        stats_layout = QHBoxLayout()

        self.total_users_label = QLabel(_("Всего пользователей: 0"))
        self.total_users_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); background: transparent;")
        stats_layout.addWidget(self.total_users_label)

        self.active_users_label = QLabel(_("Активных: 0"))
        self.active_users_label.setStyleSheet("color: #4aff4a; background: transparent;")
        stats_layout.addWidget(self.active_users_label)

        self.inactive_users_label = QLabel(_("Деактивированных: 0"))
        self.inactive_users_label.setStyleSheet("color: #ff9a4a; background: transparent;")
        stats_layout.addWidget(self.inactive_users_label)

        stats_layout.addStretch()

        content_layout.addLayout(stats_layout)

        # Bottom buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.close_button = QPushButton(_("Закрыть"))
        self.close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.close_button)

        content_layout.addLayout(buttons_layout)

        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        self.setLayout(main_layout)

        # Apply styles
        self.apply_styles()

    def _create_title_bar(self) -> QWidget:
        """Create custom title bar"""
        title_bar = QWidget()
        title_bar.setFixedHeight(35)
        title_bar.setStyleSheet(
            """
            QWidget {
                background-color: rgb(43, 43, 43);
                border-bottom: 1px solid rgb(60, 60, 60);
            }
        """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(10)

        title_label = QLabel(_("Панель управления"))
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 13px;
                border: none;
                background: transparent;
            }
        """
        )

        layout.addWidget(title_label)
        layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: rgba(255, 255, 255, 0.7);
                border: none;
                font-size: 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(232, 17, 35, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(180, 30, 30, 1.0);
            }
        """
        )
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        title_bar.setLayout(layout)

        # Make draggable
        title_bar.mousePressEvent = self._title_bar_mouse_press  # type: ignore[assignment]
        title_bar.mouseMoveEvent = self._title_bar_mouse_move  # type: ignore[assignment]

        return title_bar

    def _title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _title_bar_mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "drag_pos"):  # type: ignore[attr-defined]
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
                font-size: 12px;
            }

            QLineEdit:focus {
                border: 1px solid #4a9eff;
                background-color: rgba(60, 60, 60, 0.8);
            }

            QComboBox {
                background-color: rgba(60, 60, 60, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 6px 10px;
                color: white;
                font-size: 12px;
            }

            QComboBox::drop-down {
                border: none;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid white;
            }

            QTableWidget {
                background-color: rgba(30, 30, 30, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                color: white;
                gridline-color: rgba(255, 255, 255, 0.1);
            }

            QTableWidget::item {
                padding: 8px;
            }

            QTableWidget::item:selected {
                background-color: rgba(74, 158, 255, 0.3);
            }

            QHeaderView::section {
                background-color: rgba(60, 60, 60, 0.8);
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }

            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #3a8eff;
            }

            QPushButton:pressed {
                background-color: #2a7eff;
            }

            QPushButton#action_button {
                background-color: rgba(255, 255, 255, 0.1);
                padding: 6px 12px;
            }

            QPushButton#action_button:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }

            QPushButton#danger_button {
                background-color: rgba(255, 74, 74, 0.7);
            }

            QPushButton#danger_button:hover {
                background-color: rgba(255, 74, 74, 0.9);
            }
        """
        )

    def load_users(self):
        """Load users from database"""
        try:
            # Получаем пользователей ТОЛЬКО с сервера (если доступен)
            remote_users = []
            use_server = False
            
            try:
                # Пробуем через Client API
                if hasattr(self.auth_manager, "client_api") and self.auth_manager.client_api:
                    client_api = self.auth_manager.client_api
                    if client_api.is_authenticated():
                        ok, data = client_api.admin_list_users()
                        if ok and isinstance(data, list):
                            remote_users = data
                            use_server = True
                            self.logger.info(f"✓ Loaded {len(remote_users)} users from server (Client API)")
            except Exception as e:
                self.logger.warning(f"Client API unavailable: {e}")
            
            # Fallback на RemoteAuthClient (старый API)
            if not use_server:
                try:
                    client = RemoteAuthClient.get()
                    if client.is_authenticated():
                        ok, data = client.list_users()
                        if ok and isinstance(data, list):
                            remote_users = data
                            use_server = True
                            self.logger.info(f"✓ Loaded {len(remote_users)} users from server (Admin API)")
                except Exception as e:
                    self.logger.warning(f"Admin API unavailable: {e}")

            if use_server and remote_users:
                # Используем ТОЛЬКО серверных пользователей
                class RUser:
                    def __init__(self, d):
                        from utils.security.rbac import Role as RoleEnum
                        self.user_id = d.get("user_id")
                        self.username = d.get("username")
                        role_key = (d.get("role") or "user").upper()
                        self.role = RoleEnum.__members__.get(role_key, RoleEnum.USER)
                        self.is_active = bool(d.get("is_active", True))
                        self.require_2fa = bool(d.get("require_2fa", False))
                        self.totp_secret = None
                        self.last_login = d.get("last_login")
                users = [RUser(u) for u in remote_users]
                self.logger.info("→ Using server users list (local users ignored)")
            else:
                # Сервер недоступен - показываем локальных пользователей с предупреждением
                if hasattr(self.auth_manager, "local_auth") and self.auth_manager.local_auth:
                    users = self.auth_manager.local_auth.list_users()
                else:
                    from utils.security.auth import AuthManager as _LocalAuth
                    users = _LocalAuth({}).list_users()
                
                self.logger.warning("⚠ Server unavailable - showing local users only")
                QMessageBox.warning(
                    self,
                    _("Работа в автономном режиме"),
                    _("Сервер недоступен.\n\nПоказаны только локальные пользователи.\n"
                      "Изменения будут сохранены локально и не синхронизируются с сервером.")
                )

            self.users_table.setRowCount(0)
            self.all_users = users  # Store for filtering

            # Statistics
            total = len(users)
            active = sum(1 for u in users if u.is_active)
            inactive = total - active

            self.total_users_label.setText(_("Всего пользователей: {count}").format(count=total))
            self.active_users_label.setText(_("Активных: {count}").format(count=active))
            self.inactive_users_label.setText(_("Деактивированных: {count}").format(count=inactive))

            # Populate table
            for user in users:
                self._add_user_to_table(user)

            self.logger.info(f"Loaded {total} users")

        except Exception as e:
            self.logger.error(f"Failed to load users: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Не удалось загрузить пользователей:\n{error}").format(error=e))

    def _add_user_to_table(self, user):
        """Add user to table"""
        row = self.users_table.rowCount()
        self.users_table.insertRow(row)

        # ID
        id_item = QTableWidgetItem(user.user_id[:8] + "...")
        id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
        self.users_table.setItem(row, 0, id_item)

        # Username
        username_item = QTableWidgetItem(user.username)
        username_item.setFlags(username_item.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
        self.users_table.setItem(row, 1, username_item)

        # Role
        role_text = self._get_role_display_name(user.role)
        role_item = QTableWidgetItem(role_text)
        role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
        self._apply_role_color(role_item, user.role)
        self.users_table.setItem(row, 2, role_item)

        # Status
        status_text = _("Активен") if user.is_active else _("Деактивирован")
        status_item = QTableWidgetItem(status_text)
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
        status_item.setForeground(QColor('green') if user.is_active else QColor('gray'))
        self.users_table.setItem(row, 3, status_item)

        # 2FA Status (Phase 2 Day 5)
        twofa_text = "✅" if user.require_2fa else "❌"
        twofa_item = QTableWidgetItem(twofa_text)
        twofa_item.setFlags(twofa_item.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
        try:
            from PyQt6.QtCore import Qt as _Qt
            twofa_item.setTextAlignment(_Qt.AlignmentFlag.AlignCenter)  # type: ignore[attr-defined]
        except Exception:
            twofa_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore[attr-defined]
        twofa_item.setForeground(QColor('green') if user.require_2fa else QColor('gray'))
        self.users_table.setItem(row, 4, twofa_item)

        # Last login
        if user.last_login:
            try:
                dt = datetime.fromisoformat(user.last_login)
                last_login_text = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                last_login_text = _("Неизвестно")
        else:
            last_login_text = _("Никогда")

        last_login_item = QTableWidgetItem(last_login_text)
        last_login_item.setFlags(last_login_item.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
        self.users_table.setItem(row, 5, last_login_item)  # Индекс 5 (было 4)

        # Actions - create widget with buttons
        actions_widget = self._create_action_buttons(user)
        self.users_table.setCellWidget(row, 6, actions_widget)  # Индекс 6 (было 5)

    def _get_role_display_name(self, role: Role) -> str:
        """Get localized role name"""
        role_names = {
            Role.GUEST: _("Гость"),
            Role.USER: _("Пользователь"),
            Role.POWER_USER: _("Опытный пользователь"),
            Role.ADMIN: _("Администратор"),
        }
        return role_names.get(role, str(role.value))

    def _apply_role_color(self, item: QTableWidgetItem, role: Role):
        """Apply color coding to role"""
        from PyQt6.QtGui import QColor
        colors = {
            Role.GUEST: QColor('gray'),
            Role.USER: QColor('cyan'),
            Role.POWER_USER: QColor('yellow'),
            Role.ADMIN: QColor('red'),
        }
        color = colors.get(role, QColor('white'))
        item.setForeground(color)

    def _create_action_buttons(self, user) -> QWidget:
        """Create action buttons for user row"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        # Edit role button
        edit_btn = QPushButton(_("Роль"))
        edit_btn.setObjectName("action_button")
        edit_btn.clicked.connect(lambda: self.edit_user_role(user))
        layout.addWidget(edit_btn)

        # Deactivate/Activate button
        if user.is_active:
            deactivate_btn = QPushButton(_("Деактивировать"))
            deactivate_btn.setObjectName("danger_button")
            deactivate_btn.clicked.connect(lambda: self.deactivate_user(user))
            layout.addWidget(deactivate_btn)
        else:
            activate_btn = QPushButton(_("Активировать"))
            activate_btn.setObjectName("action_button")
            activate_btn.clicked.connect(lambda: self.activate_user(user))
            layout.addWidget(activate_btn)

        # Delete button (only for inactive users)
        if not user.is_active:
            delete_btn = QPushButton(_("Удалить"))
            delete_btn.setObjectName("danger_button")
            delete_btn.clicked.connect(lambda: self.delete_user(user))
            layout.addWidget(delete_btn)

        # Reset password button
        reset_btn = QPushButton(_("Сброс пароля"))
        reset_btn.setObjectName("action_button")
        reset_btn.clicked.connect(lambda: self.reset_password(user))
        layout.addWidget(reset_btn)

        # 2FA Management buttons (Phase 2 Day 5)
        if user.require_2fa:
            # Disable 2FA button
            disable_2fa_btn = QPushButton("🔓 " + _("Откл. 2FA"))
            disable_2fa_btn.setObjectName("action_button")
            disable_2fa_btn.setToolTip(_("Отключить двухфакторную аутентификацию"))
            disable_2fa_btn.clicked.connect(lambda: self.disable_2fa(user))
            layout.addWidget(disable_2fa_btn)
        else:
            # Enable 2FA button
            enable_2fa_btn = QPushButton("🔐 " + _("Вкл. 2FA"))
            enable_2fa_btn.setObjectName("action_button")
            enable_2fa_btn.setToolTip(_("Включить двухфакторную аутентификацию"))
            enable_2fa_btn.clicked.connect(lambda: self.enable_2fa(user))
            layout.addWidget(enable_2fa_btn)

        # Reset 2FA button (always visible if 2FA was ever enabled)
        if user.require_2fa or user.totp_secret:
            reset_2fa_btn = QPushButton("🔄 " + _("Сброс 2FA"))
            reset_2fa_btn.setObjectName("danger_button")
            reset_2fa_btn.setToolTip(_("Сбросить настройки 2FA"))
            reset_2fa_btn.clicked.connect(lambda: self.reset_2fa(user))
            layout.addWidget(reset_2fa_btn)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def filter_users(self):
        """Filter users based on search and role"""
        search_text = self.search_input.text().lower()
        role_index = self.role_filter.currentIndex()

        # Role mapping
        role_map = {
            0: None,  # All
            1: Role.GUEST,
            2: Role.USER,
            3: Role.POWER_USER,
            4: Role.ADMIN,
        }
        selected_role = role_map[role_index]

        # Filter users
        for row in range(self.users_table.rowCount()):
            username_item = self.users_table.item(row, 1)
            role_item = self.users_table.item(row, 2)
            username = (username_item.text().lower() if username_item else "")
            user_role_text = (role_item.text() if role_item else "")

            # Check username match
            username_match = search_text in username if search_text else True

            # Check role match
            if selected_role is None:
                role_match = True
            else:
                expected_role_text = self._get_role_display_name(selected_role)
                role_match = user_role_text == expected_role_text

            # Show/hide row
            self.users_table.setRowHidden(row, not (username_match and role_match))

    def create_user(self):
        """Create new user (server if available, else local)"""
        from PyQt6.QtWidgets import QInputDialog

        # If remote admin session available -> create on server
        try:
            client = RemoteAuthClient.get()
            if client.is_authenticated():
                username, ok1 = QInputDialog.getText(self, _("Создать пользователя"), _("Имя пользователя:"))
                if not ok1 or not username:
                    return
                password, ok2 = QInputDialog.getText(self, _("Создать пользователя"), _("Пароль:"), QLineEdit.EchoMode.Password)
                if not ok2 or not password:
                    return
                confirm, ok3 = QInputDialog.getText(self, _("Создать пользователя"), _("Подтвердите пароль:"), QLineEdit.EchoMode.Password)
                if not ok3 or confirm != password:
                    QMessageBox.warning(self, _("Ошибка"), _("Пароли не совпадают"))
                    return
                roles = [_("Гость"), _("Пользователь"), _("Опытный пользователь"), _("Администратор")]
                role_map = {roles[0]: "guest", roles[1]: "user", roles[2]: "power_user", roles[3]: "admin"}
                role_sel, ok4 = QInputDialog.getItem(self, _("Роль"), _("Выберите роль:"), roles, 1, False)
                if not ok4 or not role_sel:
                    return
                role_val = role_map[role_sel]

                ok, resp = client.create_user(username=username.strip(), password=password, role=role_val)
                if ok:
                    QMessageBox.information(self, _("Успех"), _("Пользователь создан на сервере"))
                    self.load_users(); self.user_updated.emit()
                    return
                else:
                    err = resp.get("error") if isinstance(resp, dict) else None
                    QMessageBox.warning(self, _("Ошибка"), err or _("Не удалось создать пользователя"))
                    return
        except Exception as e:
            self.logger.warning(f"Admin API create failed: {e}")

        # Fallback: локальное создание с предупреждением
        reply = QMessageBox.question(
            self,
            _("Работа в автономном режиме"),
            _("Сервер недоступен.\n\nСоздать пользователя локально?\n"
              "(Не будет синхронизирован с сервером)"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            from .login_dialog import CreateAccountDialog
            dialog = CreateAccountDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_users(); self.user_updated.emit()

    def edit_user_role(self, user):
        """Edit user role"""
        # Cannot edit own role
        if user.user_id == self.current_user_id:
            QMessageBox.warning(self, _("Ошибка"), _("Вы не можете изменить свою собственную роль"))
            return

        # Show role selection dialog
        from PyQt6.QtWidgets import QInputDialog

        roles = [_("Гость"), _("Пользователь"), _("Опытный пользователь"), _("Администратор")]
        current_role_name = self._get_role_display_name(user.role)
        current_index = roles.index(current_role_name) if current_role_name in roles else 1

        selected_role, ok = QInputDialog.getItem(
            self,
            _("Изменить роль"),
            _("Выберите новую роль для {username}:").format(username=user.username),
            roles,
            current_index,
            False,
        )

        if ok and selected_role:
            # Map back to Role enum
            role_map = {
                roles[0]: Role.GUEST,
                roles[1]: Role.USER,
                roles[2]: Role.POWER_USER,
                roles[3]: Role.ADMIN,
            }
            new_role = role_map[selected_role]

            try:
                # Update role
                user.role = new_role
                server_updated = False
                
                # Пробуем обновить на сервере через Client API
                try:
                    if hasattr(self.auth_manager, "client_api") and self.auth_manager.client_api:
                        client_api = self.auth_manager.client_api
                        if client_api.is_authenticated():
                            ok, _ = client_api.admin_update_user(user.user_id, role=new_role.value)
                            if ok:
                                server_updated = True
                                self.logger.info(f"✓ Role updated on server (Client API): {user.username}")
                except Exception as e:
                    self.logger.warning(f"Client API update failed: {e}")
                
                # Fallback на Admin API
                if not server_updated:
                    try:
                        client = RemoteAuthClient.get()
                        if client.is_authenticated():
                            ok, _ = client.update_user(user.user_id, role=new_role.value)
                            if ok:
                                server_updated = True
                                self.logger.info(f"✓ Role updated on server (Admin API): {user.username}")
                    except Exception as e:
                        self.logger.warning(f"Admin API update failed: {e}")
                
                # Локальное обновление (только если сервер недоступен)
                if not server_updated:
                    try:
                        if hasattr(self.auth_manager, "local_auth") and self.auth_manager.local_auth:
                            self.auth_manager.local_auth.update_user(user.user_id, role=new_role.value)
                            self.logger.warning("⚠ Role updated locally (server unavailable)")
                    except Exception as e:
                        self.logger.error(f"Local update failed: {e}")

                # Audit log
                self.audit_logger.log_event(
                    AuditEventType.USER_ROLE_CHANGED,
                    action="user.role.changed",
                    user_id=self.current_user_id,
                    details={"target_user": user.username, "new_role": new_role.value},
                )

                self.logger.info(f"Role updated for user {user.username}: {new_role.value}")
                QMessageBox.information(self, _("Успех"), _("Роль успешно изменена"))

                self.load_users()
                self.user_updated.emit()

            except Exception as e:
                self.logger.error(f"Failed to update role: {e}")
                QMessageBox.critical(self, _("Ошибка"), _("Не удалось изменить роль:\n{error}").format(error=e))

    def deactivate_user(self, user):
        """Deactivate user"""
        # Cannot deactivate self
        if user.user_id == self.current_user_id:
            QMessageBox.warning(self, _("Ошибка"), _("Вы не можете деактивировать свой собственный аккаунт"))
            return

        reply = QMessageBox.question(
            self,
            _("Подтверждение"),
            _(
                "Вы уверены, что хотите деактивировать пользователя {username}?\n\nПользователь не сможет войти в систему."
            ).format(username=user.username),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Деактивация: на сервере и локально
                user.is_active = False
                server_updated = False
                
                # Пробуем через Client API
                try:
                    if hasattr(self.auth_manager, "client_api") and self.auth_manager.client_api:
                        client_api = self.auth_manager.client_api
                        if client_api.is_authenticated():
                            ok, _ = client_api.admin_update_user(user.user_id, is_active=False)
                            if ok:
                                server_updated = True
                except Exception:
                    pass
                
                # Fallback на Admin API
                if not server_updated:
                    try:
                        client = RemoteAuthClient.get()
                        if client.is_authenticated():
                            ok, _ = client.update_user(user.user_id, is_active=False)
                            if ok:
                                server_updated = True
                    except Exception:
                        pass
                
                # Локально (если сервер недоступен)
                if not server_updated:
                    try:
                        if hasattr(self.auth_manager, "local_auth") and self.auth_manager.local_auth:
                            self.auth_manager.local_auth.update_user(user.user_id, is_active=False)
                    except Exception:
                        pass

                # Audit log
                self.audit_logger.log_event(
                    AuditEventType.USER_DEACTIVATED,
                    action="user.deactivated",
                    user_id=self.current_user_id,
                    details={"target_user": user.username},
                )

                self.logger.info(f"User deactivated: {user.username}")
                QMessageBox.information(self, _("Успех"), _("Пользователь деактивирован"))

                self.load_users()
                self.user_updated.emit()

            except Exception as e:
                self.logger.error(f"Failed to deactivate user: {e}")
                QMessageBox.critical(
                    self, _("Ошибка"), _("Не удалось деактивировать пользователя:\n{error}").format(error=e)
                )

    def activate_user(self, user):
        """Activate user"""
        try:
            # Активация
            user.is_active = True
            server_updated = False
            
            # Пробуем через Client API
            try:
                if hasattr(self.auth_manager, "client_api") and self.auth_manager.client_api:
                    client_api = self.auth_manager.client_api
                    if client_api.is_authenticated():
                        ok, _ = client_api.admin_update_user(user.user_id, is_active=True)
                        if ok:
                            server_updated = True
            except Exception:
                pass
            
            # Fallback на Admin API
            if not server_updated:
                try:
                    client = RemoteAuthClient.get()
                    if client.is_authenticated():
                        ok, _ = client.update_user(user.user_id, is_active=True)
                        if ok:
                            server_updated = True
                except Exception:
                    pass
            
            # Локально (если сервер недоступен)
            if not server_updated:
                try:
                    if hasattr(self.auth_manager, "local_auth") and self.auth_manager.local_auth:
                        self.auth_manager.local_auth.update_user(user.user_id, is_active=True)
                except Exception:
                    pass

            # Audit log
            self.audit_logger.log_event(
                AuditEventType.USER_ACTIVATED,
                action="user.activated",
                user_id=self.current_user_id,
                details={"target_user": user.username},
            )

            self.logger.info(f"User activated: {user.username}")
            QMessageBox.information(self, _("Успех"), _("Пользователь активирован"))

            self.load_users()
            self.user_updated.emit()

        except Exception as e:
            self.logger.error(f"Failed to activate user: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Не удалось активировать пользователя:\n{error}").format(error=e))

    def delete_user(self, user):
        """Delete user permanently"""
        # Cannot delete self
        if user.user_id == self.current_user_id:
            QMessageBox.warning(self, _("Ошибка"), _("Вы не можете удалить свой собственный аккаунт"))
            return

        reply = QMessageBox.question(
            self,
            _("Подтверждение"),
            _("Вы уверены, что хотите УДАЛИТЬ пользователя {username}?\n\nЭто действие необратимо!").format(
                username=user.username
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Удаление пользователя
                server_deleted = False
                
                # Пробуем через Client API
                try:
                    if hasattr(self.auth_manager, "client_api") and self.auth_manager.client_api:
                        client_api = self.auth_manager.client_api
                        if client_api.is_authenticated():
                            if client_api.admin_delete_user(user.user_id):
                                server_deleted = True
                except Exception:
                    pass
                
                # Fallback на Admin API
                if not server_deleted:
                    try:
                        client = RemoteAuthClient.get()
                        if client.is_authenticated():
                            if client.delete_user(user.user_id):
                                server_deleted = True
                    except Exception:
                        pass
                
                # Локально (если сервер недоступен)
                if not server_deleted:
                    try:
                        if hasattr(self.auth_manager, "local_auth") and self.auth_manager.local_auth:
                            self.auth_manager.local_auth.delete_user(user.user_id)
                    except Exception:
                        pass

                # Audit log
                self.audit_logger.log_event(
                    AuditEventType.USER_DELETED,
                    action="user.deleted",
                    user_id=self.current_user_id,
                    details={"target_user": user.username},
                )

                self.logger.info(f"User deleted: {user.username}")
                QMessageBox.information(self, _("Успех"), _("Пользователь удалён"))

                self.load_users()
                self.user_updated.emit()

            except Exception as e:
                self.logger.error(f"Failed to delete user: {e}")
                QMessageBox.critical(self, _("Ошибка"), _("Не удалось удалить пользователя:\n{error}").format(error=e))

    def reset_password(self, user):
        """Reset user password"""
        from PyQt6.QtWidgets import QInputDialog

        new_password, ok = QInputDialog.getText(
            self,
            _("Сброс пароля"),
            _("Введите новый пароль для {username}:").format(username=user.username),
            QLineEdit.EchoMode.Password,
        )

        if ok and new_password:
            if len(new_password) < 8:
                QMessageBox.warning(self, _("Ошибка"), _("Пароль должен содержать минимум 8 символов"))
                return

            try:
                # Update password using AuthManager method
                # Смена пароля админом: пробуем серверный вызов
                server_changed = False
                try:
                    client = RemoteAuthClient.get()
                    if client.is_authenticated():
                        # На сервере нет отдельного эндпоинта для admin reset, можно временно поставить is_active=False/True и попросить пользователя сменить пароль вручную.
                        # Поэтому используем локальный метод как fallback.
                        pass
                except Exception:
                    pass

                if not server_changed:
                        result_ok = False
                        try:
                            if hasattr(self.auth_manager, "local_auth") and self.auth_manager.local_auth:
                                result_ok = bool(self.auth_manager.local_auth.change_password(user.username, "", new_password))
                        except Exception:
                            result_ok = False
                else:
                    result_ok = True

                if result_ok:
                    # Audit log
                    self.audit_logger.log_event(
                        AuditEventType.PASSWORD_CHANGED,
                        action="auth.password.changed",
                        user_id=self.current_user_id,
                        details={"target_user": user.username, "by": "admin"},
                    )

                    self.logger.info(f"Password reset for user: {user.username}")
                    QMessageBox.information(self, _("Успех"), _("Пароль успешно изменён"))
                else:
                    QMessageBox.warning(self, _("Ошибка"), _("Не удалось изменить пароль"))

            except Exception as e:
                self.logger.error(f"Failed to reset password: {e}")
                QMessageBox.critical(self, _("Ошибка"), _("Не удалось сбросить пароль:\n{error}").format(error=e))

    # 2FA Management Methods (Phase 2 Day 5)

    def enable_2fa(self, user):
        """Enable 2FA for user (Admin action)"""
        try:
            # Import dialog here to avoid circular imports
            from src.gui.two_factor_setup_dialog import TwoFactorSetupDialog

            # Show 2FA setup dialog
            dialog = TwoFactorSetupDialog(self, user.username)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get encrypted secret and hashed backup codes
                encrypted_secret = dialog.get_encrypted_secret()
                hashed_codes = dialog.get_hashed_backup_codes()

                # Get storage and TOTP manager
                storage = UserStorage()
                totp = get_totp_manager()

                # Serialize backup codes
                serialized_codes = totp.serialize_backup_codes(hashed_codes)

                # Enable 2FA in database
                if storage.enable_two_factor(user.user_id, encrypted_secret, serialized_codes):
                    # Audit log
                    self.audit_logger.log_event(
                        AuditEventType.TWO_FACTOR_ENABLED,
                        self.current_user_id,
                        success=True,
                        details={"target_user": user.username, "enabled_by": "admin"},
                    )

                    self.logger.info(f"2FA enabled for user: {user.username} by admin")
                    QMessageBox.information(
                        self,
                        _("Успех"),
                        _("Двухфакторная аутентификация включена для пользователя {username}").format(
                            username=user.username
                        ),
                    )

                    # Reload users to update table
                    self.load_users()
                    self.user_updated.emit()
                else:
                    raise Exception("Failed to enable 2FA in database")

        except Exception as e:
            self.logger.error(f"Failed to enable 2FA: {e}")
            QMessageBox.critical(self, _("Ошибка"), _("Не удалось включить 2FA:\n{error}").format(error=e))

    def disable_2fa(self, user):
        """Disable 2FA for user (Admin action)"""
        # Confirm action
        reply = QMessageBox.question(
            self,
            _("Подтверждение"),
            _(
                "Вы уверены, что хотите отключить двухфакторную аутентификацию для пользователя {username}?\n\n"
                "Это действие удалит все данные 2FA (секрет и резервные коды)."
            ).format(username=user.username),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                storage = UserStorage()

                # Disable 2FA in database
                if storage.disable_two_factor(user.user_id):
                    # Audit log
                    self.audit_logger.log_event(
                        AuditEventType.TWO_FACTOR_DISABLED,
                        self.current_user_id,
                        success=True,
                        details={"target_user": user.username, "disabled_by": "admin"},
                    )

                    self.logger.info(f"2FA disabled for user: {user.username} by admin")
                    QMessageBox.information(
                        self,
                        _("Успех"),
                        _("Двухфакторная аутентификация отключена для пользователя {username}").format(
                            username=user.username
                        ),
                    )

                    # Reload users
                    self.load_users()
                    self.user_updated.emit()
                else:
                    raise Exception("Failed to disable 2FA in database")

            except Exception as e:
                self.logger.error(f"Failed to disable 2FA: {e}")
                QMessageBox.critical(self, _("Ошибка"), _("Не удалось отключить 2FA:\n{error}").format(error=e))

    def reset_2fa(self, user):
        """Reset 2FA for user (Admin action) - Complete reset requiring new setup"""
        # Confirm action
        reply = QMessageBox.question(
            self,
            _("Подтверждение"),
            _(
                "Вы уверены, что хотите сбросить двухфакторную аутентификацию для пользователя {username}?\n\n"
                "Это действие:\n"
                "• Удалит текущий секрет и резервные коды\n"
                "• Отключит 2FA\n"
                "• Потребует новую настройку от пользователя\n\n"
                "Используйте это, если пользователь потерял доступ к приложению аутентификации."
            ).format(username=user.username),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                storage = UserStorage()

                # Disable 2FA (complete reset)
                if storage.disable_two_factor(user.user_id):
                    # Audit log
                    self.audit_logger.log_event(
                        AuditEventType.TWO_FACTOR_RESET,
                        self.current_user_id,
                        success=True,
                        details={"target_user": user.username, "reset_by": "admin", "reason": "admin_reset"},
                    )

                    self.logger.info(f"2FA reset for user: {user.username} by admin")
                    QMessageBox.information(
                        self,
                        _("Успех"),
                        _(
                            "Двухфакторная аутентификация сброшена для пользователя {username}.\n\n"
                            "Пользователь может настроить 2FA заново при следующем входе."
                        ).format(username=user.username),
                    )

                    # Reload users
                    self.load_users()
                    self.user_updated.emit()
                else:
                    raise Exception("Failed to reset 2FA in database")

            except Exception as e:
                self.logger.error(f"Failed to reset 2FA: {e}")
                QMessageBox.critical(self, _("Ошибка"), _("Не удалось сбросить 2FA:\n{error}").format(error=e))
