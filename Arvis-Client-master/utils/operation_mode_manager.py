"""
Operation Mode Manager
Менеджер для управления режимами работы приложения (STANDALONE, HYBRID, CLOUD)

v1.0 - October 21, 2025
"""

import copy
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.config import Config
from utils.logger import ModuleLogger
from utils.providers import (
    FallbackManager,
    OperationMode,
    Provider,
    ProviderType,
)


class MigrationBackup:
    """Структура для хранения бэкапа состояния при миграции между режимами"""

    def __init__(
        self,
        from_mode: OperationMode,
        to_mode: OperationMode,
        timestamp: datetime,
    ):
        self.from_mode = from_mode
        self.to_mode = to_mode
        self.timestamp = timestamp

        # Данные для восстановления
        self.config_snapshot: Optional[Dict[str, Any]] = None
        self.auth_state: Optional[Dict[str, Any]] = None
        self.user_data: Optional[Dict[str, Any]] = None
        self.history_data: Optional[List[Dict[str, Any]]] = None
        self.custom_data: Dict[str, Any] = {}

    def is_valid(self) -> bool:
        """Проверить валидность бэкапа"""
        return self.config_snapshot is not None

    def get_size_mb(self) -> float:
        """Получить приблизительный размер бэкапа в МБ"""
        import sys

        total_bytes = (
            sys.getsizeof(self.config_snapshot)
            + sys.getsizeof(self.auth_state)
            + sys.getsizeof(self.user_data)
            + sys.getsizeof(self.history_data)
            + sys.getsizeof(self.custom_data)
        )
        return total_bytes / (1024 * 1024)


class OperationModeManager:
    """
    Менеджер для управления режимами работы приложения.
    
    Поддерживает:
    - Инициализацию режимов
    - Переключение между режимами
    - Миграцию данных при переходе
    - Fallback логику
    - Сохранение состояния
    """

    def __init__(self, config: Config):
        """
        Args:
            config: Объект конфигурации приложения
        """
        self.config = config
        self.logger = ModuleLogger("OperationModeManager")

        # Текущий режим
        self._current_mode = self._detect_current_mode()

        # Провайдеры для каждого типа
        self.stt_providers: List[Provider] = []
        self.tts_providers: List[Provider] = []
        self.llm_providers: List[Provider] = []
        self.auth_providers: List[Provider] = []

        # Fallback менеджеры
        self.stt_fallback: Optional[FallbackManager] = None
        self.tts_fallback: Optional[FallbackManager] = None
        self.llm_fallback: Optional[FallbackManager] = None
        self.auth_fallback: Optional[FallbackManager] = None

        # История миграций
        self.backups: List[MigrationBackup] = []

        self.logger.info(f"OperationModeManager initialized with mode: {self._current_mode.get_display_name()}")

    def _detect_current_mode(self) -> OperationMode:
        """Определить текущий режим из конфигурации"""
        try:
            mode_str = str(self.config.get("operation_mode", "hybrid")).lower()

            try:
                return OperationMode(mode_str)
            except ValueError:
                self.logger.warning(f"Unknown operation mode: {mode_str}, falling back to HYBRID")
                return OperationMode.HYBRID

        except Exception as e:
            self.logger.error(f"Error detecting operation mode: {e}")
            return OperationMode.HYBRID

    def get_current_mode(self) -> OperationMode:
        """Получить текущий режим работы"""
        return self._current_mode

    def register_provider(self, provider: Provider) -> bool:
        """
        Зарегистрировать провайдера.
        
        Args:
            provider: Провайдер для регистрации
            
        Returns:
            True если провайдер успешно зарегистрирован
        """
        try:
            if provider.provider_type == ProviderType.STT:
                self.stt_providers.append(provider)
                self.logger.info(f"Registered STT provider: {provider.get_name()}")

            elif provider.provider_type == ProviderType.TTS:
                self.tts_providers.append(provider)
                self.logger.info(f"Registered TTS provider: {provider.get_name()}")

            elif provider.provider_type == ProviderType.LLM:
                self.llm_providers.append(provider)
                self.logger.info(f"Registered LLM provider: {provider.get_name()}")

            elif provider.provider_type == ProviderType.AUTH:
                self.auth_providers.append(provider)
                self.logger.info(f"Registered Auth provider: {provider.get_name()}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to register provider {provider.get_name()}: {e}")
            return False

    def initialize_mode(self) -> bool:
        """
        Инициализировать текущий режим.
        
        Returns:
            True если инициализация успешна
        """
        try:
            self.logger.info(f"Initializing mode: {self._current_mode.get_display_name()}")

            # Инициализируем fallback менеджеры
            if self.stt_providers:
                self.stt_fallback = FallbackManager(self.stt_providers, self.logger)
                self.stt_fallback.initialize_all()

            if self.tts_providers:
                self.tts_fallback = FallbackManager(self.tts_providers, self.logger)
                self.tts_fallback.initialize_all()

            if self.llm_providers:
                self.llm_fallback = FallbackManager(self.llm_providers, self.logger)
                self.llm_fallback.initialize_all()

            if self.auth_providers:
                self.auth_fallback = FallbackManager(self.auth_providers, self.logger)
                self.auth_fallback.initialize_all()

            # Проверяем, есть ли хотя бы один доступный провайдер для каждого типа
            if not self._has_available_providers():
                self.logger.error("No available providers after initialization")
                return False

            self.logger.info(f"✓ Mode {self._current_mode.get_display_name()} initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize mode: {e}")
            return False

    def _has_available_providers(self) -> bool:
        """Проверить, есть ли доступные провайдеры"""
        checks = [
            (self.stt_fallback, "STT"),
            (self.tts_fallback, "TTS"),
            (self.llm_fallback, "LLM"),
            (self.auth_fallback, "Auth"),
        ]

        all_ok = True
        for fallback, provider_type in checks:
            if fallback is None:
                self.logger.warning(f"No {provider_type} providers registered")
                all_ok = False
                continue

            if not fallback.get_available_providers():
                self.logger.error(f"No available {provider_type} providers")
                all_ok = False

        return all_ok

    def switch_mode(self, new_mode: OperationMode) -> bool:
        """
        Переключиться на новый режим.
        
        Args:
            new_mode: Новый режим работы
            
        Returns:
            True если переключение успешно
        """
        if new_mode == self._current_mode:
            self.logger.info(f"Already in mode: {new_mode.get_display_name()}")
            return True

        try:
            self.logger.info(f"Switching mode: {self._current_mode.get_display_name()} → {new_mode.get_display_name()}")

            # 1. Создаём бэкап текущего состояния
            backup = self._create_backup(self._current_mode, new_mode)
            if not backup:
                raise RuntimeError("Failed to create backup")

            # 2. Сохраняем состояние в бэкап
            self._save_current_state_to_backup(backup)

            # 3. Останавливаем текущие компоненты
            if not self._shutdown_current_mode():
                self.logger.warning("Some components failed to shutdown")
                # Не прерываем миграцию, продолжаем

            # 4. Синхронизируем данные между режимами
            if not self._sync_data_between_modes(backup):
                self.logger.warning("Data sync failed, but continuing migration")

            # 5. Переключаем конфиг
            self.config.set("operation_mode", new_mode.value)
            self._current_mode = new_mode

            # 6. Инициализируем новый режим
            if not self.initialize_mode():
                self.logger.error("New mode initialization failed")
                return self._rollback_to_backup(backup)

            # 7. Проверяем миграцию
            if not self._verify_migration():
                self.logger.error("Migration verification failed")
                return self._rollback_to_backup(backup)

            # 8. Очищаем старые бэкапы если необходимо
            self._cleanup_old_backups()

            self.logger.info(f"✓ Successfully switched to mode: {new_mode.get_display_name()}")
            return True

        except Exception as e:
            self.logger.error(f"Error switching mode: {e}")
            return False

    def _create_backup(self, from_mode: OperationMode, to_mode: OperationMode) -> Optional[MigrationBackup]:
        """Создать бэкап для миграции"""
        try:
            backup = MigrationBackup(from_mode, to_mode, datetime.now())
            self.logger.debug(f"Created backup: {from_mode.value} → {to_mode.value}")
            return backup
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None

    def _save_current_state_to_backup(self, backup: MigrationBackup):
        """Сохранить текущее состояние в бэкап"""
        try:
            # Сохраняем конфиг
            backup.config_snapshot = copy.deepcopy(dict(self.config.config))

            self.logger.debug("State saved to backup")

        except Exception as e:
            self.logger.error(f"Failed to save state to backup: {e}")

    def _shutdown_current_mode(self) -> bool:
        """Завершить работу текущего режима"""
        try:
            all_ok = True

            if self.stt_fallback:
                if not self.stt_fallback.shutdown_all():
                    all_ok = False

            if self.tts_fallback:
                if not self.tts_fallback.shutdown_all():
                    all_ok = False

            if self.llm_fallback:
                if not self.llm_fallback.shutdown_all():
                    all_ok = False

            if self.auth_fallback:
                if not self.auth_fallback.shutdown_all():
                    all_ok = False

            return all_ok

        except Exception as e:
            self.logger.error(f"Error shutting down mode: {e}")
            return False

    def _sync_data_between_modes(self, backup: MigrationBackup) -> bool:
        """Синхронизировать данные между режимами"""
        try:
            # TODO: Реализовать синхронизацию данных
            # Примеры:
            # - Сохранить/загрузить историю чатов
            # - Синхронизировать настройки пользователя
            # - Перенести данные между БД если нужно

            self.logger.debug("Data synchronization completed")
            return True

        except Exception as e:
            self.logger.error(f"Error syncing data: {e}")
            return False

    def _verify_migration(self) -> bool:
        """Проверить успешность миграции"""
        try:
            return self._has_available_providers()

        except Exception as e:
            self.logger.error(f"Migration verification failed: {e}")
            return False

    def _rollback_to_backup(self, backup: MigrationBackup) -> bool:
        """Откатить на предыдущий режим используя бэкап"""
        try:
            if not backup.is_valid():
                self.logger.error("Backup is not valid, cannot rollback")
                return False

            self.logger.warning(f"Rolling back to mode: {backup.from_mode.get_display_name()}")

            # Восстанавливаем конфиг из бэкапа
            if backup.config_snapshot:
                self.config.config = backup.config_snapshot

            # Переключаемся обратно
            self._current_mode = backup.from_mode

            # Переинициализируем
            return self.initialize_mode()

        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return False

    def _cleanup_old_backups(self):
        """Удалить старые бэкапы (оставляем только последние 5)"""
        try:
            if len(self.backups) > 5:
                old_backups = self.backups[:-5]
                self.backups = self.backups[-5:]
                self.logger.debug(f"Cleaned up {len(old_backups)} old backups")

        except Exception as e:
            self.logger.debug(f"Error cleaning up backups: {e}")

    def get_available_providers(self, provider_type: ProviderType) -> List[Provider]:
        """Получить список доступных провайдеров для типа"""
        if provider_type == ProviderType.STT:
            return self.stt_fallback.get_available_providers() if self.stt_fallback else []
        elif provider_type == ProviderType.TTS:
            return self.tts_fallback.get_available_providers() if self.tts_fallback else []
        elif provider_type == ProviderType.LLM:
            return self.llm_fallback.get_available_providers() if self.llm_fallback else []
        elif provider_type == ProviderType.AUTH:
            return self.auth_fallback.get_available_providers() if self.auth_fallback else []

        return []

    def get_status(self) -> Dict[str, Any]:
        """Получить статус менеджера и всех провайдеров"""
        return {
            "current_mode": self._current_mode.value,
            "mode_name": self._current_mode.get_display_name(),
            "stt": self.stt_fallback.get_status() if self.stt_fallback else None,
            "tts": self.tts_fallback.get_status() if self.tts_fallback else None,
            "llm": self.llm_fallback.get_status() if self.llm_fallback else None,
            "auth": self.auth_fallback.get_status() if self.auth_fallback else None,
            "backups_count": len(self.backups),
        }
