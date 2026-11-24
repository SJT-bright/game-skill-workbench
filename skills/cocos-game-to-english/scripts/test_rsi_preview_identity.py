#!/usr/bin/env python3
"""Thin top-level entry forwarder into cocos-english-pack."""
from pathlib import Path
import runpy, sys
_TARGET = Path(__file__).resolve().parents[2] / "cocos-english-pack" / "cocos-game-to-english" / "scripts" / "test_rsi_preview_identity.py"
sys.path.insert(0, str(_TARGET.parent))
sys.argv[0] = str(_TARGET)
if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")
