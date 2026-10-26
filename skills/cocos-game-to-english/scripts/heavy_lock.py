#!/usr/bin/env python3
"""Keep two jobs from writing the same game's files at the same time. Nothing else ever waits.

User 2026-10-22 / 2026-10-23: tests must never wait. "Occupied" is never a reason to queue: open a new one.
  - Browser tests and checks (chrome_touch.py touch tests, dump_ui, recordings, timing runs, batch level runs,
    serve_preview.py, ego-browser, Playwright scripts, audit_*/check_*/test_* scripts, frame analysis) never queue:
    each run opens its own new isolated window / Ego space / preview port (see browser_slots.py). If such a command
    is wrapped in this script anyway, it runs at once without taking any lock.
  - Without --project nothing waits either (the old machine-wide lock is retired): the command runs at once.
  - Only jobs that WRITE one game's files (build/export, audio pipeline) queue, and only behind a job of the SAME game
    (--project <game folder>). Start such a job in the background and keep working; tests use the latest finished
    build through `browser_slots.py snapshot` (or serve_preview.py --snapshot) in a new window instead of waiting.
The lock is a folder in the user's home directory, so it works across Codex sessions. Windows / macOS / Linux.

  python heavy_lock.py run --project <game> --name "web build" -- <command> [args...]
  python heavy_lock.py run --project <game> --name "web build" --no-wait -- <command>   # busy -> exit 75 at once
  python heavy_lock.py status [--project <game>]
  python heavy_lock.py release --force [--project <game>]   # only if a holder is known to be gone

When it does queue it prints at once who holds the game, then one line per minute (the script waits, the model does
not poll and does not tell the user it is waiting). Exit code: the command's own exit code; 3 if the same game stayed
busy longer than --timeout minutes; 75 with --no-wait when busy.
Only a lock with a recorded owner process that no longer exists may be retired. Age is diagnostic only;
a live or unknown owner is never displaced, including by release --force.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import hashlib

LOCK_ROOT = Path(os.environ.get('GAME_SKILL_LOCK_DIR', Path.home() / '.game-skill-locks'))
LOCK = LOCK_ROOT / 'heavy'
# user 2026-10-22/23: browser tests and read-only checks never queue (each opens its own new window / port)
BROWSER_TESTS = ('chrome_touch.py', 'serve_preview.py', 'prepare_preview.py', 'browser_slots.py', 'cleanup_machine.py',
                 'audit_frame_glitches.py', 'make_contact_sheet.py', 'preflight.py', 'art_check.py', 'ui_dump.js',
                 'input_observer.js', 'checkin_harness.mjs', 'league_harness.mjs', 'modules_harness.mjs', 'ego-browser', 'ego-browser.exe')
TEST_PREFIXES = ('audit_', 'check_', 'test_', 'plan_level_tests')
TEST_WORDS = ('playwright', 'chrome_touch', 'ego-browser')   # whole word or inside a script name


def is_test(cmd):
    for part in cmd:
        name = Path(str(part)).name.lower()
        script = name.endswith(('.py', '.js', '.mjs', '.cjs', '.ts'))
        if name in BROWSER_TESTS or (script and name.startswith(TEST_PREFIXES)) or name in TEST_WORDS \
                or (script and any(w in name for w in TEST_WORDS)):
            return True
    return False


def project_lock(path):
    key = hashlib.sha1(str(Path(path).resolve()).lower().encode('utf-8')).hexdigest()[:12]
    return LOCK_ROOT / ('project-' + key)


def alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259                              # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def holder():
    try:
        return json.loads((LOCK / 'owner.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def try_acquire(name, stale_hours):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    try:
        LOCK.mkdir()
    except FileExistsError:
        h = holder()
        # Missing/unfinished owner metadata is not proof of abandonment.
        # A live writer keeps its lock regardless of age (--stale is diagnostic only).
        if h is None or not isinstance(h.get('pid'), int) or h['pid'] <= 0 or alive(h['pid']):
            return False
        if not release(expected=h):
            return False
        try:
            LOCK.mkdir()
        except FileExistsError:
            return False
    info = {'pid': os.getpid(), 'name': name, 'started': datetime.now(timezone.utc).isoformat(),
            'started_ts': time.time(), 'cwd': os.getcwd()}
    (LOCK / 'owner.json').write_text(json.dumps(info, ensure_ascii=False), encoding='utf-8')
    return True


def release(expected=None):
    h = holder()
    if not LOCK.exists():
        return True
    if h is None or not isinstance(h.get('pid'), int) or h['pid'] <= 0:
        return False
    if expected is not None and h != expected:
        return False
    # Only this invocation may release its own live lock. No force path can
    # release another live owner, even when its timestamp is old.
    if h['pid'] != os.getpid() and alive(h['pid']):
        return False
    try:
        (LOCK / 'owner.json').unlink()
        LOCK.rmdir()
    except OSError:
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='action', required=True)
    r = sub.add_parser('run')
    r.add_argument('--name', required=True, help='short label shown to other sessions, e.g. "web build"')
    r.add_argument('--project', help='game folder: a job that writes this game (build, audio) queues only behind the same game')
    r.add_argument('--kind', choices=('auto', 'test', 'write'), default='auto',
                   help='test = never queue; write = queue behind the same game; auto = decide from the command')
    r.add_argument('--no-wait', action='store_true', help='if the same game is busy, exit 75 at once instead of queueing')
    r.add_argument('--timeout', type=float, default=45, help='minutes to wait for the lock')
    r.add_argument('--stale', type=float, default=3, help='diagnostic age threshold in hours; never displaces a live or unknown owner')
    r.add_argument('command', nargs=argparse.REMAINDER)
    st = sub.add_parser('status')
    st.add_argument('--project')
    rel = sub.add_parser('release')
    rel.add_argument('--force', action='store_true')
    rel.add_argument('--project')
    a = ap.parse_args()
    global LOCK
    if getattr(a, 'project', None):
        LOCK = project_lock(a.project)

    if a.action == 'status':
        h = holder()
        if h and alive(h.get('pid')):
            print(json.dumps({'busy': True, 'age_hours': max(0, (time.time() - h.get('started_ts', time.time())) / 3600), **h}, ensure_ascii=False))
        else:
            print(json.dumps({'busy': LOCK.exists(), 'owner_review_required': LOCK.exists() and h is None}))
        return 0
    if a.action == 'release':
        h = holder()
        if h and alive(h.get('pid')):
            print(json.dumps({'released': False, 'reason': 'holder still running; age and --force do not authorize displacement', **h}, ensure_ascii=False))
            return 1
        released = release(expected=h)
        print(json.dumps({'released': released, 'reason': None if released else 'owner unknown or changed; current review required'}))
        return 0 if released else 1

    cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not cmd:
        ap.error('give the command after --')
    if a.kind == 'test' or (a.kind == 'auto' and is_test(cmd)):
        print('浏览器测试/检查不排队（用户 2026-10-22/23）：直接在自己新开的独立窗口里运行，不等任何锁', flush=True)
        return subprocess.run(cmd).returncode
    if not getattr(a, 'project', None):
        print('没写 --project：不排队、直接运行（全机锁已取消，用户 2026-10-23：不同游戏、不同会话从不互相等）', flush=True)
        return subprocess.run(cmd).returncode
    deadline = time.time() + a.timeout * 60
    last_note = 0
    while not try_acquire(a.name, a.stale):
        h = holder() or {}
        if a.no_wait:
            print(json.dumps({'status': 'same_game_write_busy', 'held_by': h.get('name'), 'since': h.get('started'),
                              'live_owner_exceeds_stale': bool(h and alive(h.get('pid')) and (time.time() - h.get('started_ts', time.time())) / 3600 >= a.stale),
                              'next': 'do not wait: test the latest finished build in a new window '
                                      '(serve_preview.py --snapshot), rerun this write job later in the background'},
                             ensure_ascii=False), flush=True)
            return 75
        if time.time() > deadline:
            print(json.dumps({'status': 'busy_timeout', 'held_by': h.get('name'), 'since': h.get('started')}, ensure_ascii=False))
            return 3
        if time.time() - last_note > 60:
            if not last_note:
                print(json.dumps({'status': 'queued_behind_same_game', 'held_by': h.get('name'), 'since': h.get('started'),
                                  'meanwhile': 'this command waits by itself; keep working. Tests do not wait for it: '
                                               'serve_preview.py --snapshot serves the latest finished build in a new window'},
                                 ensure_ascii=False), flush=True)
            print(f"⏳ 同一个游戏正在写文件：「{h.get('name', '?')}」（开始于 {h.get('started', '?')}）；本命令自己排队，模型继续干别的", flush=True)
            last_note = time.time()
        time.sleep(3)
    try:
        return subprocess.run(cmd).returncode
    finally:
        h = holder()
        if h and h.get('pid') == os.getpid():
            release(expected=h)


if __name__ == '__main__':
    sys.exit(main())
