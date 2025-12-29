"""
Асинхронный менеджер задач для предотвращения блокировки UI
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from utils.logger import ModuleLogger


class AsyncTaskManager(QObject):
    """Менеджер для выполнения асинхронных задач без блокировки UI"""

    task_completed = pyqtSignal(str, object)  # task_id, result
    task_failed = pyqtSignal(str, str)  # task_id, error

    def __init__(self):
        super().__init__()
        self.logger = ModuleLogger("AsyncTaskManager")
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ArvisTask")
        self.active_tasks: dict[str, dict[str, Any]] = {}

    def run_async(
        self,
        task_id: str,
        func: Callable,
        *func_args,
        on_complete: Optional[Callable[[str, Any], None]] = None,
        on_error: Optional[Callable[[str, Exception], None]] = None,
        on_finally: Optional[Callable[[str], None]] = None,
        **func_kwargs,
    ) -> bool:
        """Запустить функцию асинхронно"""
        if task_id in self.active_tasks:
            self.logger.warning(f"Task {task_id} already running")
            return False

        try:
            future = self.executor.submit(self._safe_execute, func, *func_args, **func_kwargs)
            self.active_tasks[task_id] = {
                "future": future,
                "on_complete": on_complete,
                "on_error": on_error,
                "on_finally": on_finally,
            }

            # Проверяем завершение через таймер (неблокирующий)
            self._check_completion(task_id)
            return True

        except Exception as e:
            self.logger.error(f"Failed to start task {task_id}: {e}")
            # Сообщаем слушателям о сбое сразу
            if on_error:
                try:
                    on_error(task_id, e)
                except Exception as callback_error:
                    self.logger.error(f"on_error callback failed for task {task_id}: {callback_error}")
            self.task_failed.emit(task_id, str(e))
            if on_finally:
                try:
                    on_finally(task_id)
                except Exception as callback_error:
                    self.logger.error(f"on_finally callback failed for task {task_id}: {callback_error}")
            return False

    def _safe_execute(self, func: Callable, *args, **kwargs) -> Any:
        """Безопасно выполнить функцию с обработкой ошибок"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            raise

    def _check_completion(self, task_id: str):
        """Проверить завершение задачи через таймер"""

        def check():
            task_info = self.active_tasks.get(task_id)
            if not task_info:
                return

            future = task_info["future"]

            if future.done():
                on_complete = task_info.get("on_complete")
                on_error = task_info.get("on_error")
                on_finally = task_info.get("on_finally")

                try:
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]

                    exception = future.exception()
                    if exception is not None:
                        self.logger.error(f"Task {task_id} failed: {exception}")
                        self.task_failed.emit(task_id, str(exception))
                        if on_error:
                            try:
                                on_error(task_id, exception)
                            except Exception as callback_error:
                                self.logger.error(f"on_error callback failed for task {task_id}: {callback_error}")
                    else:
                        result = future.result()
                        self.task_completed.emit(task_id, result)
                        if on_complete:
                            try:
                                on_complete(task_id, result)
                            except Exception as callback_error:
                                self.logger.error(f"on_complete callback failed for task {task_id}: {callback_error}")
                except Exception as e:
                    self.logger.error(f"Task {task_id} completion handling failed: {e}")
                    self.task_failed.emit(task_id, str(e))
                    if on_error:
                        try:
                            on_error(task_id, e)
                        except Exception as callback_error:
                            self.logger.error(f"on_error callback failed for task {task_id}: {callback_error}")
                finally:
                    if on_finally:
                        try:
                            on_finally(task_id)
                        except Exception as callback_error:
                            self.logger.error(f"on_finally callback failed for task {task_id}: {callback_error}")
            else:
                # Если не завершено, проверяем снова через 100мс
                QTimer.singleShot(100, check)

        # Начальная проверка через 50мс
        QTimer.singleShot(50, check)

    def cancel_task(self, task_id: str) -> bool:
        """Отменить задачу"""
        task_info = self.active_tasks.get(task_id)
        if task_info:
            future = task_info["future"]
            cancelled = future.cancel()
            if cancelled:
                on_finally = task_info.get("on_finally")
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                if on_finally:
                    try:
                        on_finally(task_id)
                    except Exception as callback_error:
                        self.logger.error(f"on_finally callback failed for task {task_id}: {callback_error}")
            return cancelled
        return False

    def is_task_running(self, task_id: str) -> bool:
        """Проверить, выполняется ли задача"""
        return task_id in self.active_tasks

    def shutdown(self):
        """Завершить все задачи"""
        self.logger.info("Shutting down async task manager...")

        # Отменяем все активные задачи
        for task_id in list(self.active_tasks.keys()):
            self.cancel_task(task_id)

        # Завершаем executor
        self.executor.shutdown(wait=False)


# Глобальный экземпляр менеджера задач
task_manager = AsyncTaskManager()
