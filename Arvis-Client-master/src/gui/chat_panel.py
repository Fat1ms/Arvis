"""
Chat panel for Arvis application (restored clean version)
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from i18n import _
from src.audio.sound_effects import get_sound_effects


class MessageBubble(QFrame):
    """Message bubble widget for chat messages"""

    # Feedback signals
    message_liked = pyqtSignal(str)
    message_disliked = pyqtSignal(str)
    message_retry = pyqtSignal(str)
    message_voice_over = pyqtSignal(str)

    def __init__(self, message: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.message = message
        self.is_user = is_user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)

        # text
        msg = QLabel(self.message)
        msg.setWordWrap(True)
        try:
            # PyQt6: use explicit enum for text interaction flags
            msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        except Exception:
            pass

        # time
        time_label = QLabel(datetime.now().strftime("%H:%M"))
        try:
            time_label.setAlignment(Qt.AlignmentFlag.AlignRight if self.is_user else Qt.AlignmentFlag.AlignLeft)  # type: ignore[attr-defined]
        except Exception:
            pass

        layout.addWidget(msg)
        layout.addWidget(time_label)

        if not self.is_user:
            self._add_feedback(layout)

        self.setLayout(layout)

        if self.is_user:
            self.setStyleSheet(
                """
                QFrame {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #4a9eff, stop: 1 #1a5eff);
                    border-radius: 15px;
                    border-bottom-right-radius: 5px;
                }
                QLabel { color: white; background: transparent; font-size: 14px; }
                """
            )
            time_label.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.7);")
        else:
            self.setStyleSheet(
                """
                QFrame { background-color: rgba(60, 60, 60, 1); border-radius: 15px; border-bottom-left-radius: 5px; border: none; }
                QLabel { color: white; background: transparent; font-size: 14px; }
                """
            )
            time_label.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.5);")

    def _add_feedback(self, layout: QVBoxLayout) -> None:
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 8, 0, 5)
        buttons_layout.setSpacing(8)

        def mk_btn(svg: str, tip: str) -> QPushButton:
            b = QPushButton()
            b.setFixedSize(18, 18)
            try:
                b.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
            except Exception:
                pass
            b.setToolTip(_(tip))
            b.setStyleSheet(
                """
                QPushButton { border: none; background-color: rgba(255,255,255,0.05); border-radius: 9px; }
                QPushButton:hover { background-color: rgba(255,255,255,0.15); border: none; }
                QPushButton:pressed { background-color: rgba(255,255,255,0.25); border: none; }
                """
            )
            if Path(svg).exists():
                from PyQt6.QtSvg import QSvgRenderer

                def paint(ev):
                    QPushButton.paintEvent(b, ev)
                    p = QPainter(b)
                    try:
                        p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    except Exception:
                        try:
                            p.setRenderHint(QPainter.Antialiasing)  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    r = QSvgRenderer(svg)
                    rect = b.rect().adjusted(2, 2, -2, -2)
                    r.render(p, QRectF(rect))

                b.paintEvent = paint  # type: ignore[assignment]
            else:
                b.setText("?")
            return b

        voice_btn = mk_btn("UXUI/Button/Button_voice-over.svg", "Озвучить")
        like_btn = mk_btn("UXUI/Button/Button_like.svg", "Хороший ответ")
        dislike_btn = mk_btn("UXUI/Button/Button_dislike.svg", "Плохой ответ")
        retry_btn = mk_btn("UXUI/Button/Button_tryagen.svg", "Попробовать ещё раз")

        voice_btn.clicked.connect(lambda: self.message_voice_over.emit(self.message))
        like_btn.clicked.connect(lambda: self.message_liked.emit(self.message))
        dislike_btn.clicked.connect(lambda: self.message_disliked.emit(self.message))
        retry_btn.clicked.connect(lambda: self.message_retry.emit(self.message))

        for b in (voice_btn, like_btn, dislike_btn, retry_btn):
            buttons_layout.addWidget(b)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)


class TypingIndicator(QWidget):
    """Typing indicator animation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 30)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.dots = 0

    def start_animation(self):
        self.timer.start(500)
        self.show()

    def stop_animation(self):
        self.timer.stop()
        self.hide()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
        except Exception:
            try:
                p.setRenderHint(QPainter.Antialiasing)  # type: ignore[attr-defined]
            except Exception:
                pass
        p.setBrush(QColor(150, 150, 150))
        try:
            p.setPen(Qt.NoPen)  # type: ignore[attr-defined]
        except Exception:
            pass
        for i in range(3):
            opacity = 1.0 if i <= self.dots else 0.3
            p.setOpacity(opacity)
            p.drawEllipse(15 + i * 15, 12, 6, 6)
        self.dots = (self.dots + 1) % 4


class SvgButton(QPushButton):
    """Custom button with SVG icons"""

    def __init__(self, svg_normal: str, svg_active: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.svg_normal = svg_normal
        self.svg_active = svg_active or svg_normal
        self._force_active = False
        self.setFixedSize(54, 54)
        try:
            self.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        except Exception:
            pass
        self.setStyleSheet(
            """
            QPushButton { border: none; background: transparent; border-radius: 27px; }
            QPushButton:hover { background-color: transparent; }
            QPushButton:pressed { background-color: rgba(255,255,255,0.2); }
            """
        )

    def paintEvent(self, event):  # noqa: N802
        super().paintEvent(event)
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
        except Exception:
            try:
                p.setRenderHint(QPainter.Antialiasing)  # type: ignore[attr-defined]
            except Exception:
                pass
        use_active = self._force_active or self.isDown() or self.underMouse()
        svg_path = Path(self.svg_active if use_active else self.svg_normal)
        if svg_path.exists():
            from PyQt6.QtSvg import QSvgRenderer

            r = QSvgRenderer(str(svg_path))
            rect = self.rect().adjusted(8, 8, -8, -8)
            r.render(p, QRectF(rect))

    def setActive(self, active: bool):  # noqa: N802
        self._force_active = bool(active)
        self.update()


class ChatPanel(QWidget):
    """Main chat panel widget"""

    message_sent = pyqtSignal(str)
    microphone_clicked = pyqtSignal()
    clear_chat_requested = pyqtSignal()
    cancel_request = pyqtSignal()
    orb_toggle_requested = pyqtSignal()
    settings_clicked = pyqtSignal()
    history_clicked = pyqtSignal()
    user_management_clicked = pyqtSignal()  # Для администраторов

    message_liked = pyqtSignal(str)
    message_disliked = pyqtSignal(str)
    message_retry_requested = pyqtSignal(str)
    message_voice_over_requested = pyqtSignal(str)

    def __init__(self, config, parent=None, external_input_bar: bool = False):
        super().__init__(parent)
        self.config = config
        self.external_input_bar = external_input_bar
        self.arvis_core = None
        self.typing_indicator: Optional[TypingIndicator] = None
        self.typing_label: Optional[QLabel] = None
        self.streaming_started = False
        self._stream_container: Optional[QWidget] = None
        self._stream_bubble: Optional[MessageBubble] = None
        self.orb_button_enabled = True

        from utils.logger import ModuleLogger

        self.logger = ModuleLogger("ChatPanel")

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 10, 5, 10)

        # Chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        try:
            self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore[attr-defined]
            self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore[attr-defined]
        except Exception:
            pass

        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout()
        try:
            self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # type: ignore[attr-defined]
        except Exception:
            pass
        self.chat_layout.setSpacing(10)
        self.chat_content.setLayout(self.chat_layout)
        self.chat_scroll.setWidget(self.chat_content)

        # Input area
        input_frame = QFrame()
        self.input_frame = input_frame
        input_frame.setFixedHeight(74)
        input_frame.setStyleSheet(
            """
            QFrame { background-color: rgba(255,255,255,0.05); border-radius: 10px; padding: 5px; }
            """
        )

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(5, 10, 5, 10)
        try:
            input_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # type: ignore[attr-defined]
        except Exception:
            pass
        input_layout.setSpacing(8)

        # Text input
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText(_("Введите сообщение..."))
        self.message_input.returnPressed.connect(self.send_message)
        self.message_input.setFixedHeight(54)
        try:
            self.message_input.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)  # type: ignore[attr-defined]
        except Exception:
            pass
        self.message_input.setStyleSheet(
            """
            QLineEdit { border: 1px solid rgb(80,80,80); border-radius: 27px; padding: 10px 15px; font-size: 14px; background-color: rgb(50,50,50); }
            QLineEdit:focus { border: 2px solid #4a9eff; }
            """
        )

        # Buttons
        self.mic_button = SvgButton("UXUI/Button/Button_micr_norm.svg", "UXUI/Button/Button_micr_act.svg")
        self.mic_button.setFixedSize(58, 54)
        self.mic_button.clicked.connect(self.microphone_clicked.emit)
        self.mic_button.setToolTip(_("Голосовой ввод"))

        self.send_button = SvgButton("UXUI/Button/Button_send_norm.svg", "UXUI/Button/Button_send_act.svg")
        self.send_button.setFixedSize(58, 54)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setToolTip(_("Отправить сообщение"))

        self.cancel_button = QPushButton("❌ " + _("Отмена"))
        self.cancel_button.setFixedSize(80, 54)
        self.cancel_button.clicked.connect(self.cancel_request.emit)
        self.cancel_button.setToolTip(_("Отменить текущий запрос"))
        self.cancel_button.setStyleSheet(
            """
            QPushButton { background-color: rgba(200,50,50,0.8); color: white; border: none; border-radius: 27px; font-weight: bold; font-size: 12px; }
            QPushButton:hover { background-color: rgba(220,70,70,0.9); }
            QPushButton:pressed { background-color: rgba(180,30,30,0.9); }
            """
        )
        self.cancel_button.hide()

        self.clear_chat_button = SvgButton(
            "UXUI/Button/Button_cleanchat_norm.svg", "UXUI/Button/Button_cleanchat_act.svg"
        )
        self.clear_chat_button.setFixedSize(58, 54)
        self.clear_chat_button.clicked.connect(self.clear_chat_requested.emit)
        self.clear_chat_button.setToolTip(_("Очистить чат"))

        # Orb is always visible by design (no toggle button)
        self.orb_toggle_button = None

        self.settings_button = SvgButton("UXUI/Button/Button_setings_norm.svg", "UXUI/Button/Button_setings_act.svg")
        self.settings_button.setFixedSize(58, 54)
        self.settings_button.clicked.connect(self.settings_clicked.emit)
        self.settings_button.setToolTip(_("Настройки"))

        # Переключатель Live Mode
        self.live_mode_switch = LiveSwitch(self)
        self.live_mode_switch.setToolTip(_("Режим живого общения"))
        self.live_mode_switch.toggled.connect(self.handle_live_mode_toggle)

        # Кнопка управления пользователями (только для админов)
        self.user_mgmt_button = QPushButton("👥")
        self.user_mgmt_button.setFixedSize(58, 54)
        self.user_mgmt_button.clicked.connect(self.user_management_clicked.emit)
        self.user_mgmt_button.setToolTip(_("Управление пользователями"))
        self.user_mgmt_button.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(74, 158, 255, 0.2);
                border: 2px solid rgba(74, 158, 255, 0.4);
                border-radius: 8px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: rgba(74, 158, 255, 0.4);
                border: 2px solid rgba(74, 158, 255, 0.6);
            }
            QPushButton:pressed {
                background-color: rgba(74, 158, 255, 0.6);
            }
        """
        )
        self.user_mgmt_button.hide()  # Скрыта по умолчанию, показывается только для админов

        self.history_button = SvgButton("UXUI/Button/Button_chathist_norm.svg", "UXUI/Button/Button_chathist_act.svg")
        self.history_button.setFixedSize(58, 54)
        self.history_button.clicked.connect(self.history_clicked.emit)
        self.history_button.setToolTip(_("История разговоров"))

        # Layout order
        # Orb toggle button removed
        input_layout.addWidget(self.user_mgmt_button)  # Кнопка управления пользователями
        input_layout.addWidget(self.settings_button)
        input_layout.addWidget(self.history_button)
        input_layout.addWidget(self.message_input, 1)
        # Порядок кнопок справа внизу (справа налево): Отправить, Очистить, Голосовой ввод, Живое общение
        # Для QHBoxLayout это означает добавлять (слева направо): Живое общение, Голосовой ввод, Очистить, Отправить
        input_layout.addWidget(self.live_mode_switch)
        input_layout.addWidget(self.mic_button)
        input_layout.addWidget(self.clear_chat_button)
        input_layout.addWidget(self.send_button)
        input_layout.addWidget(self.cancel_button)
        input_frame.setLayout(input_layout)

        layout.addWidget(self.chat_scroll, 1)
        if not self.external_input_bar:
            layout.addWidget(input_frame)
        self.setLayout(layout)

        self.chat_scroll.setStyleSheet(
            """
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background-color: rgba(255,255,255,0.1); width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background-color: rgba(255,255,255,0.3); border-radius: 4px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background-color: rgba(255,255,255,0.5); }
            """
        )

    def get_input_frame(self):
        return getattr(self, "input_frame", None)

    def set_arvis_core(self, arvis_core):
        self.arvis_core = arvis_core
        if arvis_core:
            arvis_core.response_ready.connect(self.add_assistant_message)
            arvis_core.partial_response.connect(self.update_streaming_message)
            arvis_core.processing_started.connect(self.show_typing_indicator)
            arvis_core.processing_finished.connect(self.hide_typing_indicator)
            arvis_core.voice_message_recognized.connect(self.add_user_message)
            arvis_core.processing_started.connect(self.on_processing_started)
            arvis_core.processing_finished.connect(self.on_processing_finished)
            arvis_core.error_occurred.connect(self.on_processing_finished)
            # Инициализация Live-переключателя из конфига при привязке ядра
            try:
                live_initial = bool(self.config.get("modes.live_mode", False))
            except Exception:
                live_initial = False
            if hasattr(self, "live_mode_switch"):
                # setChecked эмитит toggled, прокинет состояние в ядро
                self.live_mode_switch.setChecked(live_initial)

    def on_processing_started(self):
        self.cancel_button.show()
        self.send_button.hide()

    def on_processing_finished(self):
        self.cancel_button.hide()
        self.send_button.show()

    def set_recording_active(self, is_active: bool):
        try:
            if hasattr(self, "mic_button") and hasattr(self.mic_button, "setActive"):
                self.mic_button.setActive(bool(is_active))
                self.mic_button.setToolTip(_("Микрофон активен") if is_active else _("Голосовой ввод"))
        except Exception:
            pass

    def send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return
        if hasattr(self, "_sending_message") and self._sending_message:
            self.logger.debug("Message sending already in progress, ignoring duplicate")
            return
        try:
            self._sending_message = True
            self._reset_streaming_state()
            self.message_input.clear()
            self.add_user_message(message)
            
            # Воспроизводим звук отправки сообщения
            try:
                get_sound_effects().play_message_sent()
            except Exception:
                pass
            
            QApplication.processEvents()
            QTimer.singleShot(1, lambda: self.message_sent.emit(message))
            QTimer.singleShot(100, lambda: setattr(self, "_sending_message", False))
        except Exception as e:
            self._sending_message = False
            self.logger.error(f"Error in send_message: {e}")
            raise

    def add_user_message(self, message: str):
        bubble = MessageBubble(message, is_user=True)
        self._apply_bubble_width(bubble)
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(50, 0, 0, 0)
        layout.addStretch()
        layout.addWidget(bubble)
        container.setLayout(layout)
        self.chat_layout.addWidget(container)
        self.scroll_to_bottom()

    def _connect_feedback_signals(self, bubble: MessageBubble):
        bubble.message_liked.connect(self.message_liked.emit)
        bubble.message_disliked.connect(self.message_disliked.emit)
        bubble.message_retry.connect(self.message_retry_requested.emit)
        bubble.message_voice_over.connect(self.message_voice_over_requested.emit)

    def _simulate_streaming(self, full_text: str):
        if not full_text:
            return
        simulate = self.config.get("ui.simulate_streaming", True)
        interval_ms = int(self.config.get("ui.stream_interval_ms", 16))
        chunk = int(self.config.get("ui.stream_chunk", 2))
        if not simulate:
            self.add_assistant_message(full_text)
            return
        if self.typing_label is not None:
            self.typing_label.setText(_("Arvis печатает…"))
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 50, 0)
        bubble = MessageBubble("", is_user=False)
        self._connect_feedback_signals(bubble)
        self._apply_bubble_width(bubble)
        layout.addWidget(bubble)
        layout.addStretch()
        container.setLayout(layout)
        self.chat_layout.addWidget(container)
        self.scroll_to_bottom()
        state = {"i": 0}

        def step():
            i = state["i"]
            next_i = min(i + chunk, len(full_text))
            b_layout = bubble.layout()
            if b_layout is None:
                return
            widget = b_layout.itemAt(0).widget()
            msg_label: Optional[QLabel] = widget if isinstance(widget, QLabel) else None
            if msg_label is not None:
                msg_label.setText(full_text[:next_i])
            bubble.message = full_text[:next_i]
            state["i"] = next_i
            self.scroll_to_bottom()
            if next_i >= len(full_text):
                bubble.message = full_text
                widget = bubble.layout().itemAt(1).widget()
                time_label: Optional[QLabel] = widget if isinstance(widget, QLabel) else None
                if time_label is not None:
                    time_label.setText(datetime.now().strftime("%H:%M"))
                timer.stop()

        timer = QTimer(self)
        timer.timeout.connect(step)
        timer.start(max(8, interval_ms))

    def update_streaming_message(self, text: str):
        if self._stream_bubble is None:
            if self.typing_label is not None and not self.streaming_started:
                self.typing_label.setText(_("Arvis печатает…"))
                self.streaming_started = True
            container = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 50, 0)
            bubble = MessageBubble("", is_user=False)
            self._connect_feedback_signals(bubble)
            self._apply_bubble_width(bubble)
            layout.addWidget(bubble)
            layout.addStretch()
            container.setLayout(layout)
            self.chat_layout.addWidget(container)
            self._stream_container = container
            self._stream_bubble = bubble
        bubble_obj = self._stream_bubble
        if bubble_obj is None:
            return
        bubble_obj.message = text
        b_layout = bubble_obj.layout()
        if b_layout is None:
            return
        widget = b_layout.itemAt(0).widget()
        msg_label: Optional[QLabel] = widget if isinstance(widget, QLabel) else None
        if msg_label is not None:
            msg_label.setText(text)
        
        widget = b_layout.itemAt(1).widget()
        time_label: Optional[QLabel] = widget if isinstance(widget, QLabel) else None
        if time_label is not None:
            time_label.setText(datetime.now().strftime("%H:%M"))
        if not hasattr(self, "_scroll_timer") or not self._scroll_timer.isActive():
            self._scroll_timer = QTimer()
            self._scroll_timer.setSingleShot(True)
            self._scroll_timer.timeout.connect(self.scroll_to_bottom)
            self._scroll_timer.start(50)

    def add_assistant_message(self, message: str):
        self.hide_typing_indicator()
        
        # Воспроизводим звук получения ответа
        try:
            get_sound_effects().play_message_received()
        except Exception:
            pass
        
        if self._stream_bubble is not None:
            self._stream_bubble.message = message
            b_layout = self._stream_bubble.layout()
            if b_layout is not None:
                widget = b_layout.itemAt(0).widget()
                msg_label: Optional[QLabel] = widget if isinstance(widget, QLabel) else None
                if msg_label is not None:
                    msg_label.setText(message)
                
                widget = b_layout.itemAt(1).widget()
                time_label: Optional[QLabel] = widget if isinstance(widget, QLabel) else None
                if time_label is not None:
                    time_label.setText(datetime.now().strftime("%H:%M"))
            if not hasattr(self._stream_bubble, "_signals_connected"):
                self._connect_feedback_signals(self._stream_bubble)
                self._stream_bubble._signals_connected = True  # type: ignore[attr-defined]
            self.scroll_to_bottom()
            self._stream_bubble = None
            self._stream_container = None
            self.streaming_started = False
            
            # АВТООЗВУЧКА В LIVE MODE
            self._auto_speak_if_live_mode(message)
            return
        if self.config.get("ui.simulate_streaming", True):
            self._simulate_streaming(message)
            # АВТООЗВУЧКА В LIVE MODE для симулированного стриминга
            self._auto_speak_if_live_mode(message)
            return
        bubble = MessageBubble(message, is_user=False)
        self._connect_feedback_signals(bubble)
        self._apply_bubble_width(bubble)
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 50, 0)
        layout.addWidget(bubble)
        layout.addStretch()
        container.setLayout(layout)
        self.chat_layout.addWidget(container)
        self.scroll_to_bottom()
        
        # АВТООЗВУЧКА В LIVE MODE для обычных сообщений
        self._auto_speak_if_live_mode(message)
    
    def _auto_speak_if_live_mode(self, message: str):
        """Автоматически озвучивает сообщение, если включён Live Mode."""
        try:
            # Проверяем, включён ли Live Mode
            if not hasattr(self, 'arvis_core') or not self.arvis_core:
                return
            
            if not getattr(self.arvis_core, 'live_mode', False):
                return
            
            # Проверяем наличие TTS engine
            if not hasattr(self.arvis_core, 'tts_engine') or not self.arvis_core.tts_engine:
                return
            
            # Озвучиваем сообщение
            self.arvis_core.tts_engine.speak(message)
        except Exception as e:
            # Игнорируем ошибки озвучивания, чтобы не прерывать работу
            pass

    def _reset_streaming_state(self):
        if self._stream_bubble is not None:
            b_layout = self._stream_bubble.layout()
            current_text = ""
            widget = b_layout.itemAt(0).widget()
            msg_label: Optional[QLabel] = widget if isinstance(widget, QLabel) else None
            if msg_label is not None:
                current_text = msg_label.text()
            if current_text.strip():
                widget = b_layout.itemAt(1).widget()
                time_label: Optional[QLabel] = widget if isinstance(widget, QLabel) else None
                if time_label is not None:
                    time_label.setText(datetime.now().strftime("%H:%M"))
            else:
                if self._stream_container:
                    self.chat_layout.removeWidget(self._stream_container)
                    self._stream_container.deleteLater()
            self._stream_bubble = None
            self._stream_container = None
        self.hide_typing_indicator()
        self.streaming_started = False

    def add_system_message(self, message: str):
        lbl = QLabel(message)
        try:
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore[attr-defined]
        except Exception:
            pass
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            """
            QLabel { color: rgba(255,255,255,0.6); font-style: italic; padding: 10px; background-color: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); }
            """
        )
        self.chat_layout.addWidget(lbl)
        self.scroll_to_bottom()

    def handle_live_mode_toggle(self, checked: bool):
        """Обработчик переключения Live Mode"""
        self.config.set("modes.live_mode", checked)
        self.logger.info(f"Live mode toggled: {'ON' if checked else 'OFF'}")
        if self.arvis_core:
            self.arvis_core.set_live_mode(checked)
        self.add_system_message(_("Режим живого общения {}").format(_("включен") if checked else _("выключен")))

    def show_typing_indicator(self):
        self.streaming_started = False
        if not self.typing_indicator:
            self.typing_indicator = TypingIndicator()
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 50, 0)
        self.typing_label = QLabel(_("Arvis думает…"))
        self.typing_label.setStyleSheet("color: rgba(255,255,255,0.8);")
        layout.addWidget(self.typing_label)
        layout.addWidget(self.typing_indicator)
        layout.addStretch()
        container.setLayout(layout)
        self.chat_layout.addWidget(container)
        self.typing_indicator.start_animation()
        self.scroll_to_bottom()

    def hide_typing_indicator(self):
        if self.typing_indicator:
            try:
                self.typing_indicator.stop_animation()
                # remove container that has typing_indicator
                for i in range(self.chat_layout.count()):
                    item = self.chat_layout.itemAt(i)
                    if not item or not item.widget():
                        continue
                    w = item.widget()
                    if w is None:
                        continue
                    # Безопасно получаем layout виджета
                    lay_getter = getattr(w, "layout", None)
                    lay = lay_getter() if callable(lay_getter) else None
                    if lay is None:
                        continue
                    # Убедимся, что у layout есть необходимые методы
                    if isinstance(lay, QLayout):
                        for j in range(lay.count()):
                            li = lay.itemAt(j)
                    else:
                        continue
                        if li and li.widget() == self.typing_indicator:
                            self.chat_layout.removeWidget(w)
                            # Безопасно удаляем виджет
                            if hasattr(w, "deleteLater"):
                                w.deleteLater()
                            self.typing_indicator = None
                            self.streaming_started = False
                            return
            except RuntimeError as e:
                self.logger.warning(f"TypingIndicator already removed: {e}")
                self.typing_indicator = None
                self.streaming_started = False

    def set_user_management_visible(self, visible: bool):
        """Show/hide user management button (Admin only)"""
        if hasattr(self, "user_mgmt_button"):
            if visible:
                self.user_mgmt_button.show()
            else:
                self.user_mgmt_button.hide()

    def clear_chat(self):
        # Сначала безопасно сбрасываем стриминг/typing, чтобы таймеры не трогали удалённые виджеты
        try:
            self._reset_streaming_state()
        except Exception:
            pass
        try:
            self.hide_typing_indicator()
        except Exception:
            pass

        for i in reversed(range(self.chat_layout.count())):
            item = self.chat_layout.itemAt(i)
            if not item:
                continue
            widget = item.widget()
            if widget:
                self.chat_layout.removeWidget(widget)
                widget.deleteLater()

        # Сброс ссылок (важно после массового удаления)
        self.typing_indicator = None
        self.typing_label = None
        self._stream_container = None
        self._stream_bubble = None
        self.streaming_started = False
        self.add_system_message(_("Чат очищен. Как дела?"))

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._update_all_bubble_widths()

    def _compute_bubble_max_width(self) -> int:
        try:
            vw = self.chat_scroll.viewport().width() if hasattr(self, "chat_scroll") and self.chat_scroll else self.width()
        except Exception:
            vw = self.width()
        # Чуть шире, чем было по умолчанию (решает проблему длинных сообщений)
        return max(280, int(vw * 0.78))

    def _apply_bubble_width(self, bubble: MessageBubble) -> None:
        try:
            max_w = self._compute_bubble_max_width()
            bubble.setMaximumWidth(max_w)
            lay = bubble.layout()
            if lay is not None:
                w0 = lay.itemAt(0).widget() if lay.count() > 0 else None
                msg_label: Optional[QLabel] = w0 if isinstance(w0, QLabel) else None
                if msg_label is not None:
                    msg_label.setMaximumWidth(max(100, max_w - 40))
        except Exception:
            pass

    def _update_all_bubble_widths(self) -> None:
        try:
            max_w = self._compute_bubble_max_width()
        except Exception:
            return

        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if w is None:
                continue
            for bubble in w.findChildren(MessageBubble):
                try:
                    bubble.setMaximumWidth(max_w)
                    lay = bubble.layout()
                    if lay is not None and lay.count() > 0:
                        w0 = lay.itemAt(0).widget()
                        msg_label: Optional[QLabel] = w0 if isinstance(w0, QLabel) else None
                        if msg_label is not None:
                            msg_label.setMaximumWidth(max(100, max_w - 40))
                except Exception:
                    continue

    def scroll_to_bottom(self):
        def scroll():
            if self.chat_scroll:
                sb = self.chat_scroll.verticalScrollBar()
                if sb:
                    sb.setValue(sb.maximum())

        QTimer.singleShot(100, scroll)

    def handle_orb_toggle_click(self):
        if getattr(self, "orb_toggle_button", None) is None:
            return
        if not self.orb_button_enabled:
            return
        self.orb_button_enabled = False
        self.orb_toggle_button.setEnabled(False)
        self.orb_toggle_requested.emit()
        QTimer.singleShot(1000, self._enable_orb_button)

    def _enable_orb_button(self):
        if getattr(self, "orb_toggle_button", None) is None:
            self.orb_button_enabled = True
            return
        self.orb_button_enabled = True
        self.orb_toggle_button.setEnabled(True)


class LiveSwitch(QWidget):
    """Переключатель для Live Mode с улучшенным дизайном"""
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 54)
        self._checked = False
        self._pulse_value = 0
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._update_pulse)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.toggled.emit(checked)
            
            # Запускаем/останавливаем анимацию пульсации
            if checked:
                self._animation_timer.start(50)  # 50ms для плавной пульсации
            else:
                self._animation_timer.stop()
                self._pulse_value = 0
            
            self.update()

    def _update_pulse(self):
        """Обновление пульсации"""
        self._pulse_value += 0.1
        if self._pulse_value >= 6.28:  # 2*pi
            self._pulse_value = 0
        self.update()

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Основная кнопка
        btn_rect = self.rect().adjusted(5, 7, -5, -7)
        
        if self._checked:
            # Активное состояние - синий с пульсацией
            import math
            pulse_offset = int(3 * math.sin(self._pulse_value))
            glow_rect = btn_rect.adjusted(-pulse_offset, -pulse_offset, pulse_offset, pulse_offset)
            
            # Свечение
            glow_color = QColor("#4a9eff")
            glow_color.setAlpha(80 + int(40 * math.sin(self._pulse_value)))
            p.setBrush(glow_color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(glow_rect, 8, 8)
            
            # Основная кнопка
            bg_color = QColor("#4a9eff")
        else:
            # Неактивное состояние - серый
            bg_color = QColor(70, 70, 70)
        
        p.setBrush(bg_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(btn_rect, 6, 6)

        # Иконка микрофона (упрощённая)
        p.setPen(QPen(QColor(255, 255, 255), 2))
        
        # Центр для иконки
        center_x = btn_rect.center().x()
        center_y = btn_rect.center().y() - 3
        
        # Капсула микрофона
        mic_rect = QRect(center_x - 4, center_y - 8, 8, 12)
        p.drawRoundedRect(mic_rect, 3, 3)
        
        # Подставка
        p.drawLine(center_x, center_y + 5, center_x, center_y + 10)
        p.drawLine(center_x - 5, center_y + 10, center_x + 5, center_y + 10)
        
        # Текст "LIVE" внизу
        if self._checked:
            p.setPen(QColor(255, 255, 255))
            font = p.font()
            font.setBold(True)
            font.setPointSize(7)
            p.setFont(font)
            text_rect = QRect(btn_rect.x(), btn_rect.bottom() - 12, btn_rect.width(), 12)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "LIVE")
