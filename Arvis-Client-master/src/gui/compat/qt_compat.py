"""
Qt Compatibility Layer (PyQt5 ↔ PyQt6)
Слой совместимости между PyQt5 и PyQt6

Использование:
    from src.gui.compat.qt_compat import (
        QMainWindow, QPushButton, Qt,
        QtCore, QtWidgets, QtGui,
        USING_PYQT6, QT_VERSION
    )

Автоматически определяет установленную версию
и предоставляет единый API.

Язык документации: Русский + English
"""

import sys
from typing import Any

# ============================================================================
# Определить какой Qt установлен и импортировать
# ============================================================================

_USING_PYQT6 = False
_QT_VERSION = None
_IMPORT_ERROR = None

try:
    # Попытка импортировать PyQt6
    from PyQt6 import QtCore, QtWidgets, QtGui
    _USING_PYQT6 = True
    _QT_VERSION = 6
    _IMPORT_ERROR = None
except ImportError as e1:
    try:
        # Fallback на PyQt5
        from PyQt5 import QtCore, QtWidgets, QtGui
        _USING_PYQT6 = False
        _QT_VERSION = 5
        _IMPORT_ERROR = None
    except ImportError as e2:
        _IMPORT_ERROR = f"Neither PyQt6 nor PyQt5 found: {e2}"
        raise ImportError(_IMPORT_ERROR)

# Логирование выбранной версии
print(f"[Qt Compat] Using PyQt{_QT_VERSION}")

# ============================================================================
# Экспортировать основные модули
# ============================================================================

USING_PYQT6 = _USING_PYQT6
QT_VERSION = _QT_VERSION

# Основные классы Qt
if _USING_PYQT6:
    from PyQt6.QtCore import (
        Qt, QTimer, Signal, Slot, QThread, QObject,
        QRect, QSize, QPoint, QEvent, QTimer,
        pyqtSignal, pyqtSlot,
    )
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget,
        QPushButton, QLabel, QLineEdit,
        QVBoxLayout, QHBoxLayout, QGridLayout,
        QScrollArea, QMessageBox, QDialog,
        QComboBox, QSpinBox, QCheckBox,
        QTextEdit, QPlainTextEdit, QStatusBar,
        QMenuBar, QMenu, QFileDialog,
        QProgressBar, QSlider, QDial,
    )
    from PyQt6.QtGui import (
        QIcon, QColor, QFont, QPixmap,
        QPainter, QPen, QBrush, QImage,
    )
    from PyQt6.QtCore import QTimer as QtTimer
else:
    from PyQt6.QtCore import (
        Qt, QTimer, Signal, Slot, QThread, QObject,
        QRect, QSize, QPoint, QEvent, QTimer,
        pyqtSignal, pyqtSlot,
    )
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget,
        QPushButton, QLabel, QLineEdit,
        QVBoxLayout, QHBoxLayout, QGridLayout,
        QScrollArea, QMessageBox, QDialog,
        QComboBox, QSpinBox, QCheckBox,
        QTextEdit, QPlainTextEdit, QStatusBar,
        QMenuBar, QMenu, QFileDialog,
        QProgressBar, QSlider, QDial,
    )
    from PyQt6.QtGui import (
        QIcon, QColor, QFont, QPixmap,
        QPainter, QPen, QBrush, QImage,
    )
    from PyQt6.QtCore import QTimer as QtTimer

# ============================================================================
# Совместимые перечисления (Enums)
# ============================================================================

class QtAlignmentFlag:
    """
    Совместимые флаги выравнивания.
    
    Использование:
        button.setAlignment(QtAlignmentFlag.AlignCenter)
    """
    
    @staticmethod
    def _get_align(name: str) -> Any:
        """Получить флаг выравнивания."""
        if _USING_PYQT6:
            return getattr(Qt.AlignmentFlag, f"Align{name}")
        else:
            return getattr(Qt, f"Align{name}")
    
    AlignLeft = property(lambda self: self._get_align("Left"))
    AlignRight = property(lambda self: self._get_align("Right"))
    AlignCenter = property(lambda self: self._get_align("Center"))
    AlignTop = property(lambda self: self._get_align("Top"))
    AlignBottom = property(lambda self: self._get_align("Bottom"))
    AlignVCenter = property(lambda self: self._get_align("VCenter"))
    AlignHCenter = property(lambda self: self._get_align("HCenter"))

# Проще - функции вместо класса
def align_left() -> Any:
    """Получить флаг выравнивания влево."""
    if _USING_PYQT6:
        return Qt.AlignmentFlag.AlignLeft
    return Qt.AlignmentFlag.AlignLeft

def align_right() -> Any:
    """Получить флаг выравнивания вправо."""
    if _USING_PYQT6:
        return Qt.AlignmentFlag.AlignRight
    return Qt.AlignmentFlag.AlignRight

def align_center() -> Any:
    """Получить флаг выравнивания в центр."""
    if _USING_PYQT6:
        return Qt.AlignmentFlag.AlignCenter
    return Qt.AlignmentFlag.AlignCenter

def align_v_center() -> Any:
    """Получить флаг вертикального выравнивания в центр."""
    if _USING_PYQT6:
        return Qt.AlignmentFlag.AlignVCenter
    return Qt.AlignmentFlag.AlignVCenter

def align_h_center() -> Any:
    """Получить флаг горизонтального выравнивания в центр."""
    if _USING_PYQT6:
        return Qt.AlignmentFlag.AlignHCenter
    return Qt.AlignmentFlag.AlignHCenter

# ============================================================================
# Совместимые атрибуты окна (Widget Attributes)
# ============================================================================

def wa_translucent_background() -> Any:
    """Получить флаг прозрачного фона окна."""
    if _USING_PYQT6:
        return Qt.WidgetAttribute.WA_TranslucentBackground
    return Qt.WA_TranslucentBackground

def wa_no_system_background() -> Any:
    """Получить флаг отсутствия системного фона."""
    if _USING_PYQT6:
        return Qt.WidgetAttribute.WA_NoSystemBackground
    return Qt.WA_NoSystemBackground

def wa_stay_on_top() -> Any:
    """Получить флаг окна сверху."""
    if _USING_PYQT6:
        return Qt.WidgetAttribute.WA_StayOnTop
    return Qt.WA_StayOnTop

# ============================================================================
# Совместимые события (Events)
# ============================================================================

def key_press_event() -> Any:
    """Получить тип события нажатия клавиши."""
    if _USING_PYQT6:
        return QEvent.Type.KeyPress
    return QEvent.KeyPress

def mouse_press_event() -> Any:
    """Получить тип события нажатия мыши."""
    if _USING_PYQT6:
        return QEvent.Type.MouseButtonPress
    return QEvent.MouseButtonPress

def close_event() -> Any:
    """Получить тип события закрытия."""
    if _USING_PYQT6:
        return QEvent.Type.Close
    return QEvent.Close

# ============================================================================
# Совместимые ориентации (Orientation)
# ============================================================================

def orientation_horizontal() -> Any:
    """Получить горизонтальную ориентацию."""
    if _USING_PYQT6:
        return Qt.Orientation.Horizontal
    return Qt.Horizontal

def orientation_vertical() -> Any:
    """Получить вертикальную ориентацию."""
    if _USING_PYQT6:
        return Qt.Orientation.Vertical
    return Qt.Vertical

# ============================================================================
# Экспортировать всё для использования
# ============================================================================

__all__ = [
    # Версия информация
    'USING_PYQT6',
    'QT_VERSION',
    
    # Основные модули
    'QtCore',
    'QtWidgets',
    'QtGui',
    
    # Основные классы
    'Qt',
    'QTimer',
    'Signal',
    'Slot',
    'QThread',
    'QObject',
    'QRect',
    'QSize',
    'QPoint',
    'QEvent',
    'pyqtSignal',
    'pyqtSlot',
    
    # Виджеты
    'QApplication',
    'QMainWindow',
    'QWidget',
    'QPushButton',
    'QLabel',
    'QLineEdit',
    'QVBoxLayout',
    'QHBoxLayout',
    'QGridLayout',
    'QScrollArea',
    'QMessageBox',
    'QDialog',
    'QComboBox',
    'QSpinBox',
    'QCheckBox',
    'QTextEdit',
    'QPlainTextEdit',
    'QStatusBar',
    'QMenuBar',
    'QMenu',
    'QFileDialog',
    'QProgressBar',
    'QSlider',
    'QDial',
    
    # GUI классы
    'QIcon',
    'QColor',
    'QFont',
    'QPixmap',
    'QPainter',
    'QPen',
    'QBrush',
    'QImage',
    
    # Функции совместимости
    'align_left',
    'align_right',
    'align_center',
    'align_v_center',
    'align_h_center',
    'wa_translucent_background',
    'wa_no_system_background',
    'wa_stay_on_top',
    'key_press_event',
    'mouse_press_event',
    'close_event',
    'orientation_horizontal',
    'orientation_vertical',
]


# ============================================================================
# Утилиты для отладки
# ============================================================================

def print_compat_info():
    """Вывести информацию о совместимости."""
    print(f"""
    ╔════════════════════════════════════════╗
    ║  Qt Compatibility Layer Information    ║
    ╠════════════════════════════════════════╣
    ║  PyQt Version: {_QT_VERSION}                      ║
    ║  Using PyQt6: {'Yes' if _USING_PYQT6 else 'No':8}                      ║
    ║  Status: {'✓ Ready' if _IMPORT_ERROR is None else '✗ Error':8}                       ║
    ╚════════════════════════════════════════╝
    """)

if _IMPORT_ERROR:
    print(f"⚠️  Compatibility Error: {_IMPORT_ERROR}")
else:
    # Выводить инфо только если запущено прямо
    if __name__ == "__main__":
        print_compat_info()

# ============================================================================
# Тестирование
# ============================================================================

def test_compat():
    """Протестировать совместимость."""
    print("🧪 Testing Qt Compatibility Layer...")
    
    # Проверить версию
    print(f"✓ PyQt{QT_VERSION} imported successfully")
    
    # Проверить импорты
    assert QtCore is not None, "QtCore import failed"
    assert QtWidgets is not None, "QtWidgets import failed"
    assert QtGui is not None, "QtGui import failed"
    print("✓ All modules imported")
    
    # Проверить классы
    assert QMainWindow is not None, "QMainWindow not found"
    assert QPushButton is not None, "QPushButton not found"
    assert QLabel is not None, "QLabel not found"
    print("✓ All widgets imported")
    
    # Проверить функции совместимости
    align = align_center()
    assert align is not None, "align_center() failed"
    print("✓ Compatibility functions working")
    
    print("✅ All tests passed!")
    return True


if __name__ == "__main__":
    print_compat_info()
    test_compat()
