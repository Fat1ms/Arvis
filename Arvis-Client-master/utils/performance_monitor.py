"""
Диагностика и оптимизация производительности Arvis
"""

import threading
import time
from typing import Any, Dict

import psutil

from utils.logger import ModuleLogger


class PerformanceMonitor:
    """Монитор производительности для диагностики зависаний"""

    def __init__(self):
        self.logger = ModuleLogger("PerformanceMonitor")
        self.start_time = time.time()
        self.is_monitoring = False
        self.monitor_thread = None
        self.stats = {"cpu_usage": [], "memory_usage": [], "response_times": {}, "slow_operations": []}

    def start_monitoring(self):
        """Запустить мониторинг производительности"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Остановить мониторинг"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self.logger.info("Performance monitoring stopped")

    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.is_monitoring:
            try:
                # CPU и память
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()

                self.stats["cpu_usage"].append(cpu_percent)
                self.stats["memory_usage"].append(memory.percent)

                # Логируем высокую нагрузку
                if cpu_percent > 80:
                    self.logger.warning(f"High CPU usage: {cpu_percent}%")

                if memory.percent > 80:
                    self.logger.warning(f"High memory usage: {memory.percent}%")

                # Ограничиваем размер истории
                if len(self.stats["cpu_usage"]) > 60:  # 1 минута
                    self.stats["cpu_usage"].pop(0)
                    self.stats["memory_usage"].pop(0)

            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")

            time.sleep(1)

    def measure_operation(self, operation_name: str):
        """Декоратор для измерения времени операций"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.record_operation_time(operation_name, duration)

            return wrapper

        return decorator

    def record_operation_time(self, operation: str, duration: float):
        """Записать время выполнения операции"""
        if operation not in self.stats["response_times"]:
            self.stats["response_times"][operation] = []

        self.stats["response_times"][operation].append(duration)

        # Логируем медленные операции
        if duration > 1.0:  # Более 1 секунды
            self.stats["slow_operations"].append(
                {"operation": operation, "duration": duration, "timestamp": time.time()}
            )
            self.logger.warning(f"Slow operation: {operation} took {duration:.2f}s")

        # Ограничиваем размер истории
        if len(self.stats["response_times"][operation]) > 100:
            self.stats["response_times"][operation].pop(0)

    def get_performance_report(self) -> Dict[str, Any]:
        """Получить отчёт о производительности"""
        report = {
            "uptime": time.time() - self.start_time,
            "current_cpu": psutil.cpu_percent(),
            "current_memory": psutil.virtual_memory().percent,
            "avg_cpu": sum(self.stats["cpu_usage"]) / len(self.stats["cpu_usage"]) if self.stats["cpu_usage"] else 0,
            "avg_memory": (
                sum(self.stats["memory_usage"]) / len(self.stats["memory_usage"]) if self.stats["memory_usage"] else 0
            ),
            "slow_operations_count": len(self.stats["slow_operations"]),
            "operations_stats": {},
        }

        # Статистика по операциям
        for op, times in self.stats["response_times"].items():
            if times:
                report["operations_stats"][op] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "max_time": max(times),
                    "min_time": min(times),
                }

        return report

    def diagnose_performance_issues(self) -> list:
        """Диагностировать проблемы производительности"""
        issues = []

        # Проверяем CPU
        if self.stats["cpu_usage"]:
            avg_cpu = sum(self.stats["cpu_usage"]) / len(self.stats["cpu_usage"])
            if avg_cpu > 70:
                issues.append(f"Высокая нагрузка на CPU: {avg_cpu:.1f}%")

        # Проверяем память
        if self.stats["memory_usage"]:
            avg_memory = sum(self.stats["memory_usage"]) / len(self.stats["memory_usage"])
            if avg_memory > 70:
                issues.append(f"Высокое потребление памяти: {avg_memory:.1f}%")

        # Проверяем медленные операции
        recent_slow = [
            op for op in self.stats["slow_operations"] if time.time() - op["timestamp"] < 300
        ]  # Последние 5 минут

        if len(recent_slow) > 5:
            issues.append(f"Много медленных операций: {len(recent_slow)} за 5 минут")

        # Проверяем времена ответа
        for op, times in self.stats["response_times"].items():
            if times:
                avg_time = sum(times) / len(times)
                if avg_time > 0.5:  # Более 500мс
                    issues.append(f"Медленная операция {op}: {avg_time:.2f}s в среднем")

        return issues


# Глобальный монитор производительности
performance_monitor = PerformanceMonitor()
