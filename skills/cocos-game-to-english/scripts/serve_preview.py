#!/usr/bin/env python3
"""Compatibility entry for the relocated shared preview server.

v7.8 (总表 B21 / B30 F): the shared server is remake-core/scripts/serve_preview.py in this pack (it runs the trial-link
smoke before a --keep link is printed). The old target cocos-game-core/scripts/ is not shipped in the English pack,
so this entry used to stop with "Missing modular cocos-game-core preview server".
"""
from pathlib import Path
import runpy
import sys
if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    target = next((p for p in (root / 'remake-core/scripts/serve_preview.py', root / 'cocos-game-core/scripts/serve_preview.py')
                   if p.is_file()), None)
    if target is None:
        raise SystemExit('Missing shared preview server remake-core/scripts/serve_preview.py')
    sys.path.insert(0, str(target.parent))
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name='__main__')
