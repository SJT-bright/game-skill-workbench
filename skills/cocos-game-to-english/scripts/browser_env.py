#!/usr/bin/env python3
"""Run a pack command with a browser the packaging checks can drive, on any computer (English pack 10.2.10).

Saul 2026-10-31: the English Skill is used on other people's computers, so no step may depend on Ego Lite. The pack's
browser checks (ad_regression.py, runtime_regression.py and the writers that call them, serve_preview.py --keep,
chrome_touch.py) look for `ego-browser`. This wrapper:
  * Ego found (`ego-browser` on PATH or EGO_BROWSER set): runs the command unchanged (Saul's own Mac keeps using Ego).
  * no Ego: puts a launcher named ego-browser (ego-browser.cmd on Windows) on PATH and sets EGO_BROWSER to it. The
    launcher runs cdp_browser.mjs with Node, which drives an ordinary Chrome, Edge or Chromium: headless, its own
    temporary profile, never the user's own browser windows or profile. Checks and verdicts stay the same.
  * neither works: says in plain words what is missing and exits 2 (the packaging tools' exit code for 环境不完整).

  python3 browser_env.py -- <command ...>             e.g. python3 browser_env.py -- python3 build_checked_zip.py ...
  python3 browser_env.py --browser chrome -- <cmd>    use Chrome/Edge even when Ego is installed (Ego not working)
  python3 browser_env.py --check                      say which browser the checks will use; start it once
Windows: use `python` (or `py -3`) instead of `python3`.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / 'cdp_browser.mjs'
MIN_NODE = 18
ENV_CODE = 2


def node_path():
    """Node executable and its major version, or (None, None)."""
    exe = os.environ.get('CDP_NODE') or shutil.which('node') or shutil.which('nodejs')
    if not exe:
        return None, None
    try:
        out = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=20).stdout.strip()
        return exe, int(out.lstrip('v').split('.')[0])
    except (OSError, ValueError, subprocess.SubprocessError):
        return exe, None


def browser_candidates(env=None, platform=None):
    """Same search order as cdp_browser.mjs."""
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    found = []
    own = env.get('CDP_BROWSER') or env.get('CHROME_PATH')
    if own:
        found.append(own)
    if platform == 'darwin':
        for base in ('/Applications', str(Path.home() / 'Applications')):
            for app in ('Google Chrome.app/Contents/MacOS/Google Chrome', 'Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
                        'Chromium.app/Contents/MacOS/Chromium',
                        'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'):
                found.append(base + '/' + app)
    elif platform == 'win32':
        roots = []
        for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            if env.get(key) and env.get(key) not in roots:
                roots.append(env.get(key))
        for root in roots:
            for rel in (('Google', 'Chrome', 'Application', 'chrome.exe'), ('Microsoft', 'Edge', 'Application', 'msedge.exe'),
                        ('Chromium', 'Application', 'chrome.exe')):
                found.append(os.path.join(root, *rel))
    else:
        for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge',
                     'microsoft-edge-stable'):
            hit = shutil.which(name)
            if hit:
                found.append(hit)
    return found


def find_browser():
    for c in browser_candidates():
        if os.path.isfile(c):
            return c
    return None


def find_ego():
    own = os.environ.get('EGO_BROWSER')
    if own and Path(own).exists():
        return own
    return shutil.which('ego-browser')


def plan(mode='auto'):
    """Which browser route the checks will use: {'route': 'ego'|'chrome'|None, 'problem': text, ...}."""
    ego = find_ego() if mode in ('auto', 'ego') else None
    if ego:
        return {'route': 'ego', 'ego_browser': ego}
    if mode == 'ego':
        return {'route': None, 'problem': '这台电脑没有 Ego Lite（找不到 ego-browser）。不用装 Ego：去掉 --browser ego，用 Chrome 或 Edge 跑。'}
    node, major = node_path()
    browser = find_browser()
    problems = []
    if not node:
        problems.append('没有 Node.js（检查要用它驱动浏览器）。到 https://nodejs.org 装 LTS 版，装好后新开一个终端再跑。')
    elif major is not None and major < MIN_NODE:
        problems.append('Node.js 太旧（%d），要 %d 或更新：到 https://nodejs.org 装 LTS 版。' % (major, MIN_NODE))
    if not browser:
        problems.append('没有 Chrome、Edge 或 Chromium。装 Google Chrome 就行（Windows 自带 Edge）；装在别处的用 '
                        'CDP_BROWSER=<浏览器程序的完整路径> 指定。')
    if problems:
        return {'route': None, 'problem': '；'.join(problems), 'node': node, 'browser': browser}
    return {'route': 'chrome', 'node': node, 'node_major': major, 'browser': browser, 'runtime': str(RUNTIME)}


def write_launchers(folder, node):
    """ego-browser (POSIX sh) and ego-browser.cmd (Windows) that run cdp_browser.mjs with this Node."""
    folder = Path(folder)
    sh = folder / 'ego-browser'
    q = lambda s: '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`') + '"'
    sh.write_text('#!/bin/sh\nexec %s %s "$@"\n' % (q(node), q(RUNTIME)), encoding='utf-8')
    sh.chmod(0o755)
    cmd = folder / 'ego-browser.cmd'
    pct = lambda s: '"' + str(s).replace('%', '%%') + '"'
    cmd.write_text('@echo off\r\n%s %s %%*\r\n' % (pct(node), pct(RUNTIME)), encoding='utf-8')
    return cmd if os.name == 'nt' else sh


def environment_for(chosen, folder):
    env = dict(os.environ)
    if chosen['route'] == 'chrome':
        launcher = write_launchers(folder, chosen['node'])
        env['PATH'] = str(Path(folder)) + os.pathsep + env.get('PATH', '')
        env['EGO_BROWSER'] = str(launcher)
        env['CDP_BROWSER'] = chosen['browser']
    return env


def check(mode):
    chosen = plan(mode)
    if chosen['route'] == 'chrome':
        try:
            r = subprocess.run([chosen['node'], str(RUNTIME), '--check'], capture_output=True, text=True, timeout=120,
                               env=dict(os.environ, CDP_BROWSER=chosen['browser']))
            chosen['browser_check'] = json.loads((r.stdout or '').strip().splitlines()[-1])
        except (OSError, ValueError, IndexError, subprocess.SubprocessError) as error:
            chosen['browser_check'] = {'ok': False, 'problem': str(error)}
        if not chosen['browser_check'].get('ok'):
            chosen['problem'] = '浏览器起来了但不能用：' + str(chosen['browser_check'].get('problem') or chosen['browser_check'])
    return chosen


def say(chosen):
    if chosen['route'] == 'ego':
        return '出包检查用 Ego Lite（%s）。' % chosen['ego_browser']
    if chosen['route'] == 'chrome' and not chosen.get('problem'):
        extra = chosen.get('browser_check') or {}
        tail = '，WebGL：%s，帧率约 %s' % (extra.get('renderer', '?'), extra.get('fps', '?')) if extra else ''
        return '出包检查用 %s（后台运行、单独的临时资料夹，不碰你自己的浏览器）%s。' % (chosen['browser'], tail)
    return '出包检查现在跑不了：' + chosen.get('problem', '原因不明')


def main(argv=None):
    ap = argparse.ArgumentParser(description='让出包检查在任何电脑上都有浏览器可用（没有 Ego 时用 Chrome/Edge/Chromium）')
    ap.add_argument('--browser', choices=['auto', 'ego', 'chrome'], default='auto')
    ap.add_argument('--check', action='store_true', help='只说用哪个浏览器，并启动一次确认能用')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('command', nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if a.check or not command:
        chosen = check(a.browser)
        print(json.dumps(chosen, ensure_ascii=False, indent=2) if a.json else say(chosen))
        return 0 if chosen['route'] and not chosen.get('problem') else ENV_CODE
    chosen = plan(a.browser)
    if not chosen['route']:
        print('环境不完整：' + chosen['problem'], file=sys.stderr)
        return ENV_CODE
    folder = tempfile.mkdtemp(prefix='ego-compat-')
    try:
        env = environment_for(chosen, folder)
        print('[browser_env] ' + say(chosen), file=sys.stderr, flush=True)
        try:
            return subprocess.run(command, env=env).returncode
        except FileNotFoundError:
            print('找不到命令：%s（Windows 上 python3 要写成 python 或 py -3）' % command[0], file=sys.stderr)
            return ENV_CODE
    finally:
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
