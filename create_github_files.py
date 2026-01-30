# -*- coding: utf-8 -*-
"""Script to create GitHub public page files"""
import os

TARGET_DIR = r"C:\Users\andre\Arvis-GitHub-Public"

# README.md content
README_CONTENT = """<p align="center">
  <img src="assets/logo.png" alt="Arvis Logo" width="180"/>
</p>

<h1 align="center">Arvis - AI Voice Assistant</h1>

<p align="center">
  <b>Персональный голосовой ИИ-ассистент для Windows с полной приватностью</b>
</p>

<p align="center">
  <a href="https://febrifugal-laronda-carbonisable.ngrok-free.dev/">🌐 Официальный сайт</a> •
  <a href="#-о-проекте">О проекте</a> •
  <a href="#-возможности">Возможности</a> •
  <a href="#-установка">Установка</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square" alt="Platform"/>
  <img src="https://img.shields.io/badge/python-3.11%2B-green?style=flat-square" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-orange?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=flat-square" alt="Status"/>
</p>

---

## 🎯 О проекте

**Arvis** — это современный десктопный ИИ-ассистент с голосовым управлением, созданный с фокусом на **приватность** и **офлайн-работу**. В отличие от облачных решений, Arvis обрабатывает все данные локально на вашем компьютере.

### Почему Arvis?

- 🔒 **Полная приватность** — данные не покидают ваше устройство
- 🌐 **Работает офлайн** — не требует постоянного интернета
- 🎙️ **Естественный голос** — качественный синтез речи
- 🤖 **Мощный ИИ** — интеграция с локальными LLM через Ollama
- 🎨 **Современный интерфейс** — красивый и интуитивный UI
- 🆓 **Бесплатный** — базовая версия полностью бесплатна

---

## ✨ Возможности

### 🎤 Голосовое управление
- Распознавание речи через **Vosk** (полностью офлайн)
- Естественный синтез речи: **Bark**, **Silero**, **SAPI**
- Активация голосом (wake word)
- Поддержка русского, украинского и английского языков

### 💬 Умный чат
- Интеграция с локальными LLM через **Ollama**
- Поддержка любых совместимых моделей (Llama, Mistral, Qwen и др.)
- Сохранение истории диалогов
- Режим "Live" для непрерывного общения

### 🌍 Информационные запросы
- 🌤️ **Погода** — через Open-Meteo (бесплатно)
- 📰 **Новости** — через GNews API
- 🔍 **Веб-поиск** — через SerpAPI

### 🖱️ Автоматизация
- Запуск программ голосом
- Открытие веб-сайтов
- Системные команды

### 🖼️ Мультимодальность *(в разработке)*
- Анализ изображений через Vision модели
- Работа с файлами

---

## 💻 Системные требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| **ОС** | Windows 10 | Windows 11 |
| **CPU** | 4 ядра | 8+ ядер |
| **RAM** | 8 GB | 16+ GB |
| **GPU** | Не требуется | NVIDIA (для ускорения) |
| **Диск** | 10 GB | SSD, 20+ GB |

---

## 📦 Установка

### Быстрая установка

1. Перейдите на [официальный сайт](https://febrifugal-laronda-carbonisable.ngrok-free.dev/)
2. Скачайте последнюю версию
3. Запустите установщик и следуйте инструкциям

### Ollama (для LLM)

Для работы ИИ-чата необходим Ollama:

1. Скачайте [Ollama](https://ollama.ai/) для Windows
2. Установите и запустите
3. Скачайте модель: `ollama pull llama3.2`

---

## 🗺️ Roadmap

### ✅ Реализовано
- [x] Голосовой ввод/вывод (Vosk + Bark/Silero)
- [x] Интеграция с Ollama
- [x] Погода, новости, веб-поиск
- [x] Современный UI на PyQt6
- [x] Многоязычность (RU/UA/EN)
- [x] Лаунчер с управлением моделями

### 🚧 В разработке
- [ ] Vision API (анализ изображений)
- [ ] RAG (работа с документами)
- [ ] Улучшенный TTS (Piper, Kokoro)
- [ ] AI-агенты и автоматизация

### 💡 Планируется
- [ ] Интеграция с календарем и почтой
- [ ] Кроссплатформенность (Linux, macOS)

---

## 🤝 Содействие

Мы приветствуем вклад в развитие проекта!

- 🐛 Нашли баг? [Создайте Issue](https://github.com/Fat1ms/Arvis/issues)
- 💡 Есть идея? [Предложите Feature](https://github.com/Fat1ms/Arvis/issues)

---

## 📄 Лицензия

Проект распространяется под лицензией **MIT**. См. [LICENSE](LICENSE).

---

## 📞 Контакты

- 🌐 **Сайт:** [febrifugal-laronda-carbonisable.ngrok-free.dev](https://febrifugal-laronda-carbonisable.ngrok-free.dev/)
- 📧 **GitHub:** [@Fat1ms](https://github.com/Fat1ms)

---

<p align="center">
  <b>⭐ Поставьте звезду, если проект понравился! ⭐</b>
</p>

<p align="center">
  Made with ❤️ for the community
</p>
"""

# LICENSE content (MIT)
LICENSE_CONTENT = """MIT License

Copyright (c) 2024-2026 Fat1ms

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# .gitignore content
GITIGNORE_CONTENT = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Build
build/
dist/
*.egg-info/
"""

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    os.makedirs(os.path.join(TARGET_DIR, "assets"), exist_ok=True)
    
    # Write README.md
    with open(os.path.join(TARGET_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(README_CONTENT)
    print("✓ README.md created")
    
    # Write LICENSE
    with open(os.path.join(TARGET_DIR, "LICENSE"), "w", encoding="utf-8") as f:
        f.write(LICENSE_CONTENT)
    print("✓ LICENSE created")
    
    # Write .gitignore
    with open(os.path.join(TARGET_DIR, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(GITIGNORE_CONTENT)
    print("✓ .gitignore created")
    
    # Create placeholder for logo
    placeholder = os.path.join(TARGET_DIR, "assets", "LOGO_PLACEHOLDER.txt")
    with open(placeholder, "w", encoding="utf-8") as f:
        f.write("Добавьте сюда файл logo.png (рекомендуемый размер: 512x512 px)")
    print("✓ assets/ folder created (add logo.png here)")
    
    print(f"\n✅ All files created in: {TARGET_DIR}")
    print("\nNext steps:")
    print("1. Add logo.png to assets/ folder")
    print("2. cd to folder and run: git init")
    print("3. git add .")
    print("4. git commit -m 'Initial commit'")
    print("5. git remote add origin https://github.com/Fat1ms/Arvis.git")
    print("6. git push -u origin main")

if __name__ == "__main__":
    main()
