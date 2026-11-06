#!/usr/bin/env python3
"""Run a pack command with a browser the packaging checks can drive, on any computer (English pack 10.2.10).

Saul 2026-10-31: the English Skill is used on other people's computers, so no step may depend on Ego Lite. The pack's
browser checks (ad_regression.py, runtime_regression.py and the writers that call them, serve_preview.py --keep,
chrome_touch.py) look for `ego-browser`. This wrapper:
  * Ego found (`ego-browser` on PATH or EGO_BROWSER set): the checks use Ego (Saul's own Mac keeps using Ego), through
    the relay below that switches a stuck call to Chrome/Edge.
  * no Ego: puts a launcher named ego-browser (ego-browser.cmd on Windows) on PATH and sets EGO_BROWSER to it. The
    launcher runs cdp_browser.mjs with Node, which drives an ordinary Chrome, Edge or Chromium: headless, its own
    temporary profile, never the user's own browser windows or profile. Checks and verdicts stay the same.
  * neither works: says in plain words what is missing and exits 2 (the packaging tools' exit code for 环境不完整).

  python3 browser_env.py -- <command ...>             e.g. python3 browser_env.py -- python3 build_checked_zip.py ...
  python3 browser_env.py --browser chrome -- <cmd>    use Chrome/Edge even when Ego is installed (Ego not working)
  python3 browser_env.py --check                      say which browser the checks will use; start it once
  python3 browser_env.py --game <名字> --report r.json -- <cmd>   name the test spaces; write which browser really ran
Windows: use `python` (or `py -3`) instead of `python3`.

生成时预防 P21 (2026-11-04 普查: Ego 卡死 / 空间冲突 45 次):
  * Own space names. Every command run here gets BROWSER_ENV_SPACE_PREFIX = <game>-<this process id>; tools that open
    an Ego space take their name from space_name() (ad_regression.py does), so two sessions never share one space
    (Ego taskSpace(name) resumes a same-name space and one run's finish() closed the other's pages).
  * Ego stuck -> Chrome. With Ego, the pack's tools still find `ego-browser`, but it is a small relay: when one
    `ego-browser nodejs` call fails with an Ego timeout / lost space (screenshot or page timed out, task space not found,
    target closed) or prints nothing for BROWSER_ENV_EGO_STALL_S seconds (default 180), the same call is run again at
    once on Chrome/Edge, and every later call of this command goes straight to Chrome. Ego itself is never quit or
    restarted (that would break other sessions). The switch is printed and written to --report (fallbacks).
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
RUNTIME = HERE / 'cdp_browser.mjs'
MIN_NODE = 18
ENV_CODE = 2
SPACE_ENV = 'BROWSER_ENV_SPACE_PREFIX'      # <game>-<pid> of the browser_env run; space_name() builds on it
GAME_ENV = 'BROWSER_ENV_GAME'
EVENTS_ENV = 'BROWSER_ENV_EVENTS'           # JSON lines: one row per Ego -> Chrome switch
FALLBACK_NODE_ENV = 'BROWSER_ENV_FALLBACK_NODE'
FALLBACK_BROWSER_ENV = 'BROWSER_ENV_FALLBACK_BROWSER'
STALL_ENV = 'BROWSER_ENV_EGO_STALL_S'
DEFAULT_EGO_STALL_S = 180                   # below watched_run's 240 s, so the relay acts before the caller gives up
# Ego failures that say "Ego is stuck", not "the game failed". Matched on the error stream of a failed call only.
EGO_STUCK = re.compile(r'task ?space (?:\S+ )?not found|EGO_TASK_SPACE\w*|Target closed|Session closed|LaunchServices'
                       r'|(?:CDP|protocol|screenshot|captureScreenshot|navigat\w*|goto|page\.\w+|Page\.\w+|waitFor\w*)'
                       r'[^\n]{0,80}tim(?:ed|e)[ -]?out|tim(?:ed|e)[ -]?out[^\n]{0,80}(?:CDP|screenshot|navigat|page|goto)'
                       # R4N3 (补查2 第 1 组 1d): host-side stalls seen in 方块收割者 / 火箭三消 / 合成进化恐龙 -> 环境卡住，换 Chrome 重试
                       r'|(?<![\w.])-10005(?!\d)|webContents[^\n]{0,60}\bnull\b|\bnull\b[^\n]{0,60}webContents'
                       r'|Runtime\.evaluate[^\n]{0,80}tim(?:ed|e)[ -]?out|aborted before dispatch', re.I)
# R4N3: the same host-stall texts as EGO_STUCK's last line, for tools that do not run through the relay
ENV_STUCK_R4N3 = re.compile(r'(?<![\w.])-10005(?!\d)|webContents[^\n]{0,60}\bnull\b|\bnull\b[^\n]{0,60}webContents'
                            r'|Runtime\.evaluate[^\n]{0,80}tim(?:ed|e)[ -]?out|aborted before dispatch', re.I)


def env_stuck(text):
    """R4N3: '环境卡住，换 Chrome 重试：<原文>' when `text` carries a host stall (-10005, webContents null,
    Runtime.evaluate timeout, aborted before dispatch), else None."""
    m = ENV_STUCK_R4N3.search(text or '')
    return '环境卡住，换 Chrome 重试：%s' % m.group(0) if m else None
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
    env = dict(os.environ)
    env[SPACE_ENV] = '%s-%d' % (slug(game or Path.cwd().name), os.getpid())
    env[GAME_ENV] = game or Path.cwd().name
    env[EVENTS_ENV] = str(Path(folder) / 'browser-events.jsonl')
    if chosen['route'] == 'chrome':
        launcher = write_launchers(folder, chosen['node'])
        env['PATH'] = str(Path(folder)) + os.pathsep + env.get('PATH', '')
        env['EGO_BROWSER'] = str(launcher)
        env['CDP_BROWSER'] = chosen['browser']
    elif chosen['route'] == 'ego':
        launcher = write_relay_launchers(folder, chosen['ego_browser'])
        env['PATH'] = str(Path(folder)) + os.pathsep + env.get('PATH', '')
        env['EGO_BROWSER'] = str(launcher)
        spare = plan('chrome')                  # who takes over when Ego gets stuck; none -> Ego's result stands
        if spare['route'] == 'chrome':
            env[FALLBACK_NODE_ENV], env[FALLBACK_BROWSER_ENV] = spare['node'], spare['browser']
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
    """Why this Ego call counts as "Ego stuck" (switch to Chrome), or None (the result stands, pass or fail)."""
    if stalled:
        return 'Ego %d 秒没有任何输出' % stalled
    if code != 0:
        m = EGO_STUCK.search(stderr_text or '')
        if m:
            line = next((l for l in (stderr_text or '').splitlines() if m.group(0) in l), m.group(0))
            return 'Ego 报错：' + line.strip()[:200]
    return None


def relay(ego, args, env=None, stdin_data=None, stall=None, out=None, err=None):
    """Stand in front of the real Ego for one `ego-browser ...` call. Only `nodejs` calls can switch: an Ego timeout,
    a lost space or a silent Ego reruns the same call on Chrome/Edge (cdp_browser.mjs); after one switch every later
    call of this browser_env run goes to Chrome directly. Ego itself is never quit or restarted."""
    env = dict(os.environ if env is None else env)
    out, err = out or sys.stdout, err or sys.stderr
    if args[:1] != ['nodejs']:
        return subprocess.run(_argv_for(ego) + list(args), env=env).returncode
    if stall is None:
        try:
            stall = float(env.get(STALL_ENV) or DEFAULT_EGO_STALL_S)
        except ValueError:
            stall = DEFAULT_EGO_STALL_S
    data = None
    if '-e' not in args:                        # the script comes on stdin (chrome_touch.py): keep it for a rerun
        data = stdin_data if stdin_data is not None else sys.stdin.read()
    events = env.get(EVENTS_ENV)
    node, browser = env.get(FALLBACK_NODE_ENV), env.get(FALLBACK_BROWSER_ENV)
    chrome_env = dict(env, CDP_BROWSER=browser or '')
    chrome_argv = (_argv_for(node) + [str(RUNTIME)] + list(args)) if node and browser else None
    if chrome_argv and any(r.get('to') == 'chrome' for r in read_events(events)):
        record_event(events, {'time': time.time(), 'kind': 'sticky', 'to': 'chrome', 'call': ' '.join(args[:2])})
        return _pump(chrome_argv, chrome_env, data, None, out, err)[0]
    code, text, stalled = _pump(_argv_for(ego) + list(args), env, data, stall, out, err)
    reason = ego_stuck_reason(code, text, stalled)
    if reason is None:
        return code
    if not chrome_argv:
        err.write('[browser_env] Ego 卡住了（%s），这台电脑没有能接手的 Chrome/Edge 和 Node.js，只能按 Ego 这次的结果算。\n' % reason)
        return code if code else 1
    record_event(events, {'time': time.time(), 'kind': 'switch', 'from': 'ego', 'to': 'chrome', 'reason': reason,
                          'call': ' '.join(args[:2]), 'ego_exit': code})
    err.write('[browser_env] Ego 卡住了（%s）：这一步马上改用 Chrome 从头再跑一遍，后面的步骤也直接用 Chrome。'
              'Ego 本身不退出、不重启；上面 Ego 那次的输出作废。\n' % reason)
    err.flush()
    return _pump(chrome_argv, chrome_env, data, None, out, err)[0]


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
    ap.add_argument('--game', help='游戏名：测试空间名用它加进程号（不写就从命令里的 --project/--package 等猜）')
    ap.add_argument('--report', type=Path, help='写一份 JSON：实际用了哪个浏览器、有没有从 Ego 换到 Chrome')
    ap.add_argument('--relay-ego', help=argparse.SUPPRESS)     # used by the ego-browser launcher this script writes
    ap.add_argument('command', nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if a.relay_ego:
        return relay(a.relay_ego, command)
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
    """Say whether Ego was swapped for Chrome during the command; write --report. Returns the command's exit code."""
    rows = read_events(env.get(EVENTS_ENV))
    switches = [r for r in rows if r.get('kind') == 'switch']
    if switches:
        print('[browser_env] 换过浏览器：Ego 卡住 %d 次（第一次：%s），之后 %d 步直接用 Chrome 跑完。结果以 Chrome 那次为准。'
              % (len(switches), switches[0].get('reason'), sum(1 for r in rows if r.get('kind') == 'sticky')),
              file=sys.stderr, flush=True)
    if report:
        doc = {'route': chosen['route'], 'browser': chosen.get('ego_browser') or chosen.get('browser'),
               'space_prefix': env.get(SPACE_ENV), 'switched_to_chrome': bool(switches), 'fallbacks': rows,
               'fallback_available': bool(env.get(FALLBACK_NODE_ENV)) or chosen['route'] == 'chrome', 'exit_code': code}
        Path(report).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return code


if __name__ == '__main__':
    sys.exit(main())
