#!/usr/bin/env python3
"""Old path kept working (v7.8, 总表 B32 c): cocos-game-check/core/scripts/<name>.py moved to remake-core/scripts/ when
the pack was split (2026-10-28, v7.3.1). Session notes and logs from v7.0 - v7.3 still call the old path (for example
~/.kiro/crew/skills/cocos-game-check/core/scripts/serve_preview.py). This file runs the script of the same name in
remake-core/scripts/ with the same arguments and says where it lives now. Every file in this folder is this same text.
"""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    here = Path(__file__).resolve()
    target = next((p / 'remake-core' / 'scripts' / here.name for p in here.parents
                   if (p / 'remake-core' / 'scripts' / here.name).is_file()), None)
    if target is None:
        raise SystemExit('%s moved to remake-core/scripts/%s, which is not installed next to cocos-game-check' % (here, here.name))
    print('提示：%s 已搬到 %s，以后直接用新路径' % (here, target), file=sys.stderr)
    sys.path.insert(0, str(target.parent))
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name='__main__')
