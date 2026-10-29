#!/usr/bin/env python3
"""Compatibility entry for the relocated shared preview server."""
from pathlib import Path
import runpy
import sys
if __name__ == '__main__':
    target = Path(__file__).resolve().parents[2] / 'cocos-game-core/scripts/serve_preview.py'
    if not target.is_file():
        raise SystemExit('Missing modular cocos-game-core preview server')
    sys.path.insert(0, str(target.parent))
    runpy.run_path(str(target), run_name='__main__')
