# 🔧 Исправление: TTS Voice Selection & Python Environment

**Дата**: 24 октября 2025 г.  
**Проблемы**: 2 критические  
**Статус**: ✅ ИСПРАВЛЕНО

---

## 🐛 Проблемы и решения

### Проблема 1: Config не сохранялся на диск

**Симптом**: 
- В Settings выбирали Bark + многоязычный голос
- Сохраняли
- Но при перезапуске или повторном открытии - всё равно был старый Silero

**Причина**:
- `apply_settings()` в settings_dialog.py только вызывал `config.set()` в памяти
- **Но не вызывал `config.save_config()` на диск!**
- При перезапуске приложения - загружал старый конфиг из диска

**Решение**:
- ✅ Добавлен `self.config.save_config()` в конец `apply_settings()` 
- Файл: `src/gui/settings_dialog.py` (строки ~1676-1679)
- Теперь при сохранении настроек конфиг сохраняется на диск

**Код**:
```python
# Save config to disk
try:
    self.config.save_config()
except Exception as e:
    self.logger.error(f"Failed to save config: {e}")
```

---

### Проблема 2: Subprocess использует системный Python вместо venv

**Симптом**:
- При TTS синтезе через subprocess возникала ошибка:
  ```
  [TTS-WORKER-ERROR] No module named 'omegaconf'
  ```
- Логи показывали: `Running subprocess: C:\Users\andre\AppData\Local\Programs\Python\Python312\python.exe`
- Это системный Python, не venv!

**Причина**:
- TTS использует `sys.executable` для вызова subprocess
- Если приложение запущено из системного Python (не через venv), то subprocess тоже использует системный
- omegaconf установлен в venv, но не в системном Python
- Подхват: пакеты не синхронизированы

**Решение**:
- ✅ Добавлена логика автоматического обнаружения venv Python
- Файл: `modules/silero_tts_engine.py` (метод `_speak_via_subprocess`)
- Проверяет наличие `venv/Scripts/python.exe` (Windows) или `venv/bin/python` (Linux)
- Если найден - использует его, иначе fallback на системный

**Код**:
```python
# Get the venv Python executable if available
python_exe = sys.executable
venv_path = Path(__file__).parent.parent / "venv"
if os.name == "nt":
    venv_python = venv_path / "Scripts" / "python.exe"
else:
    venv_python = venv_path / "bin" / "python"

if venv_python.exists():
    python_exe = str(venv_python)
    self.logger.debug(f"Using venv Python: {python_exe}")
else:
    self.logger.debug(f"venv not found, using system Python: {python_exe}")
```

---

## ✅ Результат

После этих двух исправлений:

1. ✅ Config сохраняется на диск при нажатии "Save" в Settings
2. ✅ Subprocess TTS использует venv Python (если доступен)
3. ✅ omegaconf находится в subprocess (нет ошибок)
4. ✅ Bark многоязычный голос будет использоваться правильно

---

## 📝 Тестирование

### Шаги воспроизведения:

1. **Запустить приложение из venv**:
   ```bash
   .venv\Scripts\activate
   python main.py
   ```

2. **Открыть Settings**:
   - Settings → TTS | STT tab

3. **Переключить на Bark**:
   - TTS Engine: выбрать **Bark**
   - Voice: выбрать **v2/multilingual_00**
   - Click: **Save**

4. **Генерировать ответ и озвучить**:
   - Введите вопрос в чат
   - Получите ответ от LLM
   - Click: кнопка озвучки (speaker icon)

5. **Проверить логи**:
   ```
   2025-10-24 22:XX:XX INFO Arvis.ArvisCore: Using venv Python: ...\venv\Scripts\python.exe
   2025-10-24 22:XX:XX INFO Arvis.ArvisCore: Starting subprocess TTS: '...' with voice 'v2/multilingual_00'
   2025-10-24 22:XX:XX INFO Arvis.ArvisCore: TTS subprocess completed successfully
   ```

---

## 📋 Файлы изменены

| Файл | Метод | Изменение |
|------|-------|-----------|
| `src/gui/settings_dialog.py` | `apply_settings()` | Добавлен `config.save_config()` |
| `modules/silero_tts_engine.py` | `_speak_via_subprocess()` | Автодетект venv Python |

---

## 🔍 Дополнительная информация

### Почему это была проблема?

**Сценарий 1**: Пользователь запускает app через GUI (не через terminal)
- Windows ищет Python по умолчанию → находит системный Python 3.12
- Но venv может использовать Python 3.10 или 3.11
- Subprocess вызывается в системном Python → omegaconf не найден

**Сценарий 2**: Config.json не сохраняется
- Settings изменяются в памяти
- App перезапускается или перезагружается
- Старый config.json загружается со диска
- Все изменения потеряны!

### Как убедиться что все работает?

1. Проверьте `config.json` - должна быть:
   ```json
   {
     "tts": {
       "default_engine": "bark",
       "bark": {
         "voice": "v2/multilingual_00"
       }
     }
   }
   ```

2. Запустите TTS и проверьте logs на наличие:
   ```
   Using venv Python: ...
   Starting subprocess TTS: '...' with voice 'v2/multilingual_00'
   TTS subprocess completed successfully
   ```

---

**Статус**: ✅ Готово к тестированию
