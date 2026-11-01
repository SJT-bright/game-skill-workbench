#!/usr/bin/env python3
"""Run one browser step of a regression and stop it when nothing moves (v7.9, 出包检查提速 S7, 总表 19 ③).

ad_regression.py and runtime_regression.py used subprocess.run(capture_output=True, timeout=limit): a hung browser or
page was only noticed at the step's own limit (startup and ad_entries 1500 s, button_sweep and layout_state 1200 s),
and a child that kept the output pipes open could hold communicate() even after the timeout. run() reads the output
while the step runs and watches the step's work folders (host log, result, evidence, and the progress file the suite
helpers touch after every page round trip: runtime_regression/lib.mjs and gates.mjs). When none of these changed for
`stall` seconds (default 240: longer than any legitimate quiet stretch, one startup case is capped at 110 s and a
revive at 45 s) the step and everything it started are stopped and Stalled is raised. The runners refuse on it, as
they already refused on a timeout; the total limit is unchanged (TimedOut). $TIKTOK_REGRESSION_STALL_S sets the window
(tests use a few seconds)."""
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

ENV_STALL = 'TIKTOK_REGRESSION_STALL_S'
DEFAULT_STALL_S = 240


class TimedOut(Exception):
    """The step ran past its total limit."""


class Stalled(Exception):
    """Nothing moved for `seconds`: no new output line and no file change in the watched folders."""

    def __init__(self, seconds, detail):
        super().__init__('no progress for %d s (%s)' % (seconds, detail))
        self.seconds = seconds
        self.detail = detail


class Finished:
    """What subprocess.run returned before (returncode, stdout, stderr)."""

    def __init__(self, returncode, stdout, stderr):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def stall_window(default=DEFAULT_STALL_S):
    """Seconds without any progress after which a step is stopped ($TIKTOK_REGRESSION_STALL_S, else default)."""
    raw = os.environ.get(ENV_STALL)
    try:
        value = float(raw) if raw else float(default)
    except ValueError:
        value = float(default)
    return value if value > 0 else float(default)


def _files(folders):
    """{path: (size, mtime_ns)} of every file under the watched folders."""
    state = {}
    for folder in folders:
        root = Path(folder)
        if not root.is_dir():
            continue
        for path in root.rglob('*'):
            try:
                if path.is_file():
                    st = path.stat()
                    state[str(path)] = (st.st_size, st.st_mtime_ns)
            except OSError:
                continue
    return state


def _stop(proc):
    """Stop the step and everything it started (start_new_session: the step has its own process group)."""
    if proc.poll() is not None:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except OSError:
            try:
                proc.send_signal(sig)
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue


def run(cmd, limit, watch=(), stall=None, poll=1.0):
    """Run cmd with stdin closed in its own process group. -> Finished(returncode, stdout, stderr).
    Raises TimedOut after `limit` seconds, and Stalled after `stall` seconds (default stall_window()) in which the
    step printed no new line and no file under `watch` changed. The step is stopped before either is raised."""
    stall = stall_window() if stall is None else stall
    watch = [Path(w) for w in watch]
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, errors='replace', start_new_session=True)
    out, err, moved = [], [], [time.monotonic()]

    def read(stream, sink):
        for line in iter(stream.readline, ''):
            sink.append(line)
            moved[0] = time.monotonic()
        stream.close()

    readers = [threading.Thread(target=read, args=(proc.stdout, out), daemon=True),
               threading.Thread(target=read, args=(proc.stderr, err), daemon=True)]
    for reader in readers:
        reader.start()
    started = time.monotonic()
    seen = _files(watch)
    try:
        while proc.poll() is None:
            time.sleep(poll)
            now = time.monotonic()
            current = _files(watch)
            if current != seen:
                seen, moved[0] = current, now
            if now - started > limit:
                _stop(proc)
                raise TimedOut('timed out after %d s' % limit)
            if now - moved[0] > stall:
                _stop(proc)
                where = ', '.join(w.name for w in watch) or 'nothing watched'
                raise Stalled(stall, 'no output line, and no file changed in %s' % where)
    except BaseException:
        _stop(proc)
        raise
    for reader in readers:
        reader.join(timeout=5)     # a leftover child may keep a pipe open; never wait on it (subprocess.run did)
    return Finished(proc.returncode, ''.join(out), ''.join(err))
