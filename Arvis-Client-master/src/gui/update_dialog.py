"""
Update Dialog for Arvis
Диалог обновления приложения
"""

import logging
from pathlib import Path

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.update_checker import UpdateChecker

logger = logging.getLogger(__name__)


class UpdateCheckThread(QThread):
    """Thread для проверки обновлений в фоне"""

    update_available = pyqtSignal(dict)
    check_completed = pyqtSignal(bool)

    def __init__(self, update_checker: UpdateChecker):
        super().__init__()
        self.update_checker = update_checker

    def run(self):
        """Проверка обновлений"""
        try:
            release_info = self.update_checker.check_for_updates()
            if release_info:
                self.update_available.emit(release_info)
                self.check_completed.emit(True)
            else:
                self.check_completed.emit(False)
        except Exception as e:
            logger.error(f"Ошибка проверки обновлений: {e}")
            self.check_completed.emit(False)


class UpdateNotificationDialog(QDialog):
    """Уведомление о доступном обновлении"""

    def __init__(self, update_info: dict, update_checker: UpdateChecker, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.update_checker = update_checker
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Доступно обновление")
        self.setFixedSize(500, 400)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # Content
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Icon and title
        title_label = QLabel("🔔 Доступно обновление Arvis")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        content_layout.addWidget(title_label)

        # Version info
        current_ver = self.update_checker.current_version
        new_ver = self.update_info.get("version", "Unknown")
        version_label = QLabel(f"Текущая версия: {current_ver}\nНовая версия: {new_ver}")
        version_label.setStyleSheet("color: #aaa; margin-bottom: 10px;")
        content_layout.addWidget(version_label)

        # Release notes
        notes_label = QLabel("Что нового:")
        notes_label.setStyleSheet("font-weight: bold; color: white;")
        content_layout.addWidget(notes_label)

        notes_text = QTextEdit()
        notes_text.setReadOnly(True)
        notes_text.setMinimumHeight(150)
        body = self.update_info.get("body", "Нет описания изменений")
        # Limit length
        if len(body) > 500:
            body = body[:500] + "..."
        notes_text.setPlainText(body)
        content_layout.addWidget(notes_text)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        later_button = QPushButton("Напомнить позже")
        later_button.clicked.connect(self.reject)
        buttons_layout.addWidget(later_button)

        update_button = QPushButton("Обновить сейчас")
        update_button.clicked.connect(self.accept)
        buttons_layout.addWidget(update_button)

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
            QTextEdit {
                background-color: rgb(50, 50, 50);
                border: 1px solid rgb(70, 70, 70);
                border-radius: 5px;
                padding: 8px;
                color: white;
            }
            QPushButton {
                background-color: rgb(60, 60, 60);
                color: white;
                border: 1px solid rgb(80, 80, 80);
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: rgb(70, 70, 70);
            }
            QPushButton:pressed {
                background-color: rgb(50, 50, 50);
            }
        """
        )

    def _create_title_bar(self) -> QWidget:
        """Создание заголовка"""
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

        title_label = QLabel("Обновление")
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px; border: none;")
        layout.addWidget(title_label)
        layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgb(43, 43, 43);
                color: rgb(180, 180, 180);
                border: none;
                font-size: 20px;
                font-weight: bold;
                width: 30px;
                height: 30px;
                min-width: 30px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgb(232, 17, 35);
                color: white;
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


class UpdateWorker(QThread):
    """Worker thread для операций обновления"""

    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    update_completed = pyqtSignal(bool, str)

    def __init__(self, update_checker: UpdateChecker, release_info: dict):
        super().__init__()
        self.update_checker = update_checker
        self.release_info = release_info
        self.update_archive = None

    def run(self):
        """Выполнение процесса обновления"""
        try:
            # Скачивание
            self.status_changed.emit("Скачивание обновления...")
            self.update_archive = self.update_checker.download_update(
                self.release_info, progress_callback=self.progress_changed.emit
            )

            if not self.update_archive:
                self.update_completed.emit(False, "Не удалось скачать обновление")
                return

            self.progress_changed.emit(100)

            # Применение обновления
            self.status_changed.emit("Установка обновления...")
            success = self.update_checker.apply_update(self.update_archive)

            if success:
                self.update_completed.emit(True, "Обновление установлено успешно!")
            else:
                self.update_completed.emit(False, "Ошибка установки обновления")

        except Exception as e:
            logger.error(f"Ошибка в worker обновления: {e}")
            self.update_completed.emit(False, str(e))


class UpdateDialog(QDialog):
    """Диалог управления обновлениями"""

    update_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.update_checker = UpdateChecker()
        self.release_info = None
        self.worker = None
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Обновление Arvis")
        self.setFixedSize(600, 500)
        self.setModal(True)

        # Без стандартного заголовка
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)  # type: ignore[attr-defined]

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        self.create_title_bar()
        main_layout.addWidget(self.title_bar)

        # Content
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Status label
        self.status_label = QLabel("Проверка обновлений...")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        content_layout.addWidget(self.status_label)

        # Version info
        self.version_label = QLabel()
        self.version_label.setStyleSheet("color: #aaa;")
        content_layout.addWidget(self.version_label)

        # Release notes
        notes_label = QLabel("Что нового:")
        notes_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px;")
        content_layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setMinimumHeight(200)
        content_layout.addWidget(self.notes_text)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        content_layout.addWidget(self.progress_bar)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.check_button = QPushButton("Проверить обновления")
        self.check_button.clicked.connect(self.check_updates)
        buttons_layout.addWidget(self.check_button)

        self.install_button = QPushButton("Установить обновление")
        self.install_button.clicked.connect(self.install_update)
        self.install_button.setEnabled(False)
        buttons_layout.addWidget(self.install_button)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_button)

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
            QTextEdit {
                background-color: rgb(50, 50, 50);
                border: 1px solid rgb(70, 70, 70);
                border-radius: 5px;
                padding: 8px;
                color: white;
            }
            QProgressBar {
                border: 1px solid rgb(70, 70, 70);
                border-radius: 5px;
                text-align: center;
                background-color: rgb(50, 50, 50);
                color: white;
            }
            QProgressBar::chunk {
                background-color: rgb(0, 120, 215);
                border-radius: 4px;
            }
            QPushButton {
                background-color: rgb(60, 60, 60);
                color: white;
                border: 1px solid rgb(80, 80, 80);
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: rgb(70, 70, 70);
            }
            QPushButton:pressed {
                background-color: rgb(50, 50, 50);
            }
            QPushButton:disabled {
                background-color: rgb(40, 40, 40);
                color: rgb(100, 100, 100);
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

        title_label = QLabel("Обновление Arvis")
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

        # Draggable title bar
        self.title_bar.mousePressEvent = self.title_bar_mouse_press  # type: ignore[assignment]
        self.title_bar.mouseMoveEvent = self.title_bar_mouse_move  # type: ignore[assignment]

    def title_bar_mouse_press(self, event):
        """Обработка нажатия мыши на заголовке"""
        if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        """Обработка движения мыши на заголовке"""
        if event.buttons() == Qt.LeftButton and hasattr(self, "drag_pos"):  # type: ignore[attr-defined]
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def check_updates(self):
        """Проверка наличия обновлений"""
        self.status_label.setText("Проверка обновлений...")
        self.check_button.setEnabled(False)
        self.notes_text.clear()

        try:
            self.release_info = self.update_checker.check_for_updates()

            if self.release_info:
                version = self.release_info.get("version", "Unknown")
                self.status_label.setText(f"Доступно обновление!")
                self.version_label.setText(
                    f"Текущая версия: {self.update_checker.current_version} → Новая версия: {version}"
                )

                # Release notes
                body = self.release_info.get("body", "Нет описания изменений")
                self.notes_text.setMarkdown(body)

                self.install_button.setEnabled(True)
            else:
                self.status_label.setText("Вы используете последнюю версию")
                self.version_label.setText(f"Версия: {self.update_checker.current_version}")
                self.notes_text.setPlainText("Обновления не найдены")
                self.install_button.setEnabled(False)

        except Exception as e:
            logger.error(f"Ошибка проверки обновлений: {e}")
            self.status_label.setText("Ошибка проверки обновлений")
            self.notes_text.setPlainText(f"Ошибка: {str(e)}")

        finally:
            self.check_button.setEnabled(True)

    def install_update(self):
        """Установка обновления"""
        if not self.release_info:
            QMessageBox.warning(self, "Ошибка", "Информация об обновлении недоступна")
            return

        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Установить обновление?\n\n"
            "Приложение будет перезапущено после установки.\n"
            "Резервная копия текущей версии будет создана автоматически.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Отключаем кнопки
        self.check_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.close_button.setEnabled(False)

        # Показываем прогресс бар
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Запускаем worker
        self.worker = UpdateWorker(self.update_checker, self.release_info)
        self.worker.progress_changed.connect(self.on_progress_changed)
        self.worker.status_changed.connect(self.on_status_changed)
        self.worker.update_completed.connect(self.on_update_completed)
        self.worker.start()

    def on_progress_changed(self, value: int):
        """Обновление прогресс бара"""
        self.progress_bar.setValue(value)

    def on_status_changed(self, status: str):
        """Обновление статуса"""
        self.status_label.setText(status)

    def on_update_completed(self, success: bool, message: str):
        """Завершение обновления"""
        self.progress_bar.setVisible(False)
        self.close_button.setEnabled(True)

        if success:
            QMessageBox.information(
                self,
                "Успех",
                f"{message}\n\nПриложение будет перезапущено.",
            )
            self.update_applied.emit()
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось установить обновление:\n{message}",
            )
            self.check_button.setEnabled(True)
            self.install_button.setEnabled(True)

    def showEvent(self, event):
        """Автоматическая проверка при открытии"""
        super().showEvent(event)
        # Проверяем обновления при первом показе
        if not self.release_info:
            self.check_updates()
