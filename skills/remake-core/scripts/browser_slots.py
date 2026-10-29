#!/usr/bin/env python3
"""Browser tests never wait: an occupied window/space/preview is never waited for, a new one is opened (user 2026-10-23).

Every test run gets its OWN fresh resource:
  - touch_run  : one chrome_touch.py run = one new isolated window (context) inside Ego Lite (registered automatically)
  - ego_space  : one Ego Lite TaskSpace opened by this session for manual Page work (register it after creating it)
  - preview    : one serve_preview.py local server on its own free port (registered automatically)
Before opening anything new, `sweep --close` checks registered slots. Gone owners are retired; explicitly completed
process slots close only after current process-identity matching. Live-idle and old Ego IDs become review candidates,
not automatic kills or blind takeovers. Explicitly kept user previews do not expire by age. Slots that are still working (another
session's running test, the user's trial window) are never touched. So many windows may run at once, and the old
ones do not pile up and eat memory.

  python browser_slots.py sweep [--close]          # see / close free old slots (run before every new window)
  python browser_slots.py register --kind ego_space --space-id 123 --name "测试线 音量复核" [--project <game>]
  python browser_slots.py heartbeat --id <slot>    # optional: mark an ego_space as still in use
  python browser_slots.py close --id <slot>        # stop identity-matched helpers; confirm already-finished Ego
                                                   # spaces absent before unregistering; CLI `release` = same
  python browser_slots.py close --name "测试线"    # close everything this line opened (all Ego windows/spaces; only
                                                   # a --keep preview = the user's Codex trial link stays
                                                   # unless --include-keep)
  python browser_slots.py ego-list                 # every Ego TaskSpace (to find ones left "waiting for the user")
  python browser_slots.py ego-finish --space-id 12 34   # verify spaces already finished by their current owner are absent
  python browser_slots.py check --name "测试线"    # exit 1 while this line still has a window/space/preview open
  python browser_slots.py list
  python browser_slots.py snapshot --from <web export dir>   # private copy of the latest finished web build
Close after use (user 2026-10-23): in EVERY stage, as soon as a test is finished, the session closes the Ego
windows / TaskSpaces / previews it opened for that test itself — do not leave them for a later sweep. Before saying a
test is done (or writing the handoff), `check --name <line>` must exit 0.
Ego is ONLY for the agent's own tests (user 2026-10-23): no Ego window or TaskSpace is ever opened, kept, brought to
front or handed off for the user to play. The user plays in Codex's local preview (serve_preview.py --keep; that
preview is the only thing --keep is allowed for). A waiting label is only a review candidate: verify current ownership,
use the owner's existing supported task binding to finish unused spaces, then ego-finish confirms absence.
Exit code 0 (register prints the new slot id; check exits 1 while something is still open; close exits 2 when an
resource could not be confirmed closed; its record stays pending for the current owner). Windows / macOS / Linux. Registry: ~/.game-skill-locks/browser-slots
(override with GAME_SKILL_LOCK_DIR).
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get('GAME_SKILL_LOCK_DIR', Path.home() / '.game-skill-locks'))
SLOTS = ROOT / 'browser-slots'
SNAPSHOTS = ROOT / 'web-snapshots'
KINDS = ('touch_run', 'ego_space', 'preview')
# Heartbeat age identifies review candidates; it does not authorize closing a live task.
IDLE_MIN = {'touch_run': 20, 'ego_space': 30, 'preview': 30}
KEEP_MAX_HOURS = None                    # explicit user trial retention is not revoked by age
KEEP_KINDS = ('preview',)                # only Codex user preview may be kept
SNAPSHOT_MAX_HOURS = 3                   # unreferenced build snapshots older than this are deleted


def alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def process_identity(pid):
    """Fingerprint current PID start time and command; never treat historical PID + alive as ownership."""
    if not alive(pid):
        return None
    try:
        if os.name == 'nt':
            ps = '$p=Get-CimInstance Win32_Process -Filter "ProcessId = %d"; if($p){ "$($p.CreationDate.ToUniversalTime().Ticks)|$($p.ExecutablePath)|$($p.CommandLine)" }' % pid
            r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, timeout=5)
        else:
            r = subprocess.run([shutil.which('ps') or '/bin/ps', '-p', str(pid), '-o', 'lstart=', '-o', 'command='], capture_output=True, text=True, timeout=5)
        value = r.stdout.strip()
        if r.returncode or not value:
            return None
        import hashlib
        return hashlib.sha256(value.encode('utf-8')).hexdigest()
    except (OSError, subprocess.SubprocessError):
        return None


def terminate(pid, expected_identity=None):
    # No signal when identity is missing/reused, no whole-process-tree or force termination.
    if not expected_identity or process_identity(pid) != expected_identity:
        return False
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        for _ in range(15):
            if not alive(pid):
                return True
            current_identity = process_identity(pid)
            if current_identity and current_identity != expected_identity:
                return True                       # a different, nonempty identity proves the original instance is gone
            if os.name != 'nt':
                state = subprocess.run([shutil.which('ps') or '/bin/ps', '-p', str(pid), '-o', 'stat='], capture_output=True, text=True).stdout.strip()
                if state.startswith('Z'):
                    return True
            time.sleep(.1)
        return False
    except OSError:
        return False


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex[:6] + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tmp, path)


def _read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def slots():
    out = []
    if SLOTS.is_dir():
        for p in sorted(SLOTS.glob('*.json')):
            d = _read(p)
            if isinstance(d, dict) and d.get('id'):
                out.append(d)
    return out


def register(kind, name='', pid=None, project=None, space_id=None, port=None, url=None, directory=None, keep=False):
    if kind not in KINDS:
        raise ValueError('kind must be one of ' + ', '.join(KINDS))
    if keep and kind not in KEEP_KINDS:
        raise ValueError('Ego windows and spaces are only for the agent\'s own tests and are never kept for the user '
                         '(user 2026-10-23); give the user the local preview link in Codex (serve_preview.py --keep)')
    now = time.time()
    sid = datetime.now().strftime('%m%d-%H%M%S') + '-' + kind + '-' + uuid.uuid4().hex[:6]
    data = {'id': sid, 'kind': kind, 'name': name, 'pid': pid, 'project': str(Path(project).resolve()) if project else None,
            'space_id': space_id, 'port': port, 'url': url, 'dir': str(directory) if directory else None, 'keep': bool(keep),
            'process_identity': process_identity(pid) if pid else None,
            'created': datetime.now(timezone.utc).isoformat(), 'created_ts': now, 'heartbeat_ts': now, 'state': 'running'}
    _write(SLOTS / (sid + '.json'), data)
    return sid


def heartbeat(sid, **fields):
    path = SLOTS / (sid + '.json')
    d = _read(path)
    if not d:
        return False
    d.update({k: v for k, v in fields.items() if v is not None})
    d['heartbeat_ts'] = fields.get('heartbeat_ts') or time.time()
    _write(path, d)
    return True


def release(sid):
    d = _read(SLOTS / (sid + '.json'))
    if d and d.get('dir') and _is_snapshot(d['dir']):
        shutil.rmtree(d['dir'], ignore_errors=True)
    try:
        (SLOTS / (sid + '.json')).unlink()
    except OSError:
        pass
    return bool(d)


def _is_snapshot(path):
    try:
        return Path(path).resolve().is_relative_to(SNAPSHOTS.resolve())
    except (OSError, ValueError):
        return False


def why_free(d, now=None):
    """Return the reason this slot is free (may be closed), or None while it is still working."""
    now = now or time.time()
    idle_min = (now - (d.get('heartbeat_ts') or d.get('created_ts') or 0)) / 60
    age_h = (now - (d.get('created_ts') or 0)) / 3600
    if d.get('cleanup_pending'):
        return 'browser cleanup not confirmed; current owner review required'
    if d.get('state') == 'done':
        return 'marked done'
    if d.get('keep') and d.get('kind') not in KEEP_KINDS:
        return 'Ego window kept for the user: not allowed, the user plays in Codex\'s local preview'
    if d.get('kind') in ('touch_run', 'preview'):
        if not alive(d.get('pid')):
            return 'owner process gone'
        if d.get('keep'):
            return None
        return 'stuck: no activity for %d min' % idle_min if idle_min > IDLE_MIN[d['kind']] else None
    if d.get('keep'):
        return None
    return 'idle %d min' % idle_min if idle_min > IDLE_MIN['ego_space'] else None


def ego_finish_script(space_id):
    return ('const task = await taskSpace(%d);\nawait task.finish({ keep: [] });\nconsole.log("ego-space-finished %d");\n'
            % (space_id, space_id))


def finish_ego_space(space_id):
    """Confirm absence without claiming an old numeric ID or bypassing current user/tool control.

    The owning Agent finishes its bound task with the supported Ego API first, then reruns close.
    A registry record alone never authorizes taskSpace(ID) takeover.
    """
    observed = ego_list().get('spaces')
    if isinstance(observed, list):
        ids = []
        for space in observed:
            if not isinstance(space, dict):
                return 'manual'
            sid = next((space[k] for k in ('id', 'spaceId', 'space_id') if k in space), None)
            if sid is None:
                return 'manual'
            ids.append(str(sid))
        if str(space_id) not in ids:
            return 'confirmed_absent'
    return 'manual'


def close_slot(d):
    """Really close what a slot stands for (not just forget it): finish the Ego space, stop the owner process."""
    item = {'id': d['id'], 'kind': d['kind'], 'name': d.get('name')}
    if d.get('cleanup_pending'):
        item.update(closed=False, reason='browser cleanup pending; verify the original context with the owning Agent')
        return item
    if d['kind'] in ('touch_run', 'preview') and alive(d.get('pid')):
        if d.get('pid') == os.getpid():
            item.update(closed=False, reason='owner must finish its cleanup before unregistering')
            return item
        item['terminated'] = terminate(d['pid'], d.get('process_identity'))
        if not item['terminated']:
            item.update(closed=False, reason='process identity mismatch or original process still running')
            return item
        current = _read(SLOTS / (d['id'] + '.json'))
        if current and current.get('cleanup_pending'):
            item.update(closed=False, reason='helper exited but browser context cleanup is unconfirmed')
            return item
    if d['kind'] == 'ego_space' and d.get('space_id') is not None:
        item['ego'] = finish_ego_space(d['space_id'])
        if item['ego'] == 'manual':
            item.update(closed=False, reason='Verify current ownership/control with the supported Ego API; '
                        'finish the bound completed task, verify disappearance, then rerun close. Stop on hard stop.')
            return item
    release(d['id'])
    item['closed'] = True
    return item


def mine(name=None, sid=None, include_keep=False):
    """Slots of one test line: exact id, or name equal to / starting with the line name."""
    out = []
    for d in slots():
        if sid and d['id'] == sid:
            out.append(d)
        elif name and (d.get('name') or '').startswith(name) and (include_keep or not d.get('keep') or d.get('kind') not in KEEP_KINDS):
            out.append(d)
    return out


def close(name=None, sid=None, include_keep=False):
    results = [close_slot(d) for d in mine(name, sid, include_keep)]
    closed = [x for x in results if x.get('closed')]
    pending = [x for x in results if not x.get('closed')]
    kept = [{'id': d['id'], 'name': d.get('name')} for d in mine(name, include_keep=True) if d.get('keep')] if name and not include_keep else []
    # (mine() already returned old --keep Ego slots: they are never kept)
    manual = [c for c in pending if c.get('ego') == 'manual']
    return {'closed': closed, 'cleanup_pending': pending, 'ego_spaces_to_finish_by_hand': manual, 'kept_user_trial_preview': kept,
            'rule': 'Close what a test opened as soon as the test is done, in every stage. '
                    + ('Pending resources remain registered; use their supported owner API, then rerun close.'
                       if pending else 'No unkept resources left registered for this line.')}


def check(name):
    left = [{'id': d['id'], 'kind': d['kind'], 'name': d.get('name'), 'keep': bool(d.get('keep'))} for d in mine(name, include_keep=True)]
    return {'still_open': left, 'ok': not [x for x in left if not (x['keep'] and x['kind'] in KEEP_KINDS)],
            'rule': 'Before reporting the test as done: close every window / Ego space / preview this line opened '
                    '(browser_slots.py close --name <line>); only the local preview link given to the user in Codex '
                    '(serve_preview.py --keep) may stay. No Ego window is ever left for the user.'}


def ego_list_script():
    return 'const spaces = await listTaskSpaces();\nconsole.log(JSON.stringify(spaces));\n'


def ego_list():
    """Every Ego TaskSpace as ego-browser reports it (field names follow `ego-browser skill`)."""
    exe = shutil.which('ego-browser')
    out = {'rule': 'Read-only inventory. Names and waiting labels do not establish ownership or permission to close. '
                   'The current owner verifies control and finishes its unused bound task with the supported API; '
                   'ego-finish then confirms absence. User activity, unknown ownership and hard stops remain protected.',
           'registered_running': [{'space_id': d.get('space_id'), 'name': d.get('name')} for d in slots()
                                  if d.get('kind') == 'ego_space' and why_free(d) is None]}
    if not exe:
        out.update(spaces=None, ego_browser_nodejs=ego_list_script())
        return out
    try:
        r = subprocess.run([exe, 'nodejs'], input=ego_list_script(), capture_output=True, text=True, timeout=40)
        # ego-browser nodejs currently prints console.log to stderr on macOS.
        line = [x for x in (r.stdout + '\n' + r.stderr).splitlines() if x.strip().startswith('[')]
        observed = json.loads(line[-1]) if r.returncode == 0 and line else None
        out['spaces'] = observed if isinstance(observed, list) else None
        if out['spaces'] is None:
            out.update(ego_browser_nodejs=ego_list_script(), output=r.stdout[-2000:] + r.stderr[-1000:])
    except (OSError, subprocess.SubprocessError, ValueError):
        out.update(spaces=None, ego_browser_nodejs=ego_list_script())
    return out


def ego_finish(space_ids):
    done = []
    for sid in space_ids:
        res = finish_ego_space(sid)
        item = {'space_id': sid, 'ego': res}
        if res == 'manual':
            item['reason'] = ('No ownership takeover: the owning Agent must finish its bound completed task '
                              'through the supported Ego API and verify disappearance before retrying.')
        else:
            for d in slots():
                if d.get('kind') == 'ego_space' and str(d.get('space_id')) == str(sid):
                    release(d['id'])
        done.append(item)
    pending = [x for x in done if x['ego'] == 'manual']
    return {'finished': done, 'cleanup_pending': pending, 'ego_spaces_to_finish_by_hand': pending}


def ram():
    total = free = None
    try:
        if sys.platform.startswith('linux'):
            info = dict(line.split(':', 1) for line in open('/proc/meminfo'))
            total = int(info['MemTotal'].split()[0]) / 1024
            free = int(info.get('MemAvailable', info['MemFree']).split()[0]) / 1024
        elif sys.platform == 'darwin':
            total = int(subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout) / 2 ** 20
            vm = subprocess.run(['vm_stat'], capture_output=True, text=True).stdout
            page = int(re.search(r'page size of (\d+)', vm).group(1))
            pages = sum(int(re.search(k + r':\s+(\d+)', vm).group(1)) for k in ('Pages free', 'Pages inactive', 'Pages speculative'))
            free = pages * page / 2 ** 20
        elif os.name == 'nt':
            out = subprocess.run(['powershell', '-NoProfile', '-Command',
                                  '$o=Get-CimInstance Win32_OperatingSystem; "$($o.TotalVisibleMemorySize) $($o.FreePhysicalMemory)"'],
                                 capture_output=True, text=True).stdout.split()
            total, free = int(out[0]) / 1024, int(out[1]) / 1024
    except (OSError, ValueError, KeyError, AttributeError, IndexError):
        pass
    return total, free


def soft_cap(total_mb):
    gb = (total_mb or 16384) / 1024
    return 4 if gb <= 16.5 else 6 if gb <= 48.5 else 8


def sweep(close=False):
    now = time.time()
    active, freed, ego_manual, review = [], [], [], []
    for d in slots():
        reason = why_free(d, now)
        if reason is None:
            active.append({'id': d['id'], 'kind': d['kind'], 'name': d.get('name'), 'pid': d.get('pid'),
                           'port': d.get('port'), 'space_id': d.get('space_id'),
                           'minutes': round((now - d.get('created_ts', now)) / 60)})
            continue
        item = {'id': d['id'], 'kind': d['kind'], 'name': d.get('name'), 'reason': reason}
        if close:
            if d.get('cleanup_pending'):
                item['action'] = 'original browser cleanup unconfirmed; not retired by helper PID exit'
                review.append(item)
                continue
            if d['kind'] in ('touch_run', 'preview') and alive(d.get('pid')):
                # Idle heartbeat is only a candidate: a live test/user task may be waiting normally.
                if d.get('state') != 'done':
                    item['action'] = 'review live idle resource; not closed by age alone'
                    review.append(item)
                    continue
                item['terminated'] = terminate(d['pid'], d.get('process_identity'))
                if not item['terminated']:
                    item['action'] = 'process identity missing or changed; not closed'
                    review.append(item)
                    continue
                current = _read(SLOTS / (d['id'] + '.json'))
                if current and current.get('cleanup_pending'):
                    item['action'] = 'helper exited but browser cleanup remains pending'
                    review.append(item)
                    continue
            if d['kind'] == 'ego_space' and d.get('space_id') is not None:
                # Sweeps do not claim or probe old spaces. The owning Agent verifies them explicitly.
                item['ego'] = 'manual'
                ego_manual.append({'space_id': d['space_id'], 'name': d.get('name'),
                                   'reason': 'Verify current ownership and user activity through supported Ego API; stop on hard stop.'})
                review.append(item)
                continue
            release(d['id'])
        freed.append(item)
    # build snapshots nobody serves any more
    removed_snapshots = []
    if close and SNAPSHOTS.is_dir():
        used = {str(Path(d['dir']).resolve()) for d in slots() if d.get('dir')}
        for p in SNAPSHOTS.iterdir():
            try:
                old = (now - p.stat().st_mtime) / 3600 > SNAPSHOT_MAX_HOURS
            except OSError:
                continue
            if p.is_dir() and str(p.resolve()) not in used and old:
                shutil.rmtree(p, ignore_errors=True)
                removed_snapshots.append(p.name)
    total, free = ram()
    cap = soft_cap(total)
    windows = sum(1 for a in active if a['kind'] in ('touch_run', 'ego_space'))
    return {'active': active, 'freed' if close else 'free_not_closed': freed, 'ego_spaces_to_finish_by_hand': ego_manual,
            'review_candidates_not_closed': review, 'removed_snapshots': removed_snapshots, 'active_windows': windows, 'soft_cap_windows': cap,
            'ram_mb': round(total) if total else None, 'free_ram_mb': round(free) if free else None,
            'rule': 'Never wait for an occupied window, Ego space or preview: open a new one now. '
                    + ('Over the soft cap: close this line\'s own finished windows, then still open the new one.'
                       if windows >= cap else 'Room for more windows.')}


def snapshot(source):
    """Copy a finished web export to a fresh private folder so a running build cannot change it under the test."""
    src = Path(source).resolve()
    if not (src / 'index.html').is_file():
        raise SystemExit('index.html not found in ' + str(src) + ' (give the finished web export folder)')
    dest = SNAPSHOTS / (datetime.now().strftime('%m%d-%H%M%S') + '-' + src.name + '-' + uuid.uuid4().hex[:6])
    shutil.copytree(src, dest)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='action', required=True)
    s = sub.add_parser('sweep')
    s.add_argument('--close', action='store_true', help='close the free slots (default only lists them)')
    r = sub.add_parser('register')
    r.add_argument('--kind', required=True, choices=KINDS)
    r.add_argument('--name', default='')
    r.add_argument('--pid', type=int)
    r.add_argument('--project')
    r.add_argument('--space-id')
    r.add_argument('--port', type=int)
    r.add_argument('--url')
    r.add_argument('--keep', action='store_true', help='Codex user preview only; no age-based expiry; refused for Ego')
    h = sub.add_parser('heartbeat')
    h.add_argument('--id', required=True)
    for verb in ('close', 'release'):
        rl = sub.add_parser(verb, help='close the window/space/preview for real and unregister it')
        rl.add_argument('--id')
        rl.add_argument('--name', help='every slot whose name starts with this line name')
        rl.add_argument('--include-keep', action='store_true', help='also close the local preview given to the user')
    sub.add_parser('ego-list', help='list every Ego TaskSpace (find ones left waiting for the user)')
    ef = sub.add_parser('ego-finish', help='verify already-finished Ego TaskSpaces are absent; never claim old spaces')
    ef.add_argument('--space-id', nargs='+', required=True)
    ck = sub.add_parser('check', help='exit 1 while this line still has something open')
    ck.add_argument('--name', required=True)
    sub.add_parser('list')
    sn = sub.add_parser('snapshot')
    sn.add_argument('--from', dest='source', required=True)
    a = ap.parse_args()
    if a.action == 'sweep':
        print(json.dumps(sweep(a.close), ensure_ascii=False, indent=1))
    elif a.action == 'register':
        space = int(a.space_id) if a.space_id and str(a.space_id).isdigit() else a.space_id
        try:
            print(json.dumps({'slot': register(a.kind, a.name, a.pid, a.project, space, a.port, a.url, keep=a.keep)}, ensure_ascii=False))
        except ValueError as error:
            print(json.dumps({'error': str(error)}, ensure_ascii=False))
            return 2
    elif a.action == 'heartbeat':
        print(json.dumps({'ok': heartbeat(a.id)}))
    elif a.action in ('close', 'release'):
        if not a.id and not a.name:
            ap.error('give --id <slot> or --name <line>')
        out = close(a.name, a.id, a.include_keep)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 2 if out['cleanup_pending'] else 0
    elif a.action == 'ego-list':
        print(json.dumps(ego_list(), ensure_ascii=False, indent=1))
    elif a.action == 'ego-finish':
        out = ego_finish([int(x) if x.isdigit() else x for x in a.space_id])
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 2 if out['ego_spaces_to_finish_by_hand'] else 0
    elif a.action == 'check':
        out = check(a.name)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0 if out['ok'] else 1
    elif a.action == 'list':
        print(json.dumps([dict(d, free=why_free(d)) for d in slots()], ensure_ascii=False, indent=1))
    elif a.action == 'snapshot':
        print(json.dumps({'snapshot': str(snapshot(a.source))}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
