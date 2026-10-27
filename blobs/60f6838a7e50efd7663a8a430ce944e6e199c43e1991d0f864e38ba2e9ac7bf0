"""Open a loopback user preview in a separate, Google Chrome mobile touch window.

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
    find_chrome()
    import json, time, hashlib
    runtime = Path.home() / 'GameSkillMigration/chrome-runtime/bin/python'
    if not runtime.is_file():
        runtime = Path(sys.executable)
    state = Path.home() / '.game-skill-locks/touch-previews'
    state.mkdir(parents=True,exist_ok=True)
    ident = hashlib.sha256(url.encode()).hexdigest()[:16]
    result = state / (ident + '-' + str(os.getpid()) + '.json')
    command = [str(runtime), str(Path(__file__).with_name('preview_touch_window.py')),
               '--url',url,'--width',str(phone_size[0]),'--height',str(phone_size[1]),
               '--profile',str(state / (ident+'-profile')), '--result',str(result),'--parent',str(os.getpid())]
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True)
    for _ in range(300):
        if result.is_file():
            observed=json.loads(result.read_text())
            if observed.get('status') != 'touch_window_ready':raise OSError(observed.get('error','Touch window failed'))
            observed['receipt']=str(result)
            return observed
        if child.poll() is not None:raise OSError('Chrome touch preview exited before verification')
        time.sleep(.1)
    raise OSError('Chrome touch preview did not return its device readback in time')



def browser_request(url, *, keep=False, explicit_open=False, no_browser=False, phone_size=(390, 844)):
    if no_browser or not (keep or explicit_open):
        return {'browser': 'google_chrome', 'status': 'not_requested', 'url': url}
    try:
        return open_chrome_window(url, phone_size)
    except (OSError, ValueError) as error:
        return {'browser': 'google_chrome', 'status': 'launch_failed', 'url': url,
                'error': str(error), 'visible_window_verified': False}
