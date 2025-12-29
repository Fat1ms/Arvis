"""
Chat History Dialog for Arvis
Displays conversation history with search, export, and navigation
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from i18n import _
from utils.logger import ModuleLogger


class HistoryMessageItem(QFrame):
    """Single message item in history view"""

    def __init__(self, message_data: dict, parent=None):
        super().__init__(parent)
        self.message_data = message_data
        self._build_ui()

    def _build_ui(self):
        """Build message item UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header: role + timestamp
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        role = self.message_data.get("role", "unknown")
        is_user = role == "user"

        role_label = QLabel(_("👤 Вы") if is_user else _("🤖 Arvis"))
        role_label.setStyleSheet(
            f"""
            QLabel {{
                color: {'#4a9eff' if is_user else '#8bc34a'};
                font-weight: bold;
                font-size: 13px;
                background: transparent;
            }}
        """
        )

        timestamp = self.message_data.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            time_str = timestamp

        time_label = QLabel(time_str)
        time_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
                background: transparent;
            }
        """
        )

        header_layout.addWidget(role_label)
        header_layout.addWidget(time_label)

        # Metadata (source, model if available)
        metadata = self.message_data.get("metadata", {}) or {}
        meta_label = None
        if metadata:
            source = metadata.get("source", "")
            model = metadata.get("model", "")
            meta_text = []
            if source:
                meta_text.append(f"📍 {source}")
            if model:
                meta_text.append(f"🧠 {model}")
            if meta_text:
                meta_label = QLabel(" • ".join(meta_text))
                meta_label.setStyleSheet(
                    """
                    QLabel {
                        color: rgba(255, 255, 255, 0.4);
                        font-size: 10px;
                        font-style: italic;
                        background: transparent;
                    }
                """
                )

        feedback_value = self.message_data.get("feedback") or metadata.get("feedback")
        if meta_label:
            header_layout.addWidget(meta_label)

        if feedback_value:
            if feedback_value == "positive":
                feedback_text = _("👍 Хороший ответ")
                color = "#8bc34a"
                background = "rgba(139, 195, 74, 0.15)"
            else:
                feedback_text = _("👎 Плохой ответ")
                color = "#f44336"
                background = "rgba(244, 67, 54, 0.15)"

            feedback_label = QLabel(feedback_text)
            feedback_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {color};
                    font-size: 11px;
                    font-weight: bold;
                    background-color: {background};
                    border-radius: 6px;
                    padding: 3px 8px;
                }}
            """
            )
            header_layout.addWidget(feedback_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Message content
        content = self.message_data.get("content", "")
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        # PyQt6 requires using the explicit TextInteractionFlag enum
        # This enables text selection with the mouse in the history view
        try:
            content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        except Exception:
            # Fallback for safety on older bindings
            pass
        content_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                padding: 6px;
                background: transparent;
            }
        """
        )

        layout.addWidget(content_label)

        self.setLayout(layout)

        # Styling
        if is_user:
            self.setStyleSheet(
                """
                QFrame {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0 rgba(74, 158, 255, 0.15),
                        stop: 1 rgba(26, 94, 255, 0.15));
                    border-radius: 8px;
                    border-left: 3px solid #4a9eff;
                    margin: 2px 0px;
                }
            """
            )
        else:
            self.setStyleSheet(
                """
                QFrame {
                    background-color: rgba(60, 60, 60, 0.5);
                    border-radius: 8px;
                    border-left: 3px solid #8bc34a;
                    margin: 2px 0px;
                }
            """
            )


class ChatHistoryDialog(QDialog):
    """Dialog for viewing and managing conversation history"""

    # Signals
    history_cleared = pyqtSignal()

    def __init__(self, conversation_history_manager, parent=None):
        super().__init__(parent)
        self.logger = ModuleLogger("ChatHistoryDialog")
        self.history_manager = conversation_history_manager
        self.filtered_messages = []
        self.init_ui()
        self.load_history()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(_("История разговоров"))
        self.setFixedSize(800, 600)

        # Frameless window with custom title bar (matching main window style)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(10)

        # Header with stats
        stats_layout = self._create_stats_section()
        content_layout.addLayout(stats_layout)

        # Search bar
        search_layout = self._create_search_bar()
        content_layout.addLayout(search_layout)

        # Messages scroll area
        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_scroll.setStyleSheet(
            """
            QScrollArea {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                background-color: rgba(30, 30, 30, 0.8);
            }
            QScrollBar:vertical {
                background-color: rgba(255, 255, 255, 0.05);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """
        )

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout()
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(8)
        self.messages_container.setLayout(self.messages_layout)
        self.messages_scroll.setWidget(self.messages_container)

        content_layout.addWidget(self.messages_scroll, 1)

        # Bottom action buttons
        actions_layout = self._create_action_buttons()
        content_layout.addLayout(actions_layout)

        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        self.setLayout(main_layout)

        # Styling
        self.setStyleSheet(
            """
            QDialog {
                background-color: rgb(43, 43, 43);
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: rgba(60, 60, 60, 0.8);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(74, 158, 255, 0.6);
            }
            QPushButton {
                background-color: rgba(74, 158, 255, 0.8);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(74, 158, 255, 1.0);
            }
            QPushButton:pressed {
                background-color: rgba(26, 94, 255, 1.0);
            }
            QPushButton:disabled {
                background-color: rgba(60, 60, 60, 0.5);
                color: rgba(255, 255, 255, 0.3);
            }
        """
        )

    def _create_title_bar(self) -> QWidget:
        """Create custom title bar"""
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet(
            """
            QWidget {
                background-color: rgb(43, 43, 43);
            }
        """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(10)

        # Icon + Title
        title_label = QLabel("📜 " + _("История разговоров"))
        title_label.setStyleSheet(
            """
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
        """
        )

        layout.addWidget(title_label)
        layout.addStretch()

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: rgba(255, 255, 255, 0.7);
                font-size: 20px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(200, 50, 50, 0.8);
                color: white;
            }
            QPushButton:pressed {
                background-color: rgba(180, 30, 30, 1.0);
            }
        """
        )
        close_btn.clicked.connect(self.close)

        layout.addWidget(close_btn)
        title_bar.setLayout(layout)

        # Make title bar draggable
        title_bar.mousePressEvent = self._title_bar_mouse_press
        title_bar.mouseMoveEvent = self._title_bar_mouse_move

        return title_bar

    def _title_bar_mouse_press(self, event):
        """Handle title bar mouse press for dragging"""
        # PyQt6: use Qt.MouseButton.LeftButton
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _title_bar_mouse_move(self, event):
        """Handle title bar mouse move for dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "drag_pos"):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def _create_stats_section(self) -> QHBoxLayout:
        """Create statistics section"""
        layout = QHBoxLayout()
        layout.setSpacing(15)

        stats = self.history_manager.get_statistics()

        def make_stat_label(icon: str, text: str, value: str) -> QLabel:
            label = QLabel(f"{icon} {text}: <b>{value}</b>")
            label.setStyleSheet(
                """
                QLabel {
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 12px;
                    padding: 6px 12px;
                    background-color: rgba(74, 158, 255, 0.15);
                    border-radius: 6px;
                }
            """
            )
            return label

        total_label = make_stat_label("💬", _("Всего"), str(stats.get("total_messages", 0)))
        user_label = make_stat_label("👤", _("От вас"), str(stats.get("user_messages", 0)))
        arvis_label = make_stat_label("🤖", _("От Arvis"), str(stats.get("assistant_messages", 0)))
        positive_label = None
        negative_label = None

        if stats.get("positive_feedback", 0):
            positive_label = make_stat_label("👍", _("Положительных оценок"), str(stats.get("positive_feedback", 0)))
        if stats.get("negative_feedback", 0):
            negative_label = make_stat_label("👎", _("Отрицательных оценок"), str(stats.get("negative_feedback", 0)))

        layout.addWidget(total_label)
        layout.addWidget(user_label)
        layout.addWidget(arvis_label)
        if positive_label:
            layout.addWidget(positive_label)
        if negative_label:
            layout.addWidget(negative_label)
        layout.addStretch()

        return layout

    def _create_search_bar(self) -> QHBoxLayout:
        """Create search bar"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_("🔍 Поиск по истории..."))
        self.search_input.textChanged.connect(self.on_search_changed)

        self.search_clear_btn = QPushButton("✕")
        self.search_clear_btn.setFixedSize(36, 36)
        self.search_clear_btn.clicked.connect(self.clear_search)
        self.search_clear_btn.setToolTip(_("Очистить поиск"))

        layout.addWidget(self.search_input, 1)
        layout.addWidget(self.search_clear_btn)

        return layout

    def _create_action_buttons(self) -> QHBoxLayout:
        """Create action buttons"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.export_btn = QPushButton("📥 " + _("Экспорт"))
        self.export_btn.clicked.connect(self.export_history)
        self.export_btn.setToolTip(_("Экспортировать историю в текстовый файл"))

        self.clear_btn = QPushButton("🗑️ " + _("Очистить историю"))
        self.clear_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(200, 50, 50, 0.7);
            }
            QPushButton:hover {
                background-color: rgba(220, 70, 70, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(180, 30, 30, 1.0);
            }
        """
        )
        self.clear_btn.clicked.connect(self.clear_history)
        self.clear_btn.setToolTip(_("Очистить всю историю (с архивацией)"))

        self.close_btn = QPushButton(_("Закрыть"))
        self.close_btn.clicked.connect(self.close)

        layout.addWidget(self.export_btn)
        layout.addWidget(self.clear_btn)
        layout.addStretch()
        layout.addWidget(self.close_btn)

        return layout

    def load_history(self):
        """Load and display history"""
        try:
            messages = self.history_manager.get_all()
            self.filtered_messages = messages
            self.display_messages(messages)
        except Exception as e:
            self.logger.error(f"Failed to load history: {e}")
            self.show_error_message(_("Ошибка загрузки истории"))

    def display_messages(self, messages: list):
        """Display messages in scroll area"""
        # Clear existing items
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not messages:
            empty_label = QLabel(_("📭 История пуста"))
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(
                """
                QLabel {
                    color: rgba(255, 255, 255, 0.4);
                    font-size: 16px;
                    font-style: italic;
                    padding: 40px;
                }
            """
            )
            self.messages_layout.addWidget(empty_label)
            self.messages_layout.addStretch()
            return

        # Add message items
        for msg in messages:
            item = HistoryMessageItem(msg)
            self.messages_layout.addWidget(item)

        self.messages_layout.addStretch()

        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        """Scroll to bottom of messages"""
        scrollbar = self.messages_scroll.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def on_search_changed(self, text: str):
        """Handle search text change"""
        if not text.strip():
            self.display_messages(self.history_manager.get_all())
            return

        try:
            results = self.history_manager.search(text, limit=100)
            self.filtered_messages = results
            self.display_messages(results)

            if not results:
                self.show_info_message(_("Ничего не найдено по запросу: {query}").format(query=text))
        except Exception as e:
            self.logger.error(f"Search failed: {e}")

    def clear_search(self):
        """Clear search input"""
        self.search_input.clear()

    def export_history(self):
        """Export history to text file"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            default_name = f"arvis_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file_path, _selected_filter = QFileDialog.getSaveFileName(
                self, _("Экспортировать историю"), default_name, _("Текстовые файлы (*.txt);;Все файлы (*)")
            )

            if file_path:
                self.history_manager.export_to_text(Path(file_path))
                export_text = _("История успешно экспортирована в:\n{path}").format(path=file_path)
                QMessageBox.information(self, _("Экспорт завершён"), export_text)
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            error_text = _("Не удалось экспортировать историю:\n{error}").format(error=e)
            QMessageBox.critical(self, _("Ошибка экспорта"), error_text)

    def clear_history(self):
        """Clear conversation history with confirmation"""
        archive_path = str(getattr(self.history_manager, "archive_dir", "data/conversation_archive/"))
        confirm_text = _(
            "Вы уверены, что хотите очистить всю историю?\n\nТекущая сессия будет архивирована в:\n{path}"
        ).format(path=archive_path)
        reply = QMessageBox.question(
            self, _("Подтверждение"), confirm_text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.history_manager.clear()
                self.history_cleared.emit()
                self.load_history()  # Reload (should be empty now)
                QMessageBox.information(self, _("История очищена"), _("История успешно очищена и архивирована"))
            except Exception as e:
                self.logger.error(f"Clear history failed: {e}")
                error_text = _("Не удалось очистить историю:\n{error}").format(error=e)
                QMessageBox.critical(self, _("Ошибка"), error_text)

    def show_error_message(self, message: str):
        """Show error message in messages area"""
        error_label = QLabel(f"❌ {message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 100, 100, 0.9);
                font-size: 14px;
                padding: 20px;
            }
        """
        )
        self.messages_layout.addWidget(error_label)

    def show_info_message(self, message: str):
        """Show info message"""
        # Temporarily show message at top
        pass  # Could implement as a toast notification
