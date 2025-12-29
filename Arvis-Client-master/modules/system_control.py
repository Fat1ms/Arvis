"""
System control module for Arvis
"""

import os
import subprocess
import webbrowser
import winreg
import shutil
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from config.config import Config
from utils.logger import ModuleLogger
from utils.security import AuditEventType, AuditSeverity, Permission, get_audit_logger, get_rbac_manager


class SystemControlModule:
    """Module for controlling system functions, applications, and browser"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ModuleLogger("SystemControl")

        # RBAC integration (v1.4.0+)
        self.rbac_enabled = bool(config.get("security.rbac.enabled", config.get("security.rbac_enabled", False)))
        self.rbac = get_rbac_manager() if self.rbac_enabled else None
        self.audit = get_audit_logger(config) if config.get("audit.enabled", False) else None
        self.current_user = None  # Будет устанавливаться через set_current_user()

        # Common applications and their paths
        self.common_apps = {
            "блокнот": "notepad.exe",
            "калькулятор": "calc.exe",
            "проводник": "explorer.exe",
            "командная строка": "cmd.exe",
            "powershell": "powershell.exe",
            "браузер": self.get_default_browser(),
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "телеграм": "Telegram.exe",
            "discord": "Discord.exe",
            "steam": "steam.exe",
            "vscode": "Code.exe",
            "photoshop": "Photoshop.exe",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE",
        }

        # Popular websites
        self.websites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "yandex": "https://yandex.ru",
            "github": "https://github.com",
            "stackoverflow": "https://stackoverflow.com",
            "wikipedia": "https://wikipedia.org",
            "habr": "https://habr.com",
            "gmail": "https://gmail.com",
            "outlook": "https://outlook.com",
            "vk": "https://vk.com",
            "telegram": "https://web.telegram.org",
            "whatsapp": "https://web.whatsapp.com",
            "facebook": "https://facebook.com",
            "instagram": "https://instagram.com",
            "twitter": "https://twitter.com",
            "linkedin": "https://linkedin.com",
            "reddit": "https://reddit.com",
            "amazon": "https://amazon.com",
            "aliexpress": "https://aliexpress.com",
            "ozon": "https://ozon.ru",
        }

    def set_current_user(self, user):
        """Установить текущего пользователя для аудита (v1.4.0+)"""
        self.current_user = user

    def execute_command(self, command: str) -> str:
        """Execute system control command with RBAC checks (v1.4.0+)"""
        command_lower = command.lower()
        username = self.current_user.username if self.current_user else None

        try:
            # Screenshot / snipping tool
            if any(phrase in command_lower for phrase in [
                "скриншот",
                "снимок экрана",
                "сделай скрин",
                "сделай скриншот",
                "сделать скриншот",
                "screen shot",
                "screenshot",
            ]):
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    return "❌ У вас нет прав для скриншотов (требуется роль User или выше)"
                return self._open_snipping_tool()

            # Window/UI helpers
            if any(phrase in command_lower for phrase in [
                "сверни все",
                "сверни всё",
                "свернуть все",
                "свернуть всё",
                "покажи рабочий стол",
                "показать рабочий стол",
                "покажи десктоп",
                "показать десктоп",
            ]):
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    return "❌ У вас нет прав для управления окнами (требуется роль User или выше)"
                return self._show_desktop()

            if any(phrase in command_lower for phrase in [
                "разверни все",
                "разверни всё",
                "верни окна",
                "верни всё обратно",
                "отмени сворачивание",
            ]):
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    return "❌ У вас нет прав для управления окнами (требуется роль User или выше)"
                return self._undo_minimize_all()

            if any(phrase in command_lower for phrase in [
                "открой настройки",
                "открыть настройки",
                "настройки windows",
                "открой параметры",
                "открыть параметры",
            ]):
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    return "❌ У вас нет прав для открытия настроек (требуется роль User или выше)"
                try:
                    os.startfile("ms-settings:")
                    return "✅ Открыты настройки Windows"
                except Exception as e:
                    return f"❌ Не удалось открыть настройки: {e}"

            if any(phrase in command_lower for phrase in [
                "диспетчер задач",
                "task manager",
                "taskmgr",
            ]):
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    return "❌ У вас нет прав для запуска приложений (требуется роль User или выше)"
                try:
                    subprocess.Popen(["taskmgr.exe"], shell=False)
                    return "✅ Открыт диспетчер задач"
                except Exception as e:
                    return f"❌ Не удалось открыть диспетчер задач: {e}"

            if any(phrase in command_lower for phrase in [
                "открой загрузки",
                "открыть загрузки",
                "папка загрузки",
                "папка загрузок",
            ]):
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    return "❌ У вас нет прав для открытия папок (требуется роль User или выше)"
                try:
                    downloads = str(Path.home() / "Downloads")
                    if Path(downloads).exists():
                        os.startfile(downloads)
                        return "✅ Открыта папка Загрузки"
                    return "❌ Папка Загрузки не найдена"
                except Exception as e:
                    return f"❌ Не удалось открыть загрузки: {e}"

            if any(phrase in command_lower for phrase in [
                "открой документы",
                "открыть документы",
                "папка документы",
            ]):
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    return "❌ У вас нет прав для открытия папок (требуется роль User или выше)"
                try:
                    docs = str(Path.home() / "Documents")
                    if Path(docs).exists():
                        os.startfile(docs)
                        return "✅ Открыта папка Документы"
                    return "❌ Папка Документы не найдена"
                except Exception as e:
                    return f"❌ Не удалось открыть документы: {e}"

            if any(phrase in command_lower for phrase in [
                "открой рабочий стол",
                "открыть рабочий стол",
                "папка рабочий стол",
            ]):
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    return "❌ У вас нет прав для открытия папок (требуется роль User или выше)"
                try:
                    desktop = str(Path.home() / "Desktop")
                    if Path(desktop).exists():
                        os.startfile(desktop)
                        return "✅ Открыт рабочий стол"
                    return "❌ Папка Desktop не найдена"
                except Exception as e:
                    return f"❌ Не удалось открыть рабочий стол: {e}"

            # Application launch commands
            if any(word in command_lower for word in ["запусти", "запуск", "открой", "открыть", "включи", "открой-ка", "запусти-ка"]):
                # RBAC: Проверка прав на запуск приложений
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_APPS):
                    self.logger.warning(f"Permission denied: SYSTEM_APPS for role {self.rbac.get_role()}")
                    if self.audit:
                        self.audit.log_event(
                            AuditEventType.PERMISSION_DENIED,
                            f"Attempted to launch app: {command}",
                            username=username,
                            success=False,
                            severity=AuditSeverity.WARNING,
                        )
                    return "❌ У вас нет прав для запуска приложений (требуется роль User или выше)"

                result = self.launch_application(command_lower)
                if self.audit and "✅" in result:
                    self.audit.log_event(
                        AuditEventType.APP_LAUNCHED, f"Launched application: {command}", username=username
                    )
                return result

            # Website opening commands
            elif any(word in command_lower for word in ["сайт", "веб", "браузер", "страницу", "страница", "перейди", "перейти", "открой сайт", "открой страницу"]):
                # RBAC: Проверка прав на открытие сайтов
                if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_WEBSITES):
                    self.logger.warning(f"Permission denied: SYSTEM_WEBSITES for role {self.rbac.get_role()}")
                    if self.audit:
                        self.audit.log_event(
                            AuditEventType.PERMISSION_DENIED,
                            f"Attempted to open website: {command}",
                            username=username,
                            success=False,
                            severity=AuditSeverity.INFO,
                        )
                    return "❌ У вас нет прав для открытия сайтов (требуется роль User или выше)"

                result = self.open_website(command_lower)
                if self.audit and "✅" in result:
                    self.audit.log_event(AuditEventType.WEBSITE_OPENED, f"Opened website: {command}", username=username)
                return result

            # System commands
            elif any(word in command_lower for word in ["выключи", "выключение", "перезагрузи", "перезагрузка", "заблокируй", "блокировка", "лок", "залочь"]):
                return self.system_power_command(command_lower)

            # Process management
            elif any(word in command_lower for word in ["закрой", "закрыть", "закройте", "завершить", "заверши", "убить", "убей", "выруби"]):
                result = self.close_application(command_lower)
                if self.audit and "✅" in result:
                    self.audit.log_event(
                        AuditEventType.PROCESS_KILLED, f"Closed application: {command}", username=username
                    )
                return result

            else:
                return "❓ Команда не распознана. Попробуйте: 'запусти [приложение]', 'открой [сайт]', 'закрой [приложение]'"

        except PermissionError as e:
            self.logger.error(f"Permission error: {e}")
            return f"❌ Отказано в доступе: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return f"❌ Ошибка выполнения команды: {str(e)}"

    def launch_application(self, command: str) -> str:
        """Launch an application"""
        # Extract application name from command
        app_name = self.extract_app_name(command)

        if not app_name:
            return "❓ Не указано приложение для запуска. Попробуйте: 'запусти блокнот'"

        # Check if it's a common application
        if app_name in self.common_apps:
            try:
                app_path = self.common_apps[app_name]

                # Browser: always open via webbrowser to use system default handler
                if app_name == "браузер" or "браузер" in command:
                    return self.open_browser()

                subprocess.Popen(app_path, shell=True)
                return f"✅ Приложение '{app_name}' запущено"

            except Exception as e:
                self.logger.error(f"Failed to launch {app_name}: {e}")
                return f"❌ Не удалось запустить '{app_name}': {str(e)}"
        else:
            # Try to find and launch by name
            return self.find_and_launch_app(app_name)

    def extract_app_name(self, command: str) -> Optional[str]:
        """Extract application name from command"""
        words = command.split()

        # Look for application names in the command
        for app_name in self.common_apps.keys():
            if app_name in command:
                return app_name

        # If no common app found, try to extract from command structure
        trigger_words = ["запусти", "открой", "открыть", "включи", "запуск", "открой-ка", "запусти-ка"]
        for i, word in enumerate(words):
            if word in trigger_words and i + 1 < len(words):
                # Skip common stop-words
                j = i + 1
                while j < len(words) and words[j] in ("мне", "пожалуйста", "быстро", "сейчас", "плиз", "пожалуй"):
                    j += 1
                if j < len(words):
                    potential_app = words[j]
                    return potential_app.lower()

        return None

    def _show_desktop(self) -> str:
        """Show desktop / minimize all windows."""
        try:
            # Prefer COM minimizeall (does not require nircmd)
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-Command", "(new-object -com shell.application).minimizeall()"],
                shell=False,
            )
            return "✅ Показал рабочий стол"
        except Exception as e:
            return f"❌ Не удалось показать рабочий стол: {e}"

    def _undo_minimize_all(self) -> str:
        """Undo minimize all windows."""
        try:
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-Command", "(new-object -com shell.application).undominimizeall()"],
                shell=False,
            )
            return "✅ Вернул окна"
        except Exception as e:
            return f"❌ Не удалось вернуть окна: {e}"

    def _open_snipping_tool(self) -> str:
        """Open Windows snipping tool (user completes capture)."""
        try:
            # Win11
            try:
                subprocess.Popen(["SnippingTool.exe"], shell=False)
                return "✅ Открыл инструмент для скриншотов"
            except Exception:
                pass
            # Win10 legacy
            try:
                subprocess.Popen(["snippingtool.exe"], shell=False)
                return "✅ Открыл инструмент для скриншотов"
            except Exception:
                pass
            # Last resort: screen clip URI
            try:
                os.startfile("ms-screenclip:")
                return "✅ Открыл инструмент для скриншотов"
            except Exception as e:
                return f"❌ Не удалось открыть инструмент для скриншотов: {e}"
        except Exception as e:
            return f"❌ Не удалось сделать скриншот: {e}"

    def find_and_launch_app(self, app_name: str) -> str:
        """Find and launch application by name"""
        try:
            # Search in common directories
            search_paths = [
                Path("C:/Program Files"),
                Path("C:/Program Files (x86)"),
                Path(os.path.expanduser("~/AppData/Local")),
                Path(os.path.expanduser("~/AppData/Roaming")),
            ]

            for search_path in search_paths:
                if search_path.exists():
                    for exe_file in search_path.rglob("*.exe"):
                        if app_name.lower() in exe_file.name.lower():
                            subprocess.Popen(str(exe_file))
                            return f"✅ Приложение '{exe_file.name}' запущено"

            # Try Windows Registry
            app_path = self.find_app_in_registry(app_name)
            if app_path:
                subprocess.Popen(app_path)
                return f"✅ Приложение '{app_name}' запущено"

            return f"❌ Приложение '{app_name}' не найдено"

        except Exception as e:
            self.logger.error(f"Error finding app {app_name}: {e}")
            return f"❌ Ошибка поиска приложения: {str(e)}"

    def find_app_in_registry(self, app_name: str) -> Optional[str]:
        """Find application path in Windows Registry"""
        try:
            # Check uninstall registry for installed programs
            reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                if app_name.lower() in display_name.lower():
                                    install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                    if install_location:
                                        return install_location
                            except FileNotFoundError:
                                continue
                    except OSError:
                        continue

        except Exception as e:
            self.logger.debug(f"Registry search error: {e}")

        return None

    def open_website(self, command: str) -> str:
        """Open website in browser"""
        site_name = self.extract_website_name(command)

        if not site_name:
            return "❓ Не указан сайт для открытия. Попробуйте: 'открой youtube'"

        # Check if it's a known website
        if site_name in self.websites:
            try:
                webbrowser.open(self.websites[site_name])
                return f"✅ Открыт сайт {site_name}"
            except Exception as e:
                return f"❌ Ошибка открытия сайта: {str(e)}"
        else:
            # Try to open as URL or search query
            try:
                if "." in site_name and not " " in site_name:
                    # Looks like a URL
                    url = site_name if site_name.startswith(("http://", "https://")) else f"https://{site_name}"
                    webbrowser.open(url)
                    return f"✅ Открыт сайт: {url}"
                else:
                    # Search in Google
                    search_url = f"https://www.google.com/search?q={site_name.replace(' ', '+')}"
                    webbrowser.open(search_url)
                    return f"✅ Поиск в Google: {site_name}"
            except Exception as e:
                return f"❌ Ошибка открытия: {str(e)}"

    def extract_website_name(self, command: str) -> Optional[str]:
        """Extract website name from command"""
        words = command.split()

        # Look for known websites
        for site_name in self.websites.keys():
            if site_name in command:
                return site_name

        # Extract from command structure
        trigger_words = ["открой", "открыть", "сайт", "веб", "браузер", "страницу", "страница", "перейди", "перейти"]
        for i, word in enumerate(words):
            if word in trigger_words and i + 1 < len(words):
                # Take remaining words as site name
                potential_site = " ".join(words[i + 1 :])
                return potential_site.lower()

        return None

    def close_application(self, command: str) -> str:
        """Close running application"""
        cleaned = command
        for token in ("закрой", "закрыть", "закройте", "завершить", "заверши", "убить", "убей", "выруби"):
            cleaned = cleaned.replace(token, " ")
        app_name = self.extract_app_name(cleaned)

        if not app_name:
            return "❓ Не указано приложение для закрытия"

        try:
            closed_count = 0

            # Find and terminate processes
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if app_name.lower() in proc.info["name"].lower():
                        proc.terminate()
                        closed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if closed_count > 0:
                return f"✅ Закрыто процессов '{app_name}': {closed_count}"
            else:
                return f"❓ Процессы '{app_name}' не найдены"

        except Exception as e:
            self.logger.error(f"Error closing app {app_name}: {e}")
            return f"❌ Ошибка закрытия приложения: {str(e)}"

    def system_power_command(self, command: str) -> str:
        """Execute system power commands with RBAC checks (v1.4.0+)"""
        username = self.current_user.username if self.current_user else None

        if any(word in command for word in ["выключи", "выключение", "выруби", "отключи компьютер"]):
            return self.shutdown_system()
        elif any(word in command for word in ["перезагрузи", "перезагрузка", "рестарт", "reboot"]):
            return self.restart_system()
        elif any(word in command for word in ["заблокируй", "блокировка", "залочь", "лок", "lock"]):
            return self.lock_system()
        else:
            return "❓ Неизвестная системная команда"

    def shutdown_system(self) -> str:
        """Shutdown system (CRITICAL - requires ADMIN role)"""
        username = self.current_user.username if self.current_user else None

        # RBAC: Критическая проверка - только Admin
        if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_SHUTDOWN):
            self.logger.warning(f"CRITICAL: Permission denied for shutdown by role {self.rbac.get_role()}")
            if self.audit:
                self.audit.log_event(
                    AuditEventType.PERMISSION_DENIED,
                    "Attempted system shutdown without admin permission",
                    username=username,
                    success=False,
                    severity=AuditSeverity.CRITICAL,
                )
            return "🚫 ОТКАЗАНО: Выключение системы требует роли Administrator"

        # Audit: Критическое событие
        if self.audit:
            self.audit.log_event(
                AuditEventType.SYSTEM_SHUTDOWN,
                "System shutdown initiated",
                username=username,
                severity=AuditSeverity.CRITICAL,
            )

        try:
            # For safety, we'll just return a message instead of actually shutting down
            return "⚠️ Команда выключения получена. Для безопасности автоматическое выключение отключено. Используйте стандартные средства Windows."
            # subprocess.run(["shutdown", "/s", "/t", "10"], check=True)
            # return "✅ Система будет выключена через 10 секунд"
        except Exception as e:
            if self.audit:
                self.audit.log_event(
                    AuditEventType.SYSTEM_SHUTDOWN,
                    f"System shutdown failed: {e}",
                    username=username,
                    success=False,
                    severity=AuditSeverity.ERROR,
                )
            return f"❌ Ошибка выключения: {str(e)}"

    def restart_system(self) -> str:
        """Restart system (requires POWER_USER or ADMIN)"""
        username = self.current_user.username if self.current_user else None

        # RBAC: Проверка - Power User или Admin
        if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_RESTART):
            self.logger.warning(f"Permission denied for restart by role {self.rbac.get_role()}")
            if self.audit:
                self.audit.log_event(
                    AuditEventType.PERMISSION_DENIED,
                    "Attempted system restart without sufficient permission",
                    username=username,
                    success=False,
                    severity=AuditSeverity.WARNING,
                )
            return "🚫 ОТКАЗАНО: Перезагрузка системы требует роли Power User или выше"

        # Audit: Критическое событие
        if self.audit:
            self.audit.log_event(
                AuditEventType.SYSTEM_RESTART,
                "System restart initiated",
                username=username,
                severity=AuditSeverity.WARNING,
            )

        try:
            # For safety, we'll just return a message instead of actually restarting
            return "⚠️ Команда перезагрузки получена. Для безопасности автоматическая перезагрузка отключена. Используйте стандартные средства Windows."
            # subprocess.run(["shutdown", "/r", "/t", "10"], check=True)
            # return "✅ Система будет перезагружена через 10 секунд"
        except Exception as e:
            if self.audit:
                self.audit.log_event(
                    AuditEventType.SYSTEM_RESTART,
                    f"System restart failed: {e}",
                    username=username,
                    success=False,
                    severity=AuditSeverity.ERROR,
                )
            return f"❌ Ошибка перезагрузки: {str(e)}"

    def lock_system(self) -> str:
        """Lock system (available to USER and above)"""
        username = self.current_user.username if self.current_user else None

        # RBAC: Проверка - User и выше
        if self.rbac and not self.rbac.has_permission(Permission.SYSTEM_LOCK):
            self.logger.warning(f"Permission denied for lock by role {self.rbac.get_role()}")
            if self.audit:
                self.audit.log_event(
                    AuditEventType.PERMISSION_DENIED,
                    "Attempted system lock without permission",
                    username=username,
                    success=False,
                    severity=AuditSeverity.INFO,
                )
            return "🚫 ОТКАЗАНО: Блокировка системы требует роли User или выше"

        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)

            if self.audit:
                self.audit.log_event(
                    AuditEventType.SYSTEM_LOCK, "System locked", username=username, severity=AuditSeverity.INFO
                )

            return "✅ Система заблокирована"
        except Exception as e:
            if self.audit:
                self.audit.log_event(
                    AuditEventType.SYSTEM_LOCK,
                    f"System lock failed: {e}",
                    username=username,
                    success=False,
                    severity=AuditSeverity.WARNING,
                )
            return f"❌ Ошибка блокировки: {str(e)}"

    def control_audio(self, command: str) -> str:
        """Control system audio"""
        command_lower = command.lower()

        try:
            if any(word in command_lower for word in ["громкость", "звук"]):
                # Set volume to percent: "громкость 30%" / "громкость на 30" / "звук 70 процентов"
                m = re.search(r"(\d{1,3})\s*(%|процент|процента|процентов)?", command_lower)
                if m and any(k in command_lower for k in ["на ", "%", "процент"]):
                    pct = int(m.group(1))
                    pct = max(0, min(100, pct))
                    return self.set_volume_percent(pct)
                if any(word in command_lower for word in ["больше", "увеличь", "прибавь"]):
                    return self.change_volume(10)
                elif any(word in command_lower for word in ["меньше", "уменьш", "убавь"]):
                    return self.change_volume(-10)
                elif any(word in command_lower for word in ["выключи", "отключи", "молчан"]):
                    return self.mute_volume()
                elif any(word in command_lower for word in ["включи", "включить"]):
                    return self.unmute_volume()

            elif any(word in command_lower for word in ["музыка", "плеер", "трек", "песня", "видео"]):
                if any(word in command_lower for word in ["пауза", "останов", "стоп"]):
                    return self.control_media("pause")
                elif any(word in command_lower for word in ["играй", "воспроизведи", "включи"]):
                    return self.control_media("play")
                elif any(word in command_lower for word in ["следующ", "вперед"]):
                    return self.control_media("next")
                elif any(word in command_lower for word in ["предыдущ", "назад"]):
                    return self.control_media("previous")

            return "❓ Команда управления аудио не распознана"

        except Exception as e:
            self.logger.error(f"Audio control error: {e}")
            return f"❌ Ошибка управления аудио: {str(e)}"

    def change_volume(self, delta: int) -> str:
        """Change system volume"""
        try:
            nircmd = shutil.which("nircmd.exe") or shutil.which("nircmd")
            if not nircmd:
                return "❌ Для управления громкостью нужен nircmd (утилита NirCmd). Установите nircmd.exe и добавьте в PATH."

            if delta > 0:
                os.system("nircmd changesysvolume 2000")
                return f"✅ Громкость увеличена"
            else:
                os.system("nircmd changesysvolume -2000")
                return f"✅ Громкость уменьшена"

        except Exception as e:
            return f"❌ Ошибка изменения громкости: {str(e)}"

    def mute_volume(self) -> str:
        """Mute system volume"""
        try:
            nircmd = shutil.which("nircmd.exe") or shutil.which("nircmd")
            if not nircmd:
                return "❌ Для управления звуком нужен nircmd (утилита NirCmd). Установите nircmd.exe и добавьте в PATH."
            os.system("nircmd mutesysvolume 1")
            return "✅ Звук отключен"
        except Exception as e:
            return f"❌ Ошибка отключения звука: {str(e)}"

    def unmute_volume(self) -> str:
        """Unmute system volume"""
        try:
            nircmd = shutil.which("nircmd.exe") or shutil.which("nircmd")
            if not nircmd:
                return "❌ Для управления звуком нужен nircmd (утилита NirCmd). Установите nircmd.exe и добавьте в PATH."
            os.system("nircmd mutesysvolume 0")
            return "✅ Звук включен"
        except Exception as e:
            return f"❌ Ошибка включения звука: {str(e)}"

    def set_volume_percent(self, percent: int) -> str:
        """Set system volume to percent (requires nircmd)."""
        try:
            nircmd = shutil.which("nircmd.exe") or shutil.which("nircmd")
            if not nircmd:
                return "❌ Для установки громкости в % нужен nircmd (утилита NirCmd). Установите nircmd.exe и добавьте в PATH."
            pct = max(0, min(100, int(percent)))
            # nircmd volume is 0..65535
            value = int(round(65535 * (pct / 100.0)))
            os.system(f"nircmd setsysvolume {value}")
            return f"✅ Громкость {pct}%"
        except Exception as e:
            return f"❌ Ошибка установки громкости: {e}"

    def control_media(self, action: str) -> str:
        """Control media playback"""
        try:
            nircmd = shutil.which("nircmd.exe") or shutil.which("nircmd")
            if not nircmd:
                return "❌ Для управления медиа нужен nircmd (утилита NirCmd). Установите nircmd.exe и добавьте в PATH."
            if action == "play":
                os.system("nircmd sendkeypress 0xB3")  # VK_MEDIA_PLAY_PAUSE
                return "✅ Воспроизведение"
            elif action == "pause":
                os.system("nircmd sendkeypress 0xB3")  # VK_MEDIA_PLAY_PAUSE
                return "✅ Пауза"
            elif action == "next":
                os.system("nircmd sendkeypress 0xB0")  # VK_MEDIA_NEXT_TRACK
                return "✅ Следующий трек"
            elif action == "previous":
                os.system("nircmd sendkeypress 0xB1")  # VK_MEDIA_PREV_TRACK
                return "✅ Предыдущий трек"
            else:
                return "❓ Неизвестная медиа команда"
        except Exception as e:
            return f"❌ Ошибка управления медиа: {str(e)}"

    def get_default_browser(self) -> str:
        """Get default browser executable"""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice",
            ) as key:
                prog_id = winreg.QueryValueEx(key, "Progid")[0]

            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as key:
                command = winreg.QueryValueEx(key, "")[0]
                return command.split('"')[1] if '"' in command else command.split()[0]
        except:
            return "explorer.exe"  # Fallback

    def open_browser(self) -> str:
        """Open a web browser in a robust Windows-friendly way.

        Avoids relying solely on URL associations (which can trigger the "Open with" dialog).
        """
        try:
            url = "about:blank"

            def _get_app_path_from_registry(exe_name: str) -> Optional[str]:
                # HKCU/HKLM\...\App Paths\<exe>
                reg_roots = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
                reg_key = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
                for root in reg_roots:
                    try:
                        with winreg.OpenKey(root, reg_key) as key:
                            value = winreg.QueryValueEx(key, "")[0]
                            value = (value or "").strip().strip('"')
                            if value and Path(value).exists():
                                return value
                    except Exception:
                        continue
                return None

            def _candidate_paths(exe_name: str) -> List[str]:
                candidates: List[str] = []
                reg_path = _get_app_path_from_registry(exe_name)
                if reg_path:
                    candidates.append(reg_path)
                which_path = shutil.which(exe_name)
                if which_path:
                    candidates.append(which_path)

                program_files = os.environ.get("ProgramFiles", r"C:\\Program Files")
                program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")
                local_appdata = os.environ.get("LOCALAPPDATA", "")

                # Standard install locations
                if exe_name.lower() == "msedge.exe":
                    candidates += [
                        str(Path(program_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
                        str(Path(program_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
                    ]
                elif exe_name.lower() == "chrome.exe":
                    candidates += [
                        str(Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe"),
                        str(Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe"),
                    ]
                    if local_appdata:
                        candidates.append(str(Path(local_appdata) / "Google" / "Chrome" / "Application" / "chrome.exe"))
                elif exe_name.lower() == "firefox.exe":
                    candidates += [
                        str(Path(program_files) / "Mozilla Firefox" / "firefox.exe"),
                        str(Path(program_files_x86) / "Mozilla Firefox" / "firefox.exe"),
                    ]
                elif exe_name.lower() == "brave.exe":
                    candidates += [
                        str(Path(program_files) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"),
                        str(Path(program_files_x86) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"),
                    ]
                    if local_appdata:
                        candidates.append(
                            str(Path(local_appdata) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe")
                        )
                elif exe_name.lower() == "opera.exe":
                    candidates += [
                        str(Path(program_files) / "Opera" / "launcher.exe"),
                        str(Path(program_files_x86) / "Opera" / "launcher.exe"),
                    ]
                    if local_appdata:
                        candidates.append(str(Path(local_appdata) / "Programs" / "Opera" / "launcher.exe"))

                # Deduplicate and keep existing only
                unique: List[str] = []
                for p in candidates:
                    pp = (p or "").strip().strip('"')
                    if not pp or pp in unique:
                        continue
                    if Path(pp).exists():
                        unique.append(pp)
                return unique

            def _try_launch(exe_path: str, args: List[str]) -> bool:
                try:
                    subprocess.Popen([exe_path, *args], shell=False)
                    self.logger.info(f"Browser launched: {exe_path} {' '.join(args)}")
                    return True
                except Exception as exc:
                    self.logger.debug(f"Browser launch failed for {exe_path}: {exc}")
                    return False

            # 1) Try launching the default browser executable directly
            default_exe = str(self.get_default_browser() or "").strip().strip('"')
            if default_exe and default_exe.lower() != "explorer.exe" and Path(default_exe).exists():
                # Use a neutral, no-association URL
                if _try_launch(default_exe, [url]):
                    return "✅ Браузер запущен"
                if _try_launch(default_exe, []):
                    return "✅ Браузер запущен"

            # 2) Try known browsers (even if not in PATH)
            browser_specs = [
                ("msedge.exe", ["--new-window", url]),
                ("chrome.exe", ["--new-window", url]),
                ("brave.exe", ["--new-window", url]),
                ("firefox.exe", ["-new-window", url]),
                # Opera uses launcher.exe in typical installs
                ("opera.exe", ["--new-window", url]),
            ]
            for exe_name, args in browser_specs:
                for candidate in _candidate_paths(exe_name):
                    if _try_launch(candidate, args) or _try_launch(candidate, []):
                        return "✅ Браузер запущен"

            # 3) Try Edge URI scheme (does not depend on http default app)
            try:
                os.startfile("microsoft-edge:")
                return "✅ Браузер запущен"
            except Exception as exc:
                self.logger.debug(f"microsoft-edge: launch failed: {exc}")

            # 4) Last resort: webbrowser module (may trigger "Open with" if associations are broken)
            try:
                webbrowser.open_new_tab("https://example.com")
                return "✅ Браузер запущен"
            except Exception as exc:
                self.logger.debug(f"webbrowser fallback failed: {exc}")

            return "❌ Не удалось запустить браузер. Проверьте, что установлен браузер и назначено приложение по умолчанию для HTTP/HTTPS в Windows."

        except Exception as e:
            self.logger.error(f"Failed to open browser: {e}")
            return f"❌ Не удалось запустить браузер: {e}"

    def get_system_info(self) -> str:
        """Get system information"""
        try:
            import platform

            # Get system info
            system = platform.system()
            release = platform.release()
            version = platform.version()
            machine = platform.machine()
            processor = platform.processor()

            # Get memory info
            memory = psutil.virtual_memory()
            memory_total = round(memory.total / (1024**3), 1)  # GB
            memory_used = round(memory.used / (1024**3), 1)  # GB
            memory_percent = memory.percent

            # Get disk info
            disk = psutil.disk_usage("/")
            disk_total = round(disk.total / (1024**3), 1)  # GB
            disk_used = round(disk.used / (1024**3), 1)  # GB
            disk_percent = round((disk.used / disk.total) * 100, 1)

            # Get CPU info
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            info = f"""💻 Информация о системе:

🖥️ Система: {system} {release}
⚙️ Процессор: {processor}
🏗️ Архитектура: {machine}

💾 Память: {memory_used} GB / {memory_total} GB ({memory_percent}%)
💿 Диск: {disk_used} GB / {disk_total} GB ({disk_percent}%)
🔄 CPU: {cpu_percent}% ({cpu_count} ядер)"""

            return info

        except Exception as e:
            return f"❌ Ошибка получения информации о системе: {str(e)}"

    def cleanup(self):
        """Cleanup system control module"""
        self.logger.info("System control module cleanup complete")

    def get_status(self) -> Dict[str, Any]:
        """Get system control module status"""
        return {
            "available_apps": len(self.common_apps),
            "available_websites": len(self.websites),
            "system_accessible": True,
        }
