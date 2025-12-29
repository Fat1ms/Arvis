"""Arvis Launcher GUI package.

Этот пакет намеренно НЕ импортирует код клиента Arvis.
Он запускает клиент отдельным процессом (launch.py), чтобы сборка PyInstaller
оставалась стабильной (без нативных крашей из-за torch и т.п.).
"""

from __future__ import annotations
