"""
LLM pipeline extracted from Arvis core.

This module encapsulates the LLM processing flow (streaming and non-streaming),
including helper functions for building context and appending web-search sources.

Design note:
- For minimal-risk refactor, functions here accept a reference to the ArvisCore
  instance (named `core`) to access existing state (config, logger, timers,
  conversation history, signals). This preserves behavior while reducing
  `arvis_core.py` size. Later we can decouple via a cleaner interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from i18n import _


class _LLMWorker(QThread):
    """QThread worker for non-streamed LLM responses."""

    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, llm_client, message: str, context: str, history: List[Dict[str, str]]):
        super().__init__()
        self.llm_client = llm_client
        self.message = message
        self.context = context
        self.history = history or []

    def run(self):
        try:
            resp = self.llm_client.get_response(self.message, self.context, self.history)
            if resp is None:
                self.error.emit("Empty response")
            else:
                self.success.emit(resp)
        except Exception as e:
            self.error.emit(str(e))


class _LLMStreamWorker(QThread):
    """QThread worker for streamed LLM responses (emits chunks)."""

    chunk = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, llm_client, message: str, context: str, history: List[Dict[str, str]]):
        super().__init__()
        self.llm_client = llm_client
        self.message = message
        self.context = context
        self.history = history or []

    def run(self):
        try:
            for part in self.llm_client.stream_response(self.message, self.context, self.history):
                try:
                    if part:
                        self.chunk.emit(part)
                except Exception:
                    # Continue streaming even if UI listeners misbehave
                    pass
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))


def _append_search_sources(response_text: str, search_payload: Dict[str, Any]) -> str:
    """Append formatted search sources to the assistant response."""
    try:
        results = []
        raw_results = search_payload.get("results") if isinstance(search_payload, dict) else None
        if isinstance(raw_results, list):
            results = [r for r in raw_results if isinstance(r, dict) and r.get("link")]
        if not results:
            return response_text

        lines: List[str] = []
        lines.append(_("🔎 Источники:"))
        for idx, item in enumerate(results, start=1):
            title = (item.get("title") or item.get("display_link") or item.get("link") or "").strip()
            link = (item.get("link") or "").strip()
            display_link = (item.get("display_link") or "").strip()
            snippet = (item.get("snippet") or "").strip()

            if not title:
                title = link or display_link or _("Источник")

            bullet = f"{idx}. {title}"
            if display_link and display_link != link:
                bullet += f" — {display_link}"
            if link:
                bullet += f" ({link})"
            lines.append(bullet)

            if snippet:
                lines.append(f"   {snippet}")

        base_text = (response_text or "").rstrip()
        appendix = "\n".join(lines).strip()
        if not base_text:
            return appendix
        return f"{base_text}\n\n{appendix}"
    except Exception:
        return response_text


def _build_context(core: Any, search_payload: Optional[Dict[str, Any]] = None) -> str:
    """Build context information for LLM using core's modules and config."""
    context_parts = []

    # User information
    user_name = core.config.get("user.name", "Пользователь")
    user_city = core.config.get("user.city", "")

    context_parts.append(f"Пользователя зовут {user_name}.")
    if user_city:
        context_parts.append(f"Пользователь находится в городе {user_city}.")

    # Available modules
    available_modules = []
    if getattr(core, "weather_module", None):
        available_modules.append("погода")
    if getattr(core, "news_module", None):
        available_modules.append("новости")
    if getattr(core, "system_control_module", None):
        available_modules.append("управление компьютером")
    if getattr(core, "calendar_module", None):
        available_modules.append("календарь")

    if available_modules:
        context_parts.append(f"Доступные модули: {', '.join(available_modules)}.")

    # System info
    context_parts.append("Ты - Arvis, ИИ-ассистент. Отвечай дружелюбно и полезно.")

    if search_payload and search_payload.get("context"):
        context_parts.append(
            "Используй свежие результаты поиска ниже, чтобы дать точный ответ с упоминанием источника."
        )
        context_parts.append(search_payload["context"])

    return " ".join(context_parts)


def _should_auto_continue(text: str) -> bool:
    """Heuristic: determine if a response looks truncated and should be continued."""
    try:
        t = (text or "").rstrip()
        if len(t) < 60:
            return False
        good_endings = (".", "!", "?", "…", "\u2026", "\u00BB", '"', "'", ")", "]", "}")
        bad_endings = (",", ";", ":", "—", "-", "\\")
        if t.endswith(good_endings):
            return False
        if t.endswith(bad_endings) or t[-1].isalnum():
            return True
        return False
    except Exception:
        return False


def process_with_llm(core: Any, message: str) -> None:
    """Process message with LLM using the original logic, adapted to module scope.

    Parameters
    - core: ArvisCore instance
    - message: user text
    """
    if not getattr(core, "llm_client", None):
        try:
            core.error_occurred.emit("LLM клиент не инициализирован")
        except Exception:
            pass
        return

    try:
        search_payload = getattr(core, "_pending_search_results", None)

        # Prepare context
        context = _build_context(core, search_payload)

        # Decide streaming or full-response mode
        use_stream = bool(core.config.get("llm.stream", True))
        try:
            core.logger.debug(
                f"LLM: use_stream={use_stream}, model={getattr(core.llm_client, 'default_model', None)}"
            )
        except Exception:
            pass

        # Auto-pick model if configured as 'auto'
        try:
            if getattr(core.llm_client, "default_model", None) in (None, "", "auto"):
                import psutil

                mem_gb = psutil.virtual_memory().total / (1024**3)
                if mem_gb >= 24:
                    preferred = ["qwen2:7b", "mistral:7b", "llama3:8b", "phi3:medium"]
                elif mem_gb >= 12:
                    preferred = ["phi3:mini", "gemma2:2b", "llama3:3b", "qwen2:1.5b"]
                else:
                    preferred = ["qwen2:0.5b", "phi3:mini", "tinyllama:1.1b"]
                available = []
                try:
                    available = core.llm_client.get_available_models()
                except Exception:
                    pass
                for m in preferred:
                    if m in available:
                        if hasattr(core.llm_client, "set_model"):
                            core.llm_client.set_model(m)
                        break
        except Exception:
            pass

        if use_stream and not hasattr(core.llm_client, "stream_response"):
            core.logger.error("LLM client has no stream_response; falling back to non-stream mode")
            use_stream = False

        # Build worker
        if use_stream:
            worker: QThread = _LLMStreamWorker(
                llm_client=core.llm_client,
                message=message,
                context=context,
                history=core.conversation_history_manager.get_recent(6),
            )
        else:
            worker = _LLMWorker(
                llm_client=core.llm_client,
                message=message,
                context=context,
                history=core.conversation_history_manager.get_recent(6),
            )

        # Keep reference to avoid GC
        core._current_llm_worker = worker
        core._is_streaming_current = bool(use_stream)

        # Worker timeout
        try:
            wt = core.config.get("llm.worker_timeout_ms", 45000)
            worker_timeout_ms = wt if isinstance(wt, int) and wt > 0 else 45000
        except Exception:
            worker_timeout_ms = 45000
        core._worker_timeout_ms = worker_timeout_ms

        core._timeout_timer = QTimer()
        core._timeout_timer.setSingleShot(True)
        # Some Arvis builds might miss this method; guard with getattr
        if hasattr(core, "_check_worker_timeout"):
            core._timeout_timer.timeout.connect(core._check_worker_timeout)
        core._timeout_timer.start(worker_timeout_ms)
        try:
            core.logger.debug(f"LLM: worker timeout set to {worker_timeout_ms} ms")
        except Exception:
            pass

        # Handlers
        def on_success(resp: str):
            try:
                if resp and resp.strip():
                    enriched_resp = resp
                    if search_payload and search_payload.get("results"):
                        enriched_resp = _append_search_sources(resp, search_payload)

                    try:
                        core.response_ready.emit(enriched_resp)
                    except Exception:
                        pass

                    metadata = {"source": "llm", "model": getattr(core.llm_client, "default_model", "unknown")}
                    if search_payload and search_payload.get("results"):
                        metadata["search_results"] = search_payload.get("results")

                    # Save answer into history
                    core.conversation_history_manager.add_message("assistant", enriched_resp, metadata=metadata)
                    core.conversation_history = core.conversation_history_manager.get_all()
                    core.logger.info(f"LLM response received successfully ({len(resp)} chars)")
                else:
                    try:
                        core.error_occurred.emit("Не удалось получить ответ от LLM")
                    except Exception:
                        pass
                    core.logger.warning("Empty response from LLM")
            finally:
                core._pending_search_results = None
                if hasattr(core, "_cleanup_processing_state"):
                    core._cleanup_processing_state()

        def on_error(err: str):
            try:
                core.logger.error(f"Error processing with LLM (worker): {err}")
                try:
                    core.error_occurred.emit(f"Ошибка LLM: {err}")
                except Exception:
                    pass
            finally:
                core._pending_search_results = None
                if hasattr(core, "_cleanup_processing_state"):
                    core._cleanup_processing_state()

        if use_stream and isinstance(worker, _LLMStreamWorker):
            buffer = {"text": ""}
            core._stream_buffer_text = ""

            def on_chunk(chunk: str):
                if not chunk:
                    return
                buffer["text"] += chunk
                core._stream_buffer_text = buffer["text"]
                try:
                    core.partial_response.emit(buffer["text"])  # accumulated for safety
                except Exception:
                    pass

            def on_done():
                final_text = buffer["text"].strip()
                try:
                    core.logger.debug(f"LLM: stream done, final_len={len(final_text)}")
                except Exception:
                    pass
                if not final_text:
                    core.logger.warning("Stream completed but no text was received")
                    try:
                        core.error_occurred.emit("Получен пустой ответ от LLM. Попробуйте повторить запрос.")
                    except Exception:
                        pass
                    core._is_streaming_current = False
                    core._stream_buffer_text = ""
                    return

                # Optional auto-continue (preserved from original behavior)
                try:
                    auto_enabled = bool(core.config.get("llm.auto_continue", True))
                except Exception:
                    auto_enabled = True

                try:
                    ac_max = core.config.get("llm.auto_continue_max", 2)
                    ac_max = ac_max if isinstance(ac_max, int) else int(float(ac_max))
                except Exception:
                    ac_max = 2

                if (
                    auto_enabled
                    and getattr(core, "_auto_continue_attempts", 0) < ac_max
                    and _should_auto_continue(final_text)
                ):
                    try:
                        core._auto_continue_attempts = getattr(core, "_auto_continue_attempts", 0) + 1
                        try:
                            core.response_ready.emit(final_text)
                        except Exception:
                            pass
                        core.conversation_history_manager.add_message(
                            "assistant",
                            final_text,
                            metadata={"source": "llm_partial", "part": core._auto_continue_attempts},
                        )
                        core.conversation_history = core.conversation_history_manager.get_all()
                        core.logger.info(
                            f"Auto-continue #{core._auto_continue_attempts}: truncated ending detected, scheduling continuation"
                        )
                        try:
                            core.error_occurred.emit("✍️ Продолжаю генерацию...")
                        except Exception:
                            pass
                        if hasattr(core, "_cleanup_processing_state"):
                            core._cleanup_processing_state()
                        QTimer.singleShot(100, lambda: core.process_message("Продолжи"))
                        return
                    except Exception:
                        pass

                core._is_streaming_current = False
                core._stream_buffer_text = ""
                on_success(final_text)

            def _stream_on_error_bridge(err: str):
                txt = (buffer.get("text") or "").strip()
                try:
                    auto_enabled = bool(core.config.get("llm.auto_continue", True))
                except Exception:
                    auto_enabled = True
                try:
                    ac_max = core.config.get("llm.auto_continue_max", 2)
                    ac_max = ac_max if isinstance(ac_max, int) else int(float(ac_max))
                except Exception:
                    ac_max = 2

                if txt and auto_enabled and getattr(core, "_auto_continue_attempts", 0) < ac_max:
                    core._auto_continue_attempts = getattr(core, "_auto_continue_attempts", 0) + 1
                    core.logger.warning(
                        f"LLM stream error; auto-continue attempt #{core._auto_continue_attempts}"
                    )
                    try:
                        core.response_ready.emit(txt)
                    except Exception:
                        pass
                    try:
                        core.conversation_history.append({"role": "assistant", "content": txt})
                    except Exception:
                        pass
                    if hasattr(core, "_force_reset_processing_state"):
                        core._force_reset_processing_state()
                    try:
                        core.error_occurred.emit("⚠️ Ошибка стрима. Продолжаю генерацию...")
                    except Exception:
                        pass
                    QTimer.singleShot(150, lambda: core.process_message("Продолжи"))
                else:
                    on_error(err)

            worker.chunk.connect(on_chunk)
            worker.error.connect(_stream_on_error_bridge)
            worker.done.connect(on_done)
        else:
            if isinstance(worker, _LLMWorker):
                def _non_stream_success_bridge(resp: str):
                    text = (resp or "").strip()
                    try:
                        auto_enabled = bool(core.config.get("llm.auto_continue", True))
                    except Exception:
                        auto_enabled = True
                    try:
                        ac_max = core.config.get("llm.auto_continue_max", 2)
                        ac_max = ac_max if isinstance(ac_max, int) else int(float(ac_max))
                    except Exception:
                        ac_max = 2
                    if (
                        text
                        and auto_enabled
                        and not getattr(core, "_is_streaming_current", False)
                        and getattr(core, "_auto_continue_attempts", 0) < ac_max
                        and _should_auto_continue(text)
                        and ("Ошибка" not in text)
                        and ("Не удается" not in text)
                        and ("Извините" not in text)
                    ):
                        core._auto_continue_attempts = getattr(core, "_auto_continue_attempts", 0) + 1
                        try:
                            core.response_ready.emit(text)
                        except Exception:
                            pass
                        try:
                            core.conversation_history.append({"role": "assistant", "content": text})
                        except Exception:
                            pass
                        core.logger.info(
                            f"Non-stream auto-continue #{core._auto_continue_attempts} scheduled"
                        )
                        if hasattr(core, "_cleanup_processing_state"):
                            core._cleanup_processing_state()
                        QTimer.singleShot(120, lambda: core.process_message("Продолжи"))
                        return
                    on_success(resp)

                worker.success.connect(_non_stream_success_bridge)
                worker.error.connect(on_error)

        try:
            if hasattr(worker, "started"):
                worker.started.connect(lambda: core.logger.debug(f"LLM: worker started (stream={use_stream})"))
        except Exception:
            pass
        try:
            worker.start()
            core.logger.debug("LLM: worker.start() called")
        except Exception:
            pass

    except Exception as e:
        core.logger.error(f"Error scheduling LLM processing: {e}")
        try:
            core.error_occurred.emit(f"Ошибка LLM: {e}")
        except Exception:
            pass
