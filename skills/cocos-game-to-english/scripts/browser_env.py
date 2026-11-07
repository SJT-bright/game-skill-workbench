#!/usr/bin/env python3
"""Ego-only browser-test launcher (user 2026-11-06).
Google Chrome is reserved for user trial links. Missing/stalled Ego never falls back to another browser.
The wrapper retains unique space names and reports; offline checks do not require a browser.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
MIN_NODE = 18
ENV_CODE = 2
SPACE_ENV = 'BROWSER_ENV_SPACE_PREFIX'      # <game>-<pid> of the browser_env run; space_name() builds on it
GAME_ENV = 'BROWSER_ENV_GAME'
EVENTS_ENV = 'BROWSER_ENV_EVENTS'           # JSON lines for Ego diagnostics
FALLBACK_NODE_ENV = 'BROWSER_ENV_FALLBACK_NODE'
FALLBACK_BROWSER_ENV = 'BROWSER_ENV_FALLBACK_BROWSER'
STALL_ENV = 'BROWSER_ENV_EGO_STALL_S'
DEFAULT_EGO_STALL_S = 180                   # below watched_run's 240 s, so the relay acts before the caller gives up
# Ego failures that say "Ego is stuck", not "the game failed". Matched on the error stream of a failed call only.
EGO_STUCK = re.compile(r'task ?space (?:\S+ )?not found|EGO_TASK_SPACE\w*|Target closed|Session closed|LaunchServices'
                       r'|(?:CDP|protocol|screenshot|captureScreenshot|navigat\w*|goto|page\.\w+|Page\.\w+|waitFor\w*)'
                       r'[^\n]{0,80}tim(?:ed|e)[ -]?out|tim(?:ed|e)[ -]?out[^\n]{0,80}(?:CDP|screenshot|navigat|page|goto)'
                       # R4N3 (补查2 第 1 组 1d): host-side stalls seen in 方块收割者 / 火箭三消 / 合成进化恐龙 -> preserve the first Ego host error
                       r'|(?<![\w.])-10005(?!\d)|webContents[^\n]{0,60}\bnull\b|\bnull\b[^\n]{0,60}webContents'
                       r'|Runtime\.evaluate[^\n]{0,80}tim(?:ed|e)[ -]?out|aborted before dispatch', re.I)
# R4N3: the same host-stall texts as EGO_STUCK's last line, for tools that do not run through the relay
ENV_STUCK_R4N3 = re.compile(r'(?<![\w.])-10005(?!\d)|webContents[^\n]{0,60}\bnull\b|\bnull\b[^\n]{0,60}webContents'
                            r'|Runtime\.evaluate[^\n]{0,80}tim(?:ed|e)[ -]?out|aborted before dispatch', re.I)


def env_stuck(text):
    m = ENV_STUCK_R4N3.search(text or '')
    return 'Ego 环境异常，保留未测并在 Ego 内排查：%s' % m.group(0) if m else None
GENERIC_DIRS = {'web-mobile', 'bytedance-mini-game', 'build', 'dist', 'pkg', 'package', 'source', 'src', 'scripts',
                'export', 'native', 'web', 'assets', 'tiktok', 'out', 'tmp'}


def slug(text):
    """ASCII part of a name for an Ego space; a name that lost characters (Chinese) keeps a short hash of the full
    name, so two Chinese-named games never end up with the same space name."""
    text = str(text or '').strip()
    part = re.sub(r'[^A-Za-z0-9]+', '-', text).strip('-')[:32].strip('-')
    if part != text or not part:
        part = (part + '-' if part else 'game-') + hashlib.sha1(text.encode('utf-8')).hexdigest()[:6]
    return part


def guess_game(command, cwd=None):
    """The game a command works on: the folder after --project/--package/--directory/--source/--out (skipping generic
    build folder names), else the working folder."""
    for flag in ('--project', '--package', '--directory', '--source', '--export', '--out'):
        for i, arg in enumerate(command):
            value = command[i + 1] if arg == flag and i + 1 < len(command) else (
                arg.split('=', 1)[1] if arg.startswith(flag + '=') else None)
            if value:
                p = Path(value)
                for cand in [p] + list(p.parents)[:3]:
                    name = cand.stem if cand.suffix.lower() == '.zip' else cand.name
                    if name and name.lower() not in GENERIC_DIRS:
                        return name
    return Path(cwd or os.getcwd()).name or 'game'


def space_name(purpose, game=None, pid=None, token=None, env=None):
    """Ego task-space name for one run: <game>-<pid>-<purpose>-<random>. Inside browser_env the prefix is the one it
    set (BROWSER_ENV_SPACE_PREFIX); elsewhere game (or BROWSER_ENV_GAME, or the working folder) and this process id."""
    env = os.environ if env is None else env
    prefix = env.get(SPACE_ENV)
    if not prefix:
        prefix = '%s-%d' % (slug(game or env.get(GAME_ENV) or Path.cwd().name), pid or os.getpid())
    return '%s-%s-%s' % (prefix, slug(purpose), token or secrets.token_hex(2))


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
    """Find desktop browser executables for compatibility diagnostics."""
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
    return shutil.which('ego-browser')


def plan(mode='auto'):
    if mode not in ('auto', 'ego'):
        return {'route': None, 'problem': '测试只允许 Ego（用户 2026-11-06）；--browser chrome 已停用，Chrome 仅供用户试玩。'}
    ego = find_ego()
    requested = os.environ.get('EGO_BROWSER')
    if requested and (not ego or Path(requested).resolve() != Path(ego).resolve()):
        return {'route': None, 'problem': 'EGO_BROWSER 指向非官方 Ego 启动器；移除 Chrome/Playwright 替身后重试。'}
    if not ego:
        return {'route': None, 'problem': '找不到官方 ego-browser；按 Ego Skill 处理环境，本项保留未执行，不回退 Chrome。'}
    return {'route': 'ego', 'ego_browser': ego}


def write_launchers(folder, node):
    raise ValueError('EGO_ONLY_TEST_POLICY: Chrome-as-Ego launchers are retired.')


def write_relay_launchers(folder, ego):
    """ego-browser / ego-browser.cmd that run this file as a relay in front of the real Ego (see relay())."""
    folder = Path(folder)
    q = lambda s: '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`') + '"'
    sh = folder / 'ego-browser'
    sh.write_text('#!/bin/sh\nexec %s %s --relay-ego %s -- "$@"\n' % (q(sys.executable), q(Path(__file__).resolve()), q(ego)),
                  encoding='utf-8')
    sh.chmod(0o755)
    pct = lambda s: '"' + str(s).replace('%', '%%') + '"'
    cmd = folder / 'ego-browser.cmd'
    cmd.write_text('@echo off\r\n%s %s --relay-ego %s -- %%*\r\n' % (pct(sys.executable), pct(Path(__file__).resolve()), pct(ego)),
                   encoding='utf-8')
    return cmd if os.name == 'nt' else sh


def environment_for(chosen, folder, game=None):
    if chosen.get('route') != 'ego':
        raise ValueError('EGO_ONLY_TEST_POLICY: test browser must be Ego')
    env = dict(os.environ)
    env[SPACE_ENV] = '%s-%d' % (slug(game or Path.cwd().name), os.getpid())
    env[GAME_ENV] = game or Path.cwd().name
    env[EVENTS_ENV] = str(Path(folder) / 'browser-events.jsonl')
    env['EGO_BROWSER'] = chosen['ego_browser']
    for key in (FALLBACK_NODE_ENV, FALLBACK_BROWSER_ENV): env.pop(key, None)
    return env


def _argv_for(exe):
    return [sys.executable, str(exe)] if str(exe).endswith('.py') else [str(exe)]


def read_events(path):
    rows = []
    try:
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    except (OSError, TypeError):
        pass
    return rows


def record_event(path, row):
    if not path:
        return
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except OSError:
        pass


def _pump(argv, env, data, stall, out, err):
    """Run argv, forward its output line by line. -> (exit code, stderr text, stalled seconds or None)."""
    proc = subprocess.Popen(argv, env=env, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
    moved, tail = [time.monotonic()], []

    def read(stream, sink, keep):
        for line in iter(stream.readline, ''):
            moved[0] = time.monotonic()
            sink.write(line)
            sink.flush()
            if keep:
                tail.append(line)
                del tail[:-200]
        stream.close()

    readers = [threading.Thread(target=read, args=(proc.stdout, out, False), daemon=True),
               threading.Thread(target=read, args=(proc.stderr, err, True), daemon=True)]
    for r in readers:
        r.start()
    if data is not None:
        try:
            proc.stdin.write(data)
            proc.stdin.close()
        except OSError:
            pass
    stalled = None
    while proc.poll() is None:
        time.sleep(0.1)
        if stall and time.monotonic() - moved[0] > stall:
            stalled = stall
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    for r in readers:
        r.join(5)
    return proc.returncode, ''.join(tail), stalled


def ego_stuck_reason(code, stderr_text, stalled):
    """Why this Ego call counts as "Ego stuck" or None (the result stands, pass or fail)."""
    if stalled:
        return 'Ego %d 秒没有任何输出' % stalled
    if code != 0:
        m = EGO_STUCK.search(stderr_text or '')
        if m:
            line = next((l for l in (stderr_text or '').splitlines() if m.group(0) in l), m.group(0))
            return 'Ego 报错：' + line.strip()[:200]
    return None


def relay(ego, args, env=None, stdin_data=None, stall=None, out=None, err=None):
    """Compatibility for existing Ego relays; propagate Ego's result and never spawn Chrome."""
    env = dict(os.environ if env is None else env)
    out, err = out or sys.stdout, err or sys.stderr
    if args[:1] != ['nodejs']:
        return subprocess.run(_argv_for(ego) + list(args), env=env).returncode
    if stall is None: stall = float(env.get(STALL_ENV) or DEFAULT_EGO_STALL_S)
    data = stdin_data if stdin_data is not None else (sys.stdin.read() if '-e' not in args else None)
    code, text, stalled = _pump(_argv_for(ego) + list(args), env, data, stall, out, err)
    reason = ego_stuck_reason(code, text, stalled)
    if reason:
        record_event(env.get(EVENTS_ENV), {'time': time.time(), 'kind': 'ego_error', 'reason': reason, 'route': 'ego'})
        err.write('[browser_env] Ego 测试未完成：%s；不回退 Chrome。\n' % reason)
        return code or 1
    return code


def check(mode):
    return plan(mode)


def say(chosen):
    return '浏览器测试仅用 Ego Lite（%s）。' % chosen['ego_browser'] if chosen.get('route') == 'ego' else chosen.get('problem', 'Ego 不可用，本项未执行。')


def main(argv=None):
    ap = argparse.ArgumentParser(description='浏览器测试只使用官方 Ego；Chrome 仅用于用户试玩链接')
    ap.add_argument('--browser', choices=['auto', 'ego', 'chrome'], default='auto')
    ap.add_argument('--check', action='store_true', help='只检查官方 Ego 启动器的可发现性')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--game', help='游戏名：测试空间名用它加进程号（不写就从命令里的 --project/--package 等猜）')
    ap.add_argument('--report', type=Path, help='写一份 JSON：Ego 路线、实际退出码及禁用回退状态')
    ap.add_argument('--relay-ego', help=argparse.SUPPRESS)     # used by the ego-browser launcher this script writes
    ap.add_argument('command', nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if a.relay_ego:
        official = find_ego()
        if not official or Path(a.relay_ego).resolve() != Path(official).resolve():
            print('Ego 测试只能使用 PATH 中的官方启动器。', file=sys.stderr)
            return ENV_CODE
        return relay(official, command)
    if a.check or not command:
        chosen = check(a.browser)
        print(json.dumps(chosen, ensure_ascii=False, indent=2) if a.json else say(chosen))
        return 0 if chosen['route'] and not chosen.get('problem') else ENV_CODE
    chosen = plan(a.browser)
    if not chosen['route']:
        print('环境不完整：' + chosen['problem'], file=sys.stderr)
        return finish_report(chosen, {}, ENV_CODE, a.report)
    folder = tempfile.mkdtemp(prefix='ego-compat-')
    try:
        env = environment_for(chosen, folder, a.game or guess_game(command))
        print('[browser_env] ' + say(chosen) + '测试空间名前缀：%s。' % env[SPACE_ENV], file=sys.stderr, flush=True)
        try:
            code = subprocess.run(command, env=env).returncode
        except FileNotFoundError:
            print('找不到命令：%s（Windows 上 python3 要写成 python 或 py -3）' % command[0], file=sys.stderr)
            code = ENV_CODE
        return finish_report(chosen, env, code, a.report)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def finish_report(chosen, env, code, report=None):
    if report:
        doc = {'route': chosen['route'], 'browser': chosen.get('ego_browser'), 'space_prefix': env.get(SPACE_ENV),
               'switched_to_chrome': False, 'fallbacks': [], 'fallback_available': False, 'exit_code': code,
               'browser_policy': 'ego_only_tests_20261106'}
        if not chosen['route']:
            doc.update(status='not_run', reason=chosen.get('problem'))
        Path(report).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return code


if __name__ == '__main__':
    sys.exit(main())
