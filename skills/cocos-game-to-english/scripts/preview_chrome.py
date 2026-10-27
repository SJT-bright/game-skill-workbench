"""Open a loopback user preview in a separate, ordinary Google Chrome window.

This submits an OS launch request; it does not certify that a window was shown
or that the game works. It never changes profiles, cookies or browser settings.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit


def find_chrome():
    if sys.platform == 'darwin':
        candidates = [Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
                      Path.home() / 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    elif sys.platform == 'win32':
        candidates = [Path(os.environ[key]) / 'Google/Chrome/Application/chrome.exe'
                      for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA') if os.environ.get(key)]
    else:
        candidates = [Path(found) for name in ('google-chrome', 'google-chrome-stable')
                      if (found := shutil.which(name))]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError('未找到 Google Chrome；预览服务仍可用，请安装 Chrome 后重试。')


def open_chrome_window(url, phone_size=(390, 844)):
    parsed = urlsplit(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password:
        raise ValueError('用户试玩启动器只接受本机 HTTP 预览地址')
    executable = find_chrome()
    width, height = phone_size
    window_size = (max(480, width + 80), max(560, height + 116))
    command = [str(executable), '--new-window',
               '--window-size=' + ','.join(map(str, window_size)), url]
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True)
    return {'browser': 'google_chrome', 'status': 'launch_requested', 'url': url,
            'new_window': True, 'requested_window_size': list(window_size),
            'launcher_pid': child.pid, 'visible_window_verified': False}


def browser_request(url, *, keep=False, explicit_open=False, no_browser=False, phone_size=(390, 844)):
    if no_browser or not (keep or explicit_open):
        return {'browser': 'google_chrome', 'status': 'not_requested', 'url': url}
    try:
        return open_chrome_window(url, phone_size)
    except (OSError, ValueError) as error:
        return {'browser': 'google_chrome', 'status': 'launch_failed', 'url': url,
                'error': str(error), 'visible_window_verified': False}
