# 🔄 Миграция PyQt5 → PyQt6 + Customtkinter

**Документ**: Исследование совместимости и инструкция миграции  
**Дата**: October 21, 2025  
**Статус**: Готовая документация  
**Язык**: Русский + English

---

## 📋 Содержание

1. [Обзор изменений](#обзор-изменений)
2. [Сравнение фреймворков](#сравнение-фреймворков)
3. [Стратегия миграции](#стратегия-миграции)
4. [Детальное руководство](#детальное-руководство)
5. [Проблемы совместимости](#проблемы-совместимости)
6. [Примеры кода](#примеры-кода)

---

## Обзор изменений

### PyQt5 vs PyQt6

| Аспект | PyQt5 | PyQt6 | Статус |
|--------|-------|-------|--------|
| **Лицензия** | GPL, Commercial | GPL, Commercial | Оба открыты |
| **Python версия** | 3.6+ | 3.7+ | PyQt6 новее |
| **API** | v1 (stable) | v2 (переработан) | ⚠️ Несовместим |
| **Qt версия** | Qt 5.15 | Qt 6.x | Новый major version |
| **Поддержка** | ✅ Активная | ✅ Активная | Обе поддерживаются |

### Главные изменения PyQt5 → PyQt6

```python
# PyQt5
from PyQt5.QtCore import Qt, QTimer, Signal
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton
from PyQt5.QtGui import QIcon, QColor

# PyQt6
from PyQt6.QtCore import Qt, QTimer, Signal
from PyQt6.QtWidgets import QMainWindow, QWidget, QPushButton
from PyQt6.QtGui import QIcon, QColor

# Основные отличия:
# 1. Параметры в методах теперь часто имеют type hints
# 2. Некоторые перечисления переименованы (Qt.AlignLeft → Qt.AlignmentFlag.AlignLeft)
# 3. Сигналы требуют явного типа (Signal(str) вместо Signal())
# 4. Удалены некоторые deprecated методы
```

---

## Сравнение фреймворков

### PyQt5 vs PyQt6 vs Customtkinter

| Критерий | PyQt5 | PyQt6 | Customtkinter |
|----------|-------|-------|---------------|
| **Легкость** | Средняя | Средняя | ✅ Простой |
| **Стиль** | Системный | Системный | ✅ Modern UI |
| **Кривая обучения** | Крутая | Крутая | ✅ Пологая |
| **Производительность** | ⚡⚡⚡ | ⚡⚡⚡ | ⚡⚡ |
| **Функциональность** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Кроссплатформность** | ✅ | ✅ | ✅ |
| **Windows** | ✅ Отлично | ✅ Отлично | ✅ Отлично |
| **macOS** | ✅ Отлично | ✅ Отлично | ✅ Хорошо |
| **Linux** | ✅ Хорошо | ✅ Хорошо | ✓ Функции |
| **Размер** | ~50 МБ | ~50 МБ | ~1 МБ |
| **UI из дизайнера** | ✅ (Qt Designer) | ✅ (Qt Designer) | ❌ |

### Рекомендация

**Для Arvis**:
- **PyQt5** (текущий выбор) - лучший баланс функциональности и производительности
- **PyQt6** - если нужны новые возможности Qt 6
- **Customtkinter** - если нужен простой и красивый UI, заменяем PyQt

---

## Стратегия миграции

### План действий (3 фазы)

#### Фаза 1: Исследование совместимости (1-2 дня)
- ✅ Анализ использования PyQt5 в коде
- ✅ Определение всех импортов
- ✅ Выявление несовместимостей
- ✅ Создание матрицы миграции

#### Фаза 2: Создание адаптивного слоя (2-3 дня)
```
Вместо прямой замены PyQt5 на PyQt6,
создаём промежуточный слой compatibility.py
который работает с обоими фреймворками
```

#### Фаза 3: Постепенная миграция компонентов (1-2 недели)
- Переписываем по одному компоненту
- Тестируем каждый
- Постепенно переходим на PyQt6/Customtkinter

### Минимальные изменения логики

**Принцип**: НЕ трогаем бизнес-логику ArvisCore, только GUI слой!

```
ArvisCore (не трогаем)
    ↓
GUI Layer (adaptable)
    ↓
PyQt5 / PyQt6 / Customtkinter (выбираем фреймворк)
```

---

## Детальное руководство

### Шаг 1: Создать слой совместимости

**Файл**: `src/gui/compat/qt_compat.py`

```python
"""
Qt Compatibility Layer
Совместимость между PyQt5 и PyQt6

Использование:
from src.gui.compat.qt_compat import (
    QMainWindow, QPushButton, Qt, 
    QtCore, QtWidgets, QtGui
)
"""

import sys

# Определить какой Qt установлен
try:
    from PyQt6 import QtCore, QtWidgets, QtGui
    from PyQt6.QtCore import Qt, QTimer, Signal
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QPushButton,
        QLabel, QVBoxLayout, QHBoxLayout
    )
    QT_VERSION = 6
    USING_PYQT6 = True
except ImportError:
    from PyQt5 import QtCore, QtWidgets, QtGui
    from PyQt5.QtCore import Qt, QTimer, Signal
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QPushButton,
        QLabel, QVBoxLayout, QHBoxLayout
    )
    QT_VERSION = 5
    USING_PYQT6 = False

print(f"ℹ️ Using PyQt{QT_VERSION}")

# Экспортировать всё что нужно
__all__ = [
    'QtCore', 'QtWidgets', 'QtGui',
    'Qt', 'QTimer', 'Signal',
    'QMainWindow', 'QWidget', 'QPushButton',
    'QLabel', 'QVBoxLayout', 'QHBoxLayout',
    'QT_VERSION', 'USING_PYQT6'
]
```

**Использование**:
```python
# Вместо
from PyQt5.QtWidgets import QMainWindow

# Использовать
from src.gui.compat.qt_compat import QMainWindow
```

### Шаг 2: Обновить импорты в GUI

**Было**:
```python
from PyQt5.QtCore import Qt, QTimer, Signal
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtGui import QIcon
```

**Стало**:
```python
from src.gui.compat.qt_compat import Qt, QTimer, Signal, QMainWindow
from src.gui.compat.qt_compat import QtGui as QGui

# Использовать QGui.QIcon
```

### Шаг 3: Обработать различия в перечислениях

**PyQt5**:
```python
button.setAlignment(Qt.AlignLeft)
window.setAttribute(Qt.WA_TranslucentBackground)
```

**PyQt6**:
```python
button.setAlignment(Qt.AlignmentFlag.AlignLeft)
window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
```

**Решение - Compatibility wrapper**:
```python
# src/gui/compat/qt_enums.py
if USING_PYQT6:
    class QtCompat:
        AlignLeft = Qt.AlignmentFlag.AlignLeft
        WA_TranslucentBackground = Qt.WidgetAttribute.WA_TranslucentBackground
else:
    class QtCompat:
        AlignLeft = Qt.AlignLeft
        WA_TranslucentBackground = Qt.WA_TranslucentBackground

# Использование
button.setAlignment(QtCompat.AlignLeft)
```

### Шаг 4: Обновить сигналы

**Было (PyQt5)**:
```python
class MyWidget(QWidget):
    my_signal = Signal()  # Без типов
    text_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.my_signal.emit()
        self.text_changed.emit("hello")
```

**Стало (PyQt6 - рекомендуется)**:
```python
class MyWidget(QWidget):
    my_signal = Signal()  # Проще
    text_changed = Signal(str)  # С типом
    
    def __init__(self):
        super().__init__()
        self.my_signal.emit()
        self.text_changed.emit("hello")
```

Хорошая новость: PyQt6 обычно совместим с PyQt5 в сигналах!

---

## Проблемы совместимости

### ❌ Проблема 1: Перечисления (Enums)

**PyQt5**:
```python
Qt.AlignLeft
Qt.WA_TranslucentBackground
```

**PyQt6**:
```python
Qt.AlignmentFlag.AlignLeft
Qt.WidgetAttribute.WA_TranslucentBackground
```

**Решение**: Использовать compatibility layer

```python
# qt_enums.py
from src.gui.compat.qt_compat import Qt, USING_PYQT6

if USING_PYQT6:
    class AlignmentCompat:
        AlignLeft = Qt.AlignmentFlag.AlignLeft
        AlignRight = Qt.AlignmentFlag.AlignRight
        AlignCenter = Qt.AlignmentFlag.AlignCenter
else:
    class AlignmentCompat:
        AlignLeft = Qt.AlignLeft
        AlignRight = Qt.AlignRight
        AlignCenter = Qt.AlignCenter
```

### ❌ Проблема 2: Удалённые методы

**PyQt5** имеет методы которых нет в **PyQt6**:

```python
# PyQt5
button.clicked.connect(func)  # ✅ Работает

# PyQt6 (переименовано)
button.clicked.connect(func)  # ✅ Всё ещё работает
```

**Решение**: Проверить документацию PyQt6, обновить код

### ❌ Проблема 3: Стилизация (StyleSheets)

**Обычно совместима**, но иногда:

```python
# PyQt5
button.setStyleSheet("color: red")

# PyQt6 (иногда нужна обновка)
button.setStyleSheet("color: red")  # Обычно работает

# Если не работает → обновить синтаксис Qt 6
```

### ❌ Проблема 4: Шрифты и рендеринг

**PyQt6** использует лучший рендер текста, может выглядеть по-другому

**Решение**: Протестировать UI на обоих версиях

---

## Примеры кода

### Пример 1: Базовое окно совместимое

```python
"""
Базовое окно совместимое с PyQt5 и PyQt6
"""

from src.gui.compat.qt_compat import (
    QMainWindow, QWidget, QPushButton,
    QVBoxLayout, Qt, Signal, USING_PYQT6
)

class CompatibleMainWindow(QMainWindow):
    """Главное окно совместимое с PyQt5/6."""
    
    button_clicked = Signal()
    
    def __init__(self):
        super().__init__()
        
        print(f"Using PyQt{'6' if USING_PYQT6 else '5'}")
        
        # Создать UI
        self.init_ui()
    
    def init_ui(self):
        """Инициализировать интерфейс."""
        # Центральный виджет
        central = QWidget()
        layout = QVBoxLayout()
        
        # Кнопка
        button = QPushButton("Click me")
        button.clicked.connect(self.on_button_clicked)
        
        layout.addWidget(button)
        central.setLayout(layout)
        self.setCentralWidget(central)
        
        self.setWindowTitle("Compatible App")
        self.resize(400, 300)
    
    def on_button_clicked(self):
        """Обработчик клика."""
        print("✓ Button clicked")
        self.button_clicked.emit()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = CompatibleMainWindow()
    window.show()
    sys.exit(app.exec_())
```

### Пример 2: Адаптивные перечисления

```python
"""
Адаптивные перечисления для PyQt5/6
"""

from src.gui.compat.qt_compat import Qt, USING_PYQT6

class QtEnums:
    """Unified enum access."""
    
    # Выравнивание
    @staticmethod
    def align_left():
        return Qt.AlignmentFlag.AlignLeft if USING_PYQT6 else Qt.AlignLeft
    
    @staticmethod
    def align_center():
        return Qt.AlignmentFlag.AlignCenter if USING_PYQT6 else Qt.AlignCenter
    
    # Атрибуты окна
    @staticmethod
    def wa_translucent_background():
        if USING_PYQT6:
            return Qt.WidgetAttribute.WA_TranslucentBackground
        else:
            return Qt.WA_TranslucentBackground

# Использование
button.setAlignment(QtEnums.align_center())
window.setAttribute(QtEnums.wa_translucent_background(), True)
```

### Пример 3: Миграция ChatPanel на PyQt6

**Было (PyQt5)**:
```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Signal

class ChatPanel(QWidget):
    message_sent = Signal(str)
```

**Стало (PyQt6)**:
```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Signal

class ChatPanel(QWidget):
    message_sent = Signal(str)  # ✅ Всё то же самое!
```

---

## 🔄 Миграция шаг за шагом

### Фаза 1: Создать compat слой (2 часа)

1. Создать `src/gui/compat/qt_compat.py`
2. Создать `src/gui/compat/qt_enums.py`
3. Протестировать оба фреймворка

### Фаза 2: Обновить импорты (4 часа)

1. Найти все импорты PyQt5:
   ```bash
   grep -r "from PyQt5" src/gui/
   ```

2. Заменить на compat слой:
   ```
   from PyQt5.QtWidgets → from src.gui.compat.qt_compat
   ```

3. Протестировать каждый файл

### Фаза 3: Обновить перечисления (6 часов)

1. Найти все использования `Qt.AlignLeft`, `Qt.WA_*`, и т.д.
2. Заменить на `QtEnums.align_left()`, и т.д.
3. Протестировать UI

### Фаза 4: Полная миграция на PyQt6 (1-2 дня)

Когда всё работает:
1. Удалить PyQt5 из requirements.txt
2. Добавить PyQt6
3. Обновить compat слой чтобы всегда использовал PyQt6

---

## Customtkinter интеграция

Если хотите попробовать **Customtkinter** (проще и красивее):

```python
"""
GUI слой на Customtkinter
"""

import customtkinter as ctk

class CustomtkinterUI:
    def __init__(self, root):
        self.root = ctk.CTk()
        self.root.geometry("800x600")
        self.root.title("Arvis")
        
        # Темная тема
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Создать UI
        self.init_ui()
    
    def init_ui(self):
        """Создать интерфейс."""
        # Заголовок
        title = ctk.CTkLabel(
            self.root,
            text="Arvis Assistant",
            font=("Arial", 24, "bold")
        )
        title.pack(pady=20)
        
        # Кнопка
        button = ctk.CTkButton(
            self.root,
            text="Start Listening",
            command=self.on_button_click
        )
        button.pack(pady=10)
        
        self.root.mainloop()
    
    def on_button_click(self):
        print("✓ Button clicked")

# Использование
if __name__ == "__main__":
    ui = CustomtkinterUI(None)
```

---

## ✅ Checklist миграции

- [ ] Создан compat слой (qt_compat.py)
- [ ] Создан enums слой (qt_enums.py)
- [ ] Все импорты обновлены
- [ ] Все перечисления обновлены
- [ ] GUI тесты проходят на PyQt5
- [ ] GUI тесты проходят на PyQt6
- [ ] Внешний вид одинаков на обеих версиях
- [ ] Производительность одинакова
- [ ] Requirements.txt обновлён

---

## 📚 Ссылки

- **PyQt5**: https://riverbankcomputing.com/software/pyqt/intro
- **PyQt6**: https://riverbankcomputing.com/software/pyqt/download6
- **Customtkinter**: https://github.com/TomSchimansky/CustomTkinter
- **Миграционный гайд PyQt5→PyQt6**: https://www.riverbankcomputing.com/static/Docs/PyQt6/introduction.html

---

**Версия документа**: 1.0  
**Статус**: Готово  
**Дата обновления**: October 21, 2025
