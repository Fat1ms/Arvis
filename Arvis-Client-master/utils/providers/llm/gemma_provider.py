"""
Gemma 2B LLM Provider (Ollama или прямая интеграция)
Gemma 2B LLM Провайдер через Ollama или трансформеры

Priority: 2 (высокий, но ниже Ollama)
Язык документации: Русский + English
"""

from typing import Optional, Generator
import json

from config.config import Config
from utils.logger import ModuleLogger
from utils.providers import LLMProvider, ProviderStatus


class GemmaLLMProvider(LLMProvider):
    """
    Провайдер для локальной языковой модели Gemma 2B.
    
    Режимы работы:
    1. Ollama (рекомендуется) - требует `ollama serve`
    2. Direct (прямая интеграция) - требует `transformers`, `torch`
    
    Параметры:
    - model_id: ID модели ("gemma:2b" для Ollama или "google/gemma-2b-it" для transformers)
    - mode: "ollama" или "direct"
    - quantization: Тип квантизации для Ollama ("Q4_K_M", "Q5_K_M", "Q8_0", None)
    
    Требования:
    - Ollama: localhost:11434 должен быть доступен
    - Direct: torch, transformers, bitsandbytes (опционально)
    """

    def __init__(self, config: Config, mode: str = "ollama", quantization: Optional[str] = None):
        """
        Инициализация Gemma 2B провайдера.
        
        Args:
            config: Объект конфигурации приложения
            mode: "ollama" (по умолчанию) или "direct" (прямая интеграция)
            quantization: Квантизация для Ollama (например "Q4_K_M")
        """
        super().__init__("gemma-2b")
        self.config = config
        self.mode = mode
        self.quantization = quantization
        self.model_instance = None
        self.tokenizer = None
        self._initialized = False
        
        # Параметры модели
        self.model_id = config.get("llm.gemma_model_id", "gemma:2b")
        self.ollama_url = config.get("llm.ollama_url", "http://localhost:11434")
        self.temperature = config.get("llm.temperature", 0.7)
        self.max_tokens = config.get("llm.max_tokens", 512)
        
        self.logger.info(f"🎯 Gemma 2B Provider initialized (mode={mode}, quantization={quantization})")

    def get_priority(self) -> int:
        """
        Приоритет провайдера.
        Gemma 2B - локальная модель, высокий приоритет.
        """
        return 2  # Ниже Ollama (1), но выше облачных сервисов (20+)

    def initialize(self) -> bool:
        """
        Инициализировать Gemma 2B провайдер.
        Выбирает режим работы автоматически.
        
        Returns:
            True если инициализация успешна, иначе False
        """
        try:
            if self._initialized:
                return self.is_available()

            self.logger.info(f"🚀 Initializing Gemma 2B ({self.mode} mode)...")

            if self.mode == "ollama":
                success = self._init_ollama()
            elif self.mode == "direct":
                success = self._init_direct()
            else:
                raise ValueError(f"Unknown mode: {self.mode}")

            if success:
                self._initialized = True
                self._status.value = "available"
                self.logger.info("✅ Gemma 2B initialized successfully")
                return True
            else:
                self._status.value = "unavailable"
                return False

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Gemma 2B: {e}")
            self.set_error(str(e))
            self._status.value = "error"
            return False

    def _init_ollama(self) -> bool:
        """
        Инициализировать Gemma 2B через Ollama.
        
        Требования:
        - Ollama установлена и запущена на localhost:11434
        - Модель gemma:2b загружена
        
        Returns:
            True если успешно, иначе False
        """
        try:
            import requests
            
            # Проверить доступность Ollama сервера
            health_url = f"{self.ollama_url}/api/tags"
            self.logger.info(f"🔍 Checking Ollama at {health_url}...")
            
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code != 200:
                    self.logger.error(f"Ollama returned status {response.status_code}")
                    return False
                    
                # Получить список моделей
                models_data = response.json()
                models = [m.get("name", "") for m in models_data.get("models", [])]
                
                if not models:
                    self.logger.warning("No models found in Ollama. Please run: ollama pull gemma:2b")
                    return False
                
                self.logger.info(f"📦 Available models: {', '.join(models)}")
                
                # Проверить наличие Gemma
                gemma_found = any("gemma" in m for m in models)
                if not gemma_found:
                    self.logger.error("Gemma model not found. Please run: ollama pull gemma:2b")
                    return False
                
                self.logger.info("✅ Ollama health check passed")
                self.model_instance = "ollama"  # Флаг что используем Ollama
                return True
                
            except requests.exceptions.ConnectionError:
                self.logger.error(f"Cannot connect to Ollama at {self.ollama_url}")
                self.logger.info("💡 Please run: ollama serve")
                return False
                
        except ImportError:
            self.logger.error("requests library not found. Install it: pip install requests")
            return False
        except Exception as e:
            self.logger.error(f"Ollama initialization error: {e}")
            return False

    def _init_direct(self) -> bool:
        """
        Инициализировать Gemma 2B прямой интеграцией (transformers).
        
        Требования:
        - torch установлен
        - transformers установлен
        - ~6 ГБ свободной памяти
        
        Returns:
            True если успешно, иначе False
        """
        try:
            self.logger.info("📥 Loading Gemma 2B model with transformers...")
            
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                import torch
            except ImportError:
                self.logger.error("transformers or torch not found. Install: pip install transformers torch")
                return False
            
            # Параметры загрузки
            model_name = "google/gemma-2b-it"  # '-it' = Instruct-tuned версия
            
            self.logger.info(f"🔄 Loading tokenizer from {model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            self.logger.info(f"🔄 Loading model (this may take a minute)...")
            self.model_instance = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,  # Экономит память
                device_map="auto",           # Автоматически на GPU если есть
                low_cpu_mem_usage=True,      # Экономит первичную память
            )
            
            # Включить eval режим
            self.model_instance.eval()
            
            self.logger.info("✅ Gemma 2B model loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Direct initialization failed: {e}")
            return False

    def is_available(self) -> bool:
        """
        Проверить доступность Gemma 2B провайдера.
        
        Returns:
            True если провайдер готов к работе, иначе False
        """
        try:
            if not self._initialized or self.model_instance is None:
                return False

            if self.mode == "ollama":
                # Проверить Ollama соединение
                import requests
                try:
                    response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                    return response.status_code == 200
                except:
                    return False
            else:
                # Direct mode - если модель загружена, она доступна
                return self.model_instance is not None

        except Exception as e:
            self.logger.debug(f"Gemma availability check failed: {e}")
            return False

    def generate_response(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Сгенерировать ответ на запрос.
        
        Формирует системный контекст и вызывает соответствующий метод.
        
        Args:
            prompt: Текст запроса
            temperature: Температура (0.0 - 1.0), если None используется из config
            max_tokens: Максимальное количество токенов, если None используется из config
            system_prompt: Системный промпт для установки роли модели
            
        Returns:
            Сгенерированный ответ
            
        Raises:
            RuntimeError: Если провайдер недоступен
        """
        if not self.is_available():
            raise RuntimeError("Gemma 2B is not available")

        try:
            temp = temperature if temperature is not None else self.temperature
            tokens = max_tokens if max_tokens is not None else self.max_tokens
            
            # Подготовить промпт с системным контекстом
            full_prompt = self._prepare_prompt(prompt, system_prompt)
            
            if self.mode == "ollama":
                return self._generate_ollama(full_prompt, temp, tokens)
            else:
                return self._generate_direct(full_prompt, temp, tokens)

        except Exception as e:
            self.logger.error(f"❌ Generation failed: {e}")
            raise RuntimeError(f"Gemma generation error: {e}")

    def stream_response(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Сгенерировать ответ потоком (streaming).
        
        Позволяет получать ответ по частям по мере его генерации.
        
        Args:
            prompt: Текст запроса
            temperature: Температура (0.0 - 1.0)
            max_tokens: Максимальное количество токенов
            system_prompt: Системный промпт
            
        Yields:
            Чанки ответа
            
        Raises:
            RuntimeError: Если провайдер недоступен
        """
        if not self.is_available():
            raise RuntimeError("Gemma 2B is not available")

        try:
            temp = temperature if temperature is not None else self.temperature
            tokens = max_tokens if max_tokens is not None else self.max_tokens
            
            full_prompt = self._prepare_prompt(prompt, system_prompt)
            
            if self.mode == "ollama":
                yield from self._stream_ollama(full_prompt, temp, tokens)
            else:
                yield from self._stream_direct(full_prompt, temp, tokens)

        except Exception as e:
            self.logger.error(f"❌ Stream generation failed: {e}")
            raise RuntimeError(f"Gemma stream error: {e}")

    def _prepare_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Подготовить промпт с системным контекстом.
        
        Формат для Gemma (Instruct-tuned):
        ```
        <|im_start|>system
        {system_prompt}
        <|im_end|>
        <|im_start|>user
        {prompt}
        <|im_end|>
        <|im_start|>assistant
        ```
        
        Args:
            prompt: Основной промпт
            system_prompt: Системный промпт (опционально)
            
        Returns:
            Отформатированный промпт
        """
        if system_prompt:
            full = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n"
        else:
            full = ""
        
        full += f"<|im_start|>user\n{prompt}\n<|im_end|>\n"
        full += "<|im_start|>assistant\n"
        
        return full

    def _generate_ollama(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """
        Сгенерировать через Ollama API.
        
        Args:
            prompt: Подготовленный промпт
            temperature: Температура
            max_tokens: Макс токенов
            
        Returns:
            Сгенерированный ответ
        """
        import requests
        
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.95,
                "top_k": 40,
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            return data.get("response", "").strip()
            
        except requests.exceptions.Timeout:
            self.logger.error("Ollama generation timeout (120s exceeded)")
            raise RuntimeError("Generation timeout")
        except Exception as e:
            self.logger.error(f"Ollama generation error: {e}")
            raise

    def _stream_ollama(self, prompt: str, temperature: float, max_tokens: int) -> Generator[str, None, None]:
        """
        Сгенерировать потоком через Ollama API.
        
        Args:
            prompt: Подготовленный промпт
            temperature: Температура
            max_tokens: Макс токенов
            
        Yields:
            Чанки ответа
        """
        import requests
        
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=120)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    if chunk:
                        yield chunk
                    
                    # Если done=true, заканчиваем
                    if data.get("done", False):
                        break
                        
        except Exception as e:
            self.logger.error(f"Ollama streaming error: {e}")
            raise

    def _generate_direct(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """
        Сгенерировать прямой интеграцией (transformers).
        
        Args:
            prompt: Подготовленный промпт
            temperature: Температура
            max_tokens: Макс токенов
            
        Returns:
            Сгенерированный ответ
        """
        try:
            import torch
            
            # Токенизировать
            inputs = self.tokenizer(prompt, return_tensors="pt")
            
            # Переместить на устройство (GPU если доступна)
            device = next(self.model_instance.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Сгенерировать
            with torch.no_grad():
                output_ids = self.model_instance.generate(
                    **inputs,
                    max_length=len(inputs["input_ids"][0]) + max_tokens,
                    temperature=temperature,
                    top_p=0.95,
                    do_sample=True,
                    eos_token_id=self.tokenizer.eos_token_id,
                    pad_token_id=self.tokenizer.pad_token_id,
                )
            
            # Декодировать
            response = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
            
            # Отрезать системный контекст
            if "<|im_start|>assistant" in response:
                response = response.split("<|im_start|>assistant")[-1]
            if "<|im_end|>" in response:
                response = response.split("<|im_end|>")[0]
            
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Direct generation error: {e}")
            raise

    def _stream_direct(self, prompt: str, temperature: float, max_tokens: int) -> Generator[str, None, None]:
        """
        Сгенерировать потоком прямой интеграцией.
        
        Симулирует streaming путём генерации по частям.
        
        Args:
            prompt: Подготовленный промпт
            temperature: Температура
            max_tokens: Макс токенов
            
        Yields:
            Чанки ответа
        """
        try:
            # Для прямой интеграции нет встроенного streaming
            # Генерируем целиком и выдаём по словам
            response = self._generate_direct(prompt, temperature, max_tokens)
            
            # Выдавать по словам
            words = response.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield chunk
                
        except Exception as e:
            self.logger.error(f"Direct streaming error: {e}")
            raise

    def shutdown(self) -> bool:
        """
        Завершить работу Gemma 2B.
        
        Returns:
            True если успешно, иначе False
        """
        try:
            if self.mode == "direct":
                # Освободить модель из памяти
                import torch
                if self.model_instance is not None:
                    del self.model_instance
                    torch.cuda.empty_cache()
            
            self.model_instance = None
            self.tokenizer = None
            self._initialized = False
            self._status.value = "unavailable"
            
            self.logger.info("✅ Gemma 2B shutdown complete")
            return True

        except Exception as e:
            self.logger.error(f"❌ Gemma 2B shutdown failed: {e}")
            return False

    def get_model_info(self) -> dict:
        """
        Получить информацию о текущей модели.
        
        Returns:
            Словарь с информацией о модели
        """
        return {
            "name": "Gemma 2B",
            "provider": "google",
            "parameters": 2_000_000_000,
            "context_length": 8192,
            "mode": self.mode,
            "quantization": self.quantization,
            "available": self.is_available(),
            "priority": self.get_priority(),
            "language_support": ["english", "russian", "multilingual"],
        }
