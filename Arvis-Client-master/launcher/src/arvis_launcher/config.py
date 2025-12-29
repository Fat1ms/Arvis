from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WindowConfig:
    width: int = 1100
    height: int = 700


@dataclass
class LauncherConfig:
    """Portable launcher config.

    Stored next to the launcher executable (or next to this file in dev mode).
    """

    client_root: Path
    autoscroll_logs: bool = True
    window: WindowConfig = field(default_factory=WindowConfig)

    _path: Path | None = None

    @staticmethod
    def _exe_dir() -> Path:
        # Prefer argv[0] for onefile/frozen reliability
        try:
            argv0 = Path(sys.argv[0]).resolve()
            if argv0.suffix.lower() == ".exe" and argv0.exists():
                return argv0.parent
        except Exception:
            pass
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            return Path.cwd()

    @classmethod
    def default_client_root(cls) -> Path:
        """Best-effort guess: if рядом есть launch.py — используем эту папку."""
        exe_dir = cls._exe_dir()
        if (exe_dir / "launch.py").exists():
            return exe_dir
        if (exe_dir.parent / "launch.py").exists():
            return exe_dir.parent
        # dev mode: repo root is parent of launcher/
        here = Path(__file__).resolve()
        repo_root = here.parents[3] if len(here.parents) >= 4 else Path.cwd()
        if (repo_root / "launch.py").exists():
            return repo_root
        return exe_dir

    @classmethod
    def load(cls, path: Path | None = None) -> "LauncherConfig":
        if path is None:
            path = cls._exe_dir() / "launcher_config.json"

        cfg = cls(client_root=cls.default_client_root())
        cfg._path = path

        if not path.exists():
            cfg.save()
            return cfg

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # Corrupt file: overwrite with defaults
            cfg.save()
            return cfg

        try:
            client_root = data.get("client_root")
            if isinstance(client_root, str) and client_root.strip():
                cfg.client_root = Path(client_root)

            cfg.autoscroll_logs = bool(data.get("autoscroll_logs", cfg.autoscroll_logs))

            win = data.get("window", {})
            if isinstance(win, dict):
                cfg.window.width = int(win.get("width", cfg.window.width))
                cfg.window.height = int(win.get("height", cfg.window.height))
        except Exception:
            # Keep defaults
            pass

        return cfg

    def save(self) -> None:
        path = self._path or (self._exe_dir() / "launcher_config.json")
        self._path = path
        payload = {
            "client_root": str(self.client_root),
            "autoscroll_logs": bool(self.autoscroll_logs),
            "window": {"width": int(self.window.width), "height": int(self.window.height)},
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
