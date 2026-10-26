#!/usr/bin/env python3
"""Find (and optionally close) leftovers of game-skill test runs that keep using memory — never a running test.

User 2026-10-23: tests open new windows instead of waiting, so cleanup must free only what is no longer used:
  1. browser_slots.py sweep retires gone-owner records and closes completed self-owned helpers only when their
     current process identity matches. Live idle slots and unknown Ego ownership are review candidates only.
     Useful user trial windows remain open; age alone never revokes them.
  2. Unregistered legacy browser/helper processes are reported as review candidates. A missing parent or an old
     timestamp alone never authorizes automatic termination.
A job holding a heavy_lock (any game) and everything it started is never touched.
The user's own Chrome, the Cocos editor and Codex are never closed; their memory is only reported.

  python cleanup_machine.py            # list what would be closed (default, changes nothing)
  python cleanup_machine.py --close    # close those leftovers (run before opening a new test window)
Exit code 0. Windows / macOS / Linux.
"""
import argparse
import json
import os
import signal
import subprocess
import sys

OURS = ('serve_preview.py', 'chrome_touch.py', 'audio_pipeline.py', 'audit_frame_glitches.py', 'heavy_lock.py')
BROWSER = ('playwright_chromiumdev_profile',)
REPORT_ONLY = {'cocos': ('cocoscreator', 'cocos creator', 'cocosdashboard'), 'codex': ('codex',),
               'chrome (yours)': ('google chrome', 'chrome.exe')}


def processes():
    if os.name == 'nt':
        ps = ('Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,WorkingSetSize,CommandLine '
              '| ConvertTo-Json -Compress')
        out = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout
        rows = json.loads(out or '[]')
        rows = rows if isinstance(rows, list) else [rows]
        return [{'pid': r['ProcessId'], 'ppid': r['ParentProcessId'], 'mb': (r.get('WorkingSetSize') or 0) / 1048576,
                 'cmd': r.get('CommandLine') or ''} for r in rows]
    out = subprocess.run(['ps', '-axo', 'pid=,ppid=,rss=,command='], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4 and parts[0].isdigit():
            rows.append({'pid': int(parts[0]), 'ppid': int(parts[1]), 'mb': int(parts[2]) / 1024, 'cmd': parts[3]})
    return rows


def total_ram_gb():
    try:
        if sys.platform == 'darwin':
            return int(subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout) / 2 ** 30
        if os.name == 'nt':
            out = subprocess.run(['powershell', '-NoProfile', '-Command',
                                  '(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory'], capture_output=True, text=True).stdout
            return int(out.strip()) / 2 ** 30
        with open('/proc/meminfo') as f:
            return int(f.readline().split()[1]) / 2 ** 20
    except (OSError, ValueError):
        return None


def lock_holders():
    """pids of every live heavy_lock holder (machine-wide and per game)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import heavy_lock
    pids = set()
    root = heavy_lock.LOCK_ROOT
    for d in ([root / 'heavy'] + sorted(root.glob('project-*')) if root.is_dir() else []):
        try:
            h = json.loads((d / 'owner.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if heavy_lock.alive(h.get('pid')):
            pids.add(h['pid'])
    return pids, heavy_lock.alive


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--close', action='store_true', help='close the leftovers (default only lists them)')
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import browser_slots
        slot_report = browser_slots.sweep(close=a.close)
        registered = {s.get('pid') for s in browser_slots.slots() if s.get('pid')}
    except Exception as error:            # never let the slot registry block the process scan
        slot_report, registered = {'error': str(error)}, set()
    rows = processes()
    by_pid = {r['pid']: r for r in rows}
    me = {os.getpid(), os.getppid()}
    try:
        holders, alive = lock_holders()
    except Exception:
        holders, alive = set(), (lambda pid: pid in by_pid)
    protect, grew = set(holders) | registered, True          # running heavy jobs, registered live slots, their children
    while grew:
        grew = False
        for r in rows:
            if r['ppid'] in protect and r['pid'] not in protect:
                protect.add(r['pid']); grew = True
    me |= protect

    def orphaned(r):
        ppid = r['ppid']
        if ppid in (0, 1) or ppid not in by_pid and not alive(ppid):
            return True
        parent = by_pid.get(ppid)
        # on macOS/Linux an orphan may be adopted by launchd/systemd --user instead of pid 1
        return bool(parent) and os.name != 'nt' and any(x in parent['cmd'] for x in ('launchd', 'systemd --user', '/sbin/init'))

    leftovers, still_working, totals = [], [], {k: 0.0 for k in REPORT_ONLY}
    for r in rows:
        low = r['cmd'].lower()
        if r['pid'] in me or 'cleanup_machine.py' in low:
            continue
        if any(x in r['cmd'] for x in OURS) or any(x in low for x in BROWSER):
            (leftovers if orphaned(r) else still_working).append(r)
            continue
        for k, keys in REPORT_ONLY.items():
            if any(x in low for x in keys):
                totals[k] += r['mb']
                break
    ram = total_ram_gb()
    closed = []
    # Unregistered historical orphan names/PIDs are candidates, not ownership/uselessness proof.
    # Registered completed resources above already use identity-checked ordinary termination.
    print(json.dumps({
        'slots': slot_report,
        'leftovers': [{'pid': r['pid'], 'mb': round(r['mb']), 'what': r['cmd'][:120]} for r in leftovers][:30],
        'legacy_candidates_require_current_review': True,
        'leftover_mb': round(sum(r['mb'] for r in leftovers)),
        'closed': closed if a.close else 'not closed (add --close)',
        'still_working_not_touched': [{'pid': r['pid'], 'mb': round(r['mb']), 'what': r['cmd'][:80]} for r in still_working][:30],
        'memory_mb_not_touched': {k: round(v) for k, v in totals.items()},
        'ram_gb': round(ram) if ram else None,
        'max_active_sessions': (2 if ram <= 16.5 else 3 if ram <= 48.5 else 4) if ram else 3,
        'tip': 'Never wait for a busy window: open a new one. Close the Cocos editor when no session is using it; '
               'close finished Codex sessions.'},
        ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
