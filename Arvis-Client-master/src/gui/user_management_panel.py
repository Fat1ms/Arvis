"""
User Management Panel for Administrators
Панель управления пользователями для администраторов
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
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
from utils.security import Role, get_auth_manager, get_rbac_manager
from utils.security.storage import UserStorage


class UserManagementPanel(QDialog):
    """Panel for managing users (Admin only)"""

    # Signals
    user_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = ModuleLogger("UserManagementPanel")
        self.auth_manager = get_auth_manager()
        self.rbac_manager = get_rbac_manager()
        self.storage = UserStorage()
        self.init_ui()
        self.load_users()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(_("Управление пользователями"))
        self.setFixedSize(900, 600)
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
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Title
        title_label = QLabel(_("👥 Управление пользователями"))
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                background: transparent;
            }
        """
        )
        content_layout.addWidget(title_label)

        # Info
        info_label = QLabel(
            _(
                "Управление пользователями системы. Администраторы могут изменять роли "
                "и активировать/деактивировать аккаунты."
            )
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px; background: transparent;")
        content_layout.addWidget(info_label)

        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels(
            [
                _("Имя пользователя"),
                _("Роль"),
                _("Статус"),
                _("Создан"),
                _("Последний вход"),
                _("Действия"),
            ]
        )

        # Table styling
        self.users_table.setStyleSheet(
            """
            QTableWidget {
                background-color: rgb(50, 50, 50);
                border: 1px solid rgba(255, 255, 255, 0.2);
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
                background-color: rgb(60, 60, 60);
                color: white;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #4a9eff;
                font-weight: bold;
            }
        """
        )

        # Adjust column widths
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Username
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Role
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Created
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Last login
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Actions
        self.users_table.setColumnWidth(5, 200)

        content_layout.addWidget(self.users_table)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.refresh_button = QPushButton(_("🔄 Обновить"))
        self.refresh_button.clicked.connect(self.load_users)

        self.close_button = QPushButton(_("Закрыть"))
        self.close_button.clicked.connect(self.accept)

        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addStretch()
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
        title_label = QLabel(_("Администрирование"))
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
        close_btn.clicked.connect(self.accept)
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

            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                min-width: 100px;
            }

            QPushButton:hover {
                background-color: #3a8eff;
            }

            QPushButton:pressed {
                background-color: #2a7eff;
            }

            QPushButton#close_button {
                background-color: rgba(255, 255, 255, 0.1);
            }

            QPushButton#close_button:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }

            QComboBox {
                background-color: rgba(60, 60, 60, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                padding: 5px;
                color: white;
                min-width: 120px;
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

            QComboBox:focus {
                border: 1px solid #4a9eff;
            }
        """
        )

        self.close_button.setObjectName("close_button")

    def load_users(self):
        """Load users from database"""
        try:
            users = self.storage.list_users()
            self.logger.info(f"Loading {len(users)} users")

            self.users_table.setRowCount(len(users))

            for row, user in enumerate(users):
                # Username
                username_item = QTableWidgetItem(user.username)
                username_item.setFlags(username_item.flags() & ~Qt.ItemIsEditable)
                self.users_table.setItem(row, 0, username_item)

                # Role with dropdown
                role_combo = QComboBox()
                role_combo.addItems([_("Гость"), _("Пользователь"), _("Опытный"), _("Администратор")])
                role_combo.setCurrentIndex(self._role_to_index(user.role))
                role_combo.currentIndexChanged.connect(
                    lambda idx, u=user: self.change_user_role(u.user_id, self._index_to_role(idx))
                )
                self.users_table.setCellWidget(row, 1, role_combo)

                # Disable admin role change for admin user
                if user.username == "admin":
                    role_combo.setEnabled(False)
                    role_combo.setStyleSheet("background-color: rgba(60, 60, 60, 0.4);")

                # Status
                status_text = _("✅ Активен") if user.is_active else _("❌ Неактивен")
                status_item = QTableWidgetItem(status_text)
                status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                self.users_table.setItem(row, 2, status_item)

                # Created date
                created_item = QTableWidgetItem(user.created_at.strftime("%Y-%m-%d %H:%M"))
                created_item.setFlags(created_item.flags() & ~Qt.ItemIsEditable)
                self.users_table.setItem(row, 3, created_item)

                # Last login
                last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else _("Никогда")
                last_login_item = QTableWidgetItem(last_login)
                last_login_item.setFlags(last_login_item.flags() & ~Qt.ItemIsEditable)
                self.users_table.setItem(row, 4, last_login_item)

                # Actions - container widget
                actions_widget = QWidget()
                actions_layout = QHBoxLayout()
                actions_layout.setContentsMargins(5, 2, 5, 2)
                actions_layout.setSpacing(5)

                # Toggle active button
                toggle_btn = QPushButton(_("Деактивировать") if user.is_active else _("Активировать"))
                toggle_btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #ff6b6b;
                        padding: 5px 10px;
                        font-size: 11px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #ff5555;
                    }
                """
                    if user.is_active
                    else """
                    QPushButton {
                        background-color: #4aff4a;
                        padding: 5px 10px;
                        font-size: 11px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #3aee3a;
                    }
                """
                )
                toggle_btn.clicked.connect(lambda checked, u=user: self.toggle_user_active(u.user_id))

                # Disable for admin user
                if user.username == "admin":
                    toggle_btn.setEnabled(False)
                    toggle_btn.setStyleSheet("background-color: rgba(60, 60, 60, 0.4);")

                actions_layout.addWidget(toggle_btn)
                actions_widget.setLayout(actions_layout)

                self.users_table.setCellWidget(row, 5, actions_widget)

        except Exception as e:
            self.logger.error(f"Failed to load users: {e}")
            QMessageBox.critical(
                self, _("Ошибка"), _("Не удалось загрузить список пользователей:\n{error}").format(error=str(e))
            )

    def _role_to_index(self, role: Role) -> int:
        """Convert Role to combo box index"""
        role_map = {Role.GUEST: 0, Role.USER: 1, Role.POWER_USER: 2, Role.ADMIN: 3}
        return role_map.get(role, 1)

    def _index_to_role(self, index: int) -> Role:
        """Convert combo box index to Role"""
        roles = [Role.GUEST, Role.USER, Role.POWER_USER, Role.ADMIN]
        return roles[index] if 0 <= index < len(roles) else Role.USER

    def change_user_role(self, user_id: str, new_role: Role):
        """Change user role"""
        try:
            user = self.storage.get_user_by_id(user_id)
            if not user:
                return

            # Prevent changing admin role
            if user.username == "admin":
                QMessageBox.warning(
                    self,
                    _("Ошибка"),
                    _("Нельзя изменить роль главного администратора"),
                )
                self.load_users()  # Reload to reset combo
                return

            # Confirm change
            reply = QMessageBox.question(
                self,
                _("Подтверждение"),
                _("Изменить роль пользователя '{username}' на '{role}'?").format(
                    username=user.username, role=new_role.value
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                user.role = new_role
                self.storage.save_user(user)
                self.logger.info(f"Changed role for user {user.username} to {new_role.value}")
                QMessageBox.information(self, _("Успех"), _("Роль пользователя успешно изменена"))
                self.user_updated.emit()

        except Exception as e:
            self.logger.error(f"Failed to change user role: {e}")
            QMessageBox.critical(
                self,
                _("Ошибка"),
                _("Не удалось изменить роль пользователя:\n{error}").format(error=str(e)),
            )

    def toggle_user_active(self, user_id: str):
        """Toggle user active status"""
        try:
            user = self.storage.get_user_by_id(user_id)
            if not user:
                return

            # Prevent deactivating admin
            if user.username == "admin":
                QMessageBox.warning(self, _("Ошибка"), _("Нельзя деактивировать главного администратора"))
                return

            # Confirm change
            action = _("деактивировать") if user.is_active else _("активировать")
            reply = QMessageBox.question(
                self,
                _("Подтверждение"),
                _("Вы уверены, что хотите {action} пользователя '{username}'?").format(
                    action=action, username=user.username
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                user.is_active = not user.is_active
                self.storage.save_user(user)
                self.logger.info(f"User {user.username} {'activated' if user.is_active else 'deactivated'}")
                self.load_users()  # Reload table
                self.user_updated.emit()

        except Exception as e:
            self.logger.error(f"Failed to toggle user active status: {e}")
            QMessageBox.critical(
                self,
                _("Ошибка"),
                _("Не удалось изменить статус пользователя:\n{error}").format(error=str(e)),
            )
