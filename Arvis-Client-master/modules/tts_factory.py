"""
TTS Factory for creating and managing TTS engines with priority-based fallback
Фабрика для создания и управления TTS engine'ами с приоритетной цепочкой fallback

Приоритет движков (по умолчанию):
1. Silero (быстро, офлайн, поддержка русского)
2. Bark (медленнее, офлайн, многоязычность)
3. SAPI (Windows встроенный, fallback)

Можно изменить в config.json: tts.engines_priority
"""

from typing import Optional, List, Type, Dict, Any
from modules.tts_base import TTSEngineBase
from utils.logger import ModuleLogger


class TTSFactory:
    """
    Фабрика для создания TTS engine'ов с приоритетной цепочкой fallback.
    
    Особенности:
    - Автоматическая регистрация встроенных engine'ов
    - Приоритетный выбор: Silero → Bark → SAPI
    - Проверка доступности и health check
    - Динамический fallback при ошибке
    """
    
    # Реестр доступных engine'ов: имя -> класс
    _engines: Dict[str, Type[TTSEngineBase]] = {}
    _logger = ModuleLogger("TTSFactory")
    
    # Приоритет engine'ов по умолчанию
    DEFAULT_PRIORITY = ["silero", "bark", "sapi"]
    
    @classmethod
    def register_engine(cls, name: str, engine_class: Type[TTSEngineBase]) -> None:
        """
        Зарегистрировать новый TTS engine.
        
        Args:
            name: Имя engine'а (например, 'silero', 'bark', 'sapi')
            engine_class: Класс, наследующийся от TTSEngineBase
        
        Raises:
            TypeError: Если engine_class не наследуется от TTSEngineBase
        """
        if not issubclass(engine_class, TTSEngineBase):
            raise TypeError(f"{engine_class} must inherit from TTSEngineBase")
        
        cls._engines[name] = engine_class
        cls._logger.info(f"✓ Registered TTS engine: {name}")
    
    @classmethod
    def create_engine(
        cls, engine_name: str, config, logger
    ) -> Optional[TTSEngineBase]:
        """
        Создать TTS engine по имени.
        
        Args:
            engine_name: Имя engine'а (silero, bark, sapi)
            config: Config объект
            logger: Logger экземпляр
        
        Returns:
            TTSEngineBase экземпляр или None если не найден
        
        Raises:
            ValueError: Если engine не найден
            Exception: Если ошибка при создании engine'а
        """
        if engine_name not in cls._engines:
            available = list(cls._engines.keys())
            raise ValueError(
                f"Unknown TTS engine: {engine_name}. "
                f"Available engines: {available}"
            )
        
        engine_class = cls._engines[engine_name]
        try:
            instance = engine_class(config, logger)
            cls._logger.info(f"✓ Created TTS engine: {engine_name}")
            return instance
        except Exception as e:
            cls._logger.error(f"✗ Failed to create TTS engine {engine_name}: {e}")
            raise
    
    @classmethod
    def create_engine_with_fallback(
        cls, engine_names: Optional[List[str]], config, logger
    ) -> Optional[TTSEngineBase]:
        """
        Создать TTS engine с автоматическим fallback-ом.
        
        Пытается создать engine'ы в порядке приоритета, переходит на следующий при ошибке.
        
        Args:
            engine_names: Список имен engine'ов в порядке приоритета.
                         Если None, использует DEFAULT_PRIORITY или конфиг.
            config: Config объект
            logger: Logger экземпляр
        
        Returns:
            TTSEngineBase экземпляр (первый доступный) или None если все недоступны
        """
        # Получаем приоритет из конфига или используем умолчание
        if engine_names is None:
            engine_names = config.get("tts.engines_priority", cls.DEFAULT_PRIORITY)
            if engine_names is None:
                engine_names = cls.DEFAULT_PRIORITY
        
        chain_str = " → ".join(str(e) for e in engine_names)
        cls._logger.info(f"TTS fallback chain: {chain_str}")
        
        for engine_name in engine_names:
            if engine_name not in cls._engines:
                cls._logger.warning(f"  - {engine_name}: not registered, skipping")
                continue
            # Respect config flags: skip SAPI if disabled
            if engine_name == "sapi":
                try:
                    if not bool(config.get("tts.sapi_enabled", False)):
                        cls._logger.info("  - sapi: disabled by config, skipping")
                        continue
                except Exception:
                    # If config missing, treat as disabled by default
                    cls._logger.info("  - sapi: disabled by config (default), skipping")
                    continue
            
            try:
                cls._logger.info(f"  - Trying {engine_name}...")
                instance = cls.create_engine(engine_name, config, logger)
                
                if instance is None:
                    cls._logger.warning(f"  - {engine_name}: creation returned None")
                    continue
                
                # Проверяем health
                if hasattr(instance, "health_check"):
                    try:
                        health = instance.health_check()
                        if not health.healthy:
                            cls._logger.warning(f"  - {engine_name}: unhealthy ({health.message})")
                            continue
                    except Exception as health_err:
                        cls._logger.debug(f"  - {engine_name}: health check failed: {health_err}")
                        # Не критично, продолжаем
                
                cls._logger.info(f"  ✓ Using {engine_name} TTS")
                return instance
                
            except Exception as e:
                cls._logger.warning(f"  - {engine_name}: {str(e)[:100]}")
                continue
        
        cls._logger.error("✗ No TTS engines available!")
        return None
    
    @classmethod
    def list_available_engines(cls) -> List[str]:
        """
        Получить список доступных TTS engine'ов.
        
        Returns:
            List имен доступных engine'ов
        """
        return list(cls._engines.keys())
    
    @classmethod
    def get_engine_info(cls, engine_name: str) -> Dict[str, Any]:
        """
        Получить информацию о TTS engine'е.
        
        Args:
            engine_name: Имя engine'а
        
        Returns:
            Dict с информацией об engine'е (name, class, module)
        """
        if engine_name not in cls._engines:
            return {}
        
        engine_class = cls._engines[engine_name]
        return {
            "name": engine_name,
            "class": engine_class.__name__,
            "module": engine_class.__module__,
        }
    
    @classmethod
    def is_engine_available(cls, engine_name: str) -> bool:
        """
        Проверить доступность engine'а.
        
        Args:
            engine_name: Имя engine'а
        
        Returns:
            True если engine доступен, False иначе
        """
        return engine_name in cls._engines

# ==============================================================================
# Auto-registration of built-in engines
# ==============================================================================

def _register_builtin_engines() -> None:
    """Зарегистрировать встроенные TTS engine'ы
    
    Приоритет:
    1. Silero (если доступен torch и интернет)
    2. Bark (если установлен bark-ml)
    3. SAPI5 (Windows встроенный, всегда есть)
    """
    
    # 1. Silero TTS (Приоритет 1)
    try:
        from modules.silero_tts_engine import SileroTTSEngine
        TTSFactory.register_engine("silero", SileroTTSEngine)
    except ImportError as e:
        TTSFactory._logger.debug(f"SileroTTSEngine not available: {e}")
    except Exception as e:
        TTSFactory._logger.warning(f"Error registering SileroTTSEngine: {e}")
    
    # 2. Bark TTS (Приоритет 2)
    try:
        from modules.bark_tts_engine import BarkTTSEngine
        TTSFactory.register_engine("bark", BarkTTSEngine)
    except ImportError as e:
        TTSFactory._logger.debug(f"BarkTTSEngine not available: {e}")
    except Exception as e:
        TTSFactory._logger.warning(f"Error registering BarkTTSEngine: {e}")
    
    # 3. SAPI5 TTS (Windows встроенный, Приоритет 3)
    try:
        from modules.system_tts import SAPITTSEngine
        TTSFactory.register_engine("sapi", SAPITTSEngine)
    except ImportError:
        TTSFactory._logger.debug("SAPITTSEngine not available (Windows-only)")
    except Exception as e:
        TTSFactory._logger.warning(f"Error registering SAPITTSEngine: {e}")


# Вызвать при импорте модуля
_register_builtin_engines()
