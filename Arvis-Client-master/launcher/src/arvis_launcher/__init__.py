"""Arvis Launcher package (GUI bootstrap).

This package intentionally does NOT import the Arvis client code.
It only starts the client as a separate process (launch.py) to keep
PyInstaller builds stable (avoid torch native import issues).
"""

from __future__ import annotations
