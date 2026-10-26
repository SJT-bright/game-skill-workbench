#!/usr/bin/env python3
"""Prepare an isolated Python Playwright runtime; never install a replacement browser."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv


def prepare(root=None, install=False):
    root = Path(root or Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'GameSkillMigration' / 'chrome-runtime')
    root = root.expanduser().absolute()
    python = root / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        if not install:
            return {'status': 'missing', 'root': str(root)}
        venv.EnvBuilder(with_pip=True).create(root)
    probe = subprocess.run([str(python), '-c', 'import playwright.sync_api; print("playwright_ready")'], capture_output=True, text=True, encoding='utf-8')
    if probe.returncode and install:
        subprocess.run([str(python), '-m', 'pip', 'install', '--index-url', 'https://pypi.org/simple', 'playwright>=1.50,<2'], check=True, timeout=240, stdout=sys.stderr, stderr=sys.stderr)
        probe = subprocess.run([str(python), '-c', 'import playwright.sync_api; print("playwright_ready")'], capture_output=True, text=True, encoding='utf-8')
    return {'status': 'runtime_ready_chrome_unprobed' if probe.returncode == 0 else 'dependency_failed',
            'python': str(python), 'browser_channel': 'chrome', 'browser_installed_or_accepted': False,
            'error': probe.stderr[-1000:] if probe.returncode else None}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-dir', type=Path)
    p.add_argument('--install-runtime', action='store_true')
    a = p.parse_args()
    result = prepare(a.runtime_dir, a.install_runtime)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'runtime_ready_chrome_unprobed' else 2)
