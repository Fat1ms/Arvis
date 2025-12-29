#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Arvis Launcher entrypoint (UTF-8 clean).

Этот файл должен быть максимально минимальным и НЕ импортировать клиент.
Он только добавляет `launcher/src` в sys.path и запускает GUI-лаунчер.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _add_launcher_src_to_syspath() -> None:
    here = Path(__file__).resolve()
    candidates = [
        here.parent / "src",
        here.parent.parent / "launcher" / "src",
        Path.cwd() / "launcher" / "src",
        Path.cwd() / "src",
    ]
    for src_dir in candidates:
        if src_dir.exists() and str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
            return


def _show_error_dialog(title: str, message: str) -> None:
    if sys.platform != "win32":
        return

    try:
        import ctypes

        MB_OK = 0x00000000
        MB_ICONERROR = 0x00000010
        ctypes.windll.user32.MessageBoxW(0, message, title, MB_OK | MB_ICONERROR)
    except Exception:
        pass


def main() -> int:
    _add_launcher_src_to_syspath()
    try:
        from arvis_launcher_gui.app import main as launcher_main  # type: ignore

        return int(launcher_main())
    except Exception as e:
        _show_error_dialog(
            "Arvis Launcher",
            "Не удалось запустить лаунчер.\n\n"
            f"Ошибка: {e!r}\n\n"
            "Проверь, что установлены зависимости и в сборке есть PyQt6.",
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
