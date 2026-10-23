# SPDX-License-Identifier: GPL-3.0-or-later
"""Taruh root repo di sys.path supaya `import core` jalan tanpa memuat __init__.py root (yang butuh bpy)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
