#!/usr/bin/env python
"""
Arvis Launcher - Entry point
"""

import sys
from pathlib import Path

# Add src to path for development
src_dir = Path(__file__).parent / "src"
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from arvis_launcher.app import main

if __name__ == "__main__":
    sys.exit(main())
