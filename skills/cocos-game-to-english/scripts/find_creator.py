#!/usr/bin/env python3
"""Find the Cocos Creator for a project on this computer and print the build commands (English pack 10.2.10). Read-only.

Saul 2026-10-31: the English Skill is used on other people's computers (macOS or Windows). Until 10.2.8 the pack only
listed the editors on Saul's Mac under /Applications/Cocos/Creator. This script looks where Creator can be on any
computer, picks the editor for the project's version, and prints the exact commands; it never starts a build itself.

Where it looks (first hit per version wins):
  1. COCOS_CREATOR=<CocosCreator executable, CocosCreator.app or its folder> (env, for unusual installs)
  2. the Cocos Dashboard's own list of installed editors: <home>/.cocos/profiles/editor.json (macOS and Windows)
  3. the usual folders: macOS /Applications/Cocos/Creator/<version>/CocosCreator.app (and ~/Applications, the old
     CocosCreator_v<version>.app); Windows <drive>:\\CocosDashboard\\resources\\.editors\\Creator\\<version>\\CocosCreator.exe,
     <drive>:\\ProgramData\\cocos\\editors\\Creator\\<version>\\CocosCreator.exe
Picking: the project's exact version; otherwise the nearest installed patch of the same minor version (2.4.4 -> 2.4.5),
marked as a substitute; never across 2.x / 3.x. Nothing suitable: says which version to download in Cocos Dashboard.

  python3 find_creator.py --project <Cocos project>      the editor and the web-mobile / TikTok build commands
  python3 find_creator.py --list                         every Creator found on this computer
  python3 find_creator.py --busy                         is a Creator build running now? (one build at a time)
  python3 find_creator.py --preflight                    right before a build: can this terminal start Creator at all?
  add --json for machine-readable output. Windows: python instead of python3.
生成时预防 P21 ④: the printed build commands always end with --no-sandbox --disable-gpu-sandbox --disable-gpu; when the
terminal is sandboxed (agent sandbox variables, home folder not writable, no local port) --project and --preflight say so
and exit 3: Creator would crash or hang there every time, so the build is not started and not retried.
Exit 0 found (exact or substitute), 1 not installed, 2 bad input, 3 this terminal is sandboxed (do not retry).
"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys

VERSION = re.compile(r'^(\d+)\.(\d+)\.(\d+)')


def parse_version(text):
    m = VERSION.match(str(text or '').strip().lstrip('v'))
    return tuple(int(x) for x in m.groups()) if m else None


def project_version(project):
    """('2.4.15', 2) / ('3.7.1', 3) from project.json (2.x) or package.json creator.version (3.x)."""
    project = Path(project)
    pkg, prj = project / 'package.json', project / 'project.json'
    if pkg.is_file():
        try:
            doc = json.loads(pkg.read_text(encoding='utf-8-sig'))
            v = (doc.get('creator') or {}).get('version')
            if parse_version(v):
                return str(v), parse_version(v)[0]
        except (OSError, ValueError, AttributeError):
            pass
    if prj.is_file():
        try:
            v = json.loads(prj.read_text(encoding='utf-8-sig')).get('version')
            if parse_version(v):
                return str(v), parse_version(v)[0]
        except (OSError, ValueError, AttributeError):
            pass
    raise ValueError('看不出 Cocos 版本：%s 里没有带版本号的 project.json（2.x）或 package.json 的 creator.version（3.x）' % project)


def executable_of(path, platform):
    """CocosCreator executable for an .app, a folder or the executable itself; None when there is none."""
    p = Path(path)
    if p.suffix == '.app' or (platform == 'darwin' and p.is_dir() and (p / 'Contents').is_dir()):
        exe = p / 'Contents' / 'MacOS' / 'CocosCreator'
        return exe if exe.is_file() else None
    if p.is_dir():
        for cand in (p / 'CocosCreator.exe', p / 'CocosCreator.app' / 'Contents' / 'MacOS' / 'CocosCreator'):
            if cand.is_file():
                return cand
        return None
    return p if p.is_file() else None


def app_version(exe):
    """Version from the .app's Info.plist (macOS), else from a version-looking folder name above the executable."""
    exe = Path(exe)
    for parent in exe.parents:
        if parent.suffix == '.app':
            try:
                with open(parent / 'Contents' / 'Info.plist', 'rb') as f:
                    v = plistlib.load(f).get('CFBundleShortVersionString')
                if parse_version(v):
                    return str(v)
            except (OSError, ValueError, plistlib.InvalidFileException):
                pass
    for part in reversed(exe.parts):
        m = re.search(r'(\d+\.\d+\.\d+)', part)
        if m:
            return m.group(1)
    return None


def standard_places(platform, home, env):
    if platform == 'darwin':
        roots = [Path('/Applications/Cocos/Creator'), Path(home) / 'Applications' / 'Cocos' / 'Creator',
                 Path('/Applications/CocosCreator/Creator')]
        out = []
        for r in roots:
            try:
                out += [(d.name, d / 'CocosCreator.app') for d in sorted(r.iterdir()) if d.is_dir()]
            except OSError:
                pass
        try:
            out += [(m.group(1), p) for p in sorted(Path('/Applications').glob('CocosCreator*.app'))
                    for m in [re.search(r'(\d+\.\d+\.\d+)', p.name)] if m]
        except OSError:
            pass
        return out
    if platform == 'win32':
        drives = []
        for d in (env.get('SystemDrive'), 'C:', 'D:'):
            if d and d.upper() not in [x.upper() for x in drives]:
                drives.append(d)
        roots = []
        for d in drives:
            roots += [Path(d + '\\') / 'CocosDashboard' / 'resources' / '.editors' / 'Creator',
                      Path(d + '\\') / 'ProgramData' / 'cocos' / 'editors' / 'Creator']
        for key in ('PROGRAMDATA', 'LOCALAPPDATA'):
            if env.get(key):
                roots.append(Path(env[key]) / 'cocos' / 'editors' / 'Creator')
        out = []
        for r in roots:
            try:
                out += [(d.name, d) for d in sorted(r.iterdir()) if d.is_dir()]
            except OSError:
                pass
        return out
    return []


def installed_editors(platform=None, home=None, env=None):
    """[{version, exe, source}] for every Creator found, newest first, one entry per version."""
    platform = sys.platform if platform is None else platform
    env = os.environ if env is None else env
    home = Path(home if home is not None else (env.get('USERPROFILE') if platform == 'win32' else None) or Path.home())
    found = {}

    def add(version, path, source):
        exe = executable_of(path, platform)
        if not exe:
            return
        v = version if parse_version(version) else app_version(exe)
        if parse_version(v) and v not in found:
            found[v] = {'version': v, 'exe': str(exe), 'source': source}

    own = env.get('COCOS_CREATOR')
    if own:
        exe = executable_of(own, platform)
        if exe:
            add(app_version(exe), own, 'COCOS_CREATOR')
    record = home / '.cocos' / 'profiles' / 'editor.json'
    try:
        doc = json.loads(record.read_text(encoding='utf-8-sig'))
        for kind, rows in (doc.get('editor') or {}).items():
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, dict) and row.get('file') and row.get('state', 'success') == 'success':
                    add(row.get('version'), row['file'], 'Cocos Dashboard（%s）' % kind)
    except (OSError, ValueError, AttributeError):
        pass
    for version, path in standard_places(platform, home, env):
        add(version, path, '常用安装位置')
    return sorted(found.values(), key=lambda e: parse_version(e['version']), reverse=True)


def choose(target, editors):
    """{'status': 'exact'|'substitute'|'missing', 'editor': {...} or None, 'same_minor': [...]}"""
    t = parse_version(target)
    exact = [e for e in editors if parse_version(e['version']) == t]
    same = [e for e in editors if parse_version(e['version'])[:2] == t[:2] and parse_version(e['version']) != t]
    if exact:
        return {'status': 'exact', 'editor': exact[0], 'same_minor': same}
    if same:
        # nearest patch; on a tie the newer one (2.4.4 -> 2.4.5 before 2.4.3)
        same.sort(key=lambda e: (abs(parse_version(e['version'])[2] - t[2]), -parse_version(e['version'])[2]))
        return {'status': 'substitute', 'editor': same[0], 'same_minor': same}
    return {'status': 'missing', 'editor': None, 'same_minor': []}


# 生成时预防 P21 ④: always on the build command (Electron/GPU sandbox made command-line builds hang at asset import or
# crash; 普查 env_creator_stuck). Chromium switches, accepted by Creator on macOS, Windows and Linux.
SANDBOX_FLAGS = ['--no-sandbox', '--disable-gpu-sandbox', '--disable-gpu']
SANDBOX_MARKS = ('CODEX_SANDBOX', 'CODEX_SANDBOX_NETWORK_DISABLED', 'APP_SANDBOX_CONTAINER_ID')
SANDBOX_EXIT = 3


def build_argv(editor, project, major, platform_name):
    debug = 'true' if platform_name == 'web-mobile' else 'false'
    flag = '--path' if major == 2 else '--project'
    return [editor['exe'], flag, str(Path(project).resolve()), '--build', 'platform=%s;debug=%s' % (platform_name, debug)] \
        + SANDBOX_FLAGS


def sandbox_problem(env=None, home=None, probe=True):
    """Why Creator cannot start from this terminal (a sandbox around the agent), or None. Checked before a build: in a
    sandbox Creator crashes or hangs every time, so the build is refused at once instead of retried (普查: Creator
    闪退弹崩溃框反复重试). Signs: the agent sandbox's own environment variables; no write access to the home folder
    (Creator keeps its settings there); no local port (Creator's build talks to itself over localhost)."""
    env = os.environ if env is None else env
    found = ['环境变量 %s=%s' % (k, env.get(k)) for k in SANDBOX_MARKS if env.get(k)]
    if probe:
        import socket
        try:
            with socket.socket() as s:
                s.bind(('127.0.0.1', 0))
                s.listen(1)
        except OSError as error:
            found.append('不能在本机开端口（%s）' % error)
        base = Path(home if home is not None else Path.home())
        target = base / '.CocosCreator' if (base / '.CocosCreator').is_dir() else base
        test = target / ('.find_creator_write_test_%d' % os.getpid())
        try:
            test.write_text('ok', encoding='utf-8')
            test.unlink()
        except OSError as error:
            found.append('不能写用户文件夹 %s（%s）' % (target, error.__class__.__name__))
    return '；'.join(found) or None


def quote(argv, platform):
    """Copy-paste text: PowerShell on Windows (the & runs a quoted program; in cmd.exe leave it out), POSIX shell elsewhere.
    Scripts should run the 'argv' list instead, with no shell in between."""
    if platform == 'win32':
        special = set(' \t;,=&|<>^()%!\'"')
        q = lambda a: '"' + a.replace('"', '\\"') + '"' if not a or special & set(a) or '\\' in a else a
        return '& ' + ' '.join(q(a) for a in argv)
    import shlex
    return ' '.join(shlex.quote(a) for a in argv)


def hints(version, os_name):
    v = parse_version(version)
    out = []
    out.append('构建命令已经带上 --no-sandbox --disable-gpu-sandbox --disable-gpu（以前构建卡在导入资源不动、闪退，就是少了它们），不要删。')
    if v and v[0] == 3:
        out.append('3.x 构建成功的退出码也可能是 36（32 参数错，34 构建失败）：以导出目录里有没有 index.html 和这次的图为准。')
    if v == (2, 4, 3):
        out.append('2.4.3 构建报 Device._initCaps 或 WebGL 错时：把本包 cocos-game-to-english/assets/build-worker-canvas-compat/ '
                   '复制到工程副本的 packages/ 下，命令最前面加 --use-gl=desktop（Saul 的 Mac 上要这样）；'
                   '加了 --use-gl=desktop 还报 WebGL 错，就把命令末尾的 --disable-gpu 去掉再构建一次（只这一个版本）。')
    if v == (2, 4, 4):
        out.append('2.4.4 在 Saul 的 Mac 上一次都没构建成功（WebGL 初始化错误）：构建失败就换同一小版本里装了的另一个（例如 2.4.5），'
                   '在 docs/english/engine.txt 写一行「原工程 2.4.4，用 2.4.5 构建」。')
    if v == (3, 7, 1):
        out.append('3.7.1 命令行导出的 web-mobile 可能缺 index.html、index.js、style.css：用这个编辑器自带的模板补，'
                   '见 cocos-game-to-english/references/local-creator-versions.md。')
    out.append('同一时间整台电脑只跑一个构建：先跑 find_creator.py --busy。构建都在工程的副本上做，原工程一个文件都不动。')
    return out


def busy(platform=None):
    """Running Creator build processes: [{pid, command}]."""
    platform = sys.platform if platform is None else platform
    rows = []
    if platform == 'win32':
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='CocosCreator.exe'\" | "
              "ForEach-Object { \"$($_.ProcessId) $($_.CommandLine)\" }")
        tries = [['powershell', '-NoProfile', '-Command', ps]]
    else:   # some sandboxes forbid ps but allow pgrep
        tries = [[shutil.which('ps') or '/bin/ps', '-ax', '-o', 'pid=,command='],
                 [shutil.which('pgrep') or 'pgrep', '-fl', 'CocosCreator'] if platform == 'darwin'
                 else [shutil.which('pgrep') or 'pgrep', '-af', 'CocosCreator']]
    text = None
    for argv in tries:
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode in (0, 1) and (r.stdout or r.returncode == 1) and 'not permitted' not in (r.stderr or ''):
            text = r.stdout or ''
            break
    if text is None:
        return None
    for line in text.splitlines():
        line = line.strip()
        if 'CocosCreator' in line and '--build' in line:
            pid, _, cmd = line.partition(' ')
            rows.append({'pid': pid, 'command': cmd.strip()[:300]})
    return rows


def sandbox_text(problem):
    return ('现在不能构建：这个终端受沙箱限制（%s）。Creator 在这里每次都会闪退或卡住，重试没有用，不要重试；'
            '换一个不受沙箱限制的终端再跑构建命令（在 Codex 里，请求不受沙箱限制地运行这条命令）。等的时候接着改源码。' % problem)


def report(project, platform=None, env=None, home=None, sandbox_probe=True):
    platform = sys.platform if platform is None else platform
    version, major = project_version(project)
    editors = installed_editors(platform, home, env)
    pick = choose(version, editors)
    r = {'project': str(Path(project).resolve()), 'version': version, 'major': major, 'installed': editors, **pick,
         'hints': hints(version, platform),
         'sandbox': {'flags': list(SANDBOX_FLAGS), 'problem': sandbox_problem(env, home, probe=sandbox_probe)}}
    if pick['editor']:
        for name in ('web-mobile', 'bytedance-mini-game'):
            argv = build_argv(pick['editor'], project, major, name)
            r.setdefault('commands', {})[name] = {'argv': argv, 'text': quote(argv, platform)}
    return r


def say(r):
    lines = ['工程：%s（Cocos %s）' % (r['project'], r['version'])]
    if (r.get('sandbox') or {}).get('problem'):
        lines.insert(0, sandbox_text(r['sandbox']['problem']))
    lines.append('这台电脑装了：' + ('、'.join(e['version'] for e in r['installed']) or '没找到任何 Cocos Creator'))
    if r['status'] == 'exact':
        lines.append('用 %s（和工程版本一样）：%s' % (r['editor']['version'], r['editor']['exe']))
    elif r['status'] == 'substitute':
        lines.append('没装 %s，先用同一小版本的 %s 代替：%s。构建或试玩有问题再请用户在 Cocos Dashboard 下载 %s；'
                     '在 docs/english/engine.txt 写一行「原工程 %s，用 %s 构建」。' % (
                         r['version'], r['editor']['version'], r['editor']['exe'], r['version'], r['version'],
                         r['editor']['version']))
    else:
        lines.append('这台电脑没装 Cocos Creator %s，同一小版本（%s.x）也没有。请用户打开 Cocos Dashboard，在「编辑器」里下载 %s，'
                     '装好后再跑一次本脚本；等的时候接着改源码，不停手。' % (r['version'], '.'.join(r['version'].split('.')[:2]),
                                                          r['version']))
    for name, label in (('web-mobile', '导出试玩用的 Web'), ('bytedance-mini-game', '出 TikTok 小游戏包')):
        if r.get('commands', {}).get(name):
            lines.append('%s：%s' % (label, r['commands'][name]['text']))
    if r.get('commands') and r['commands']['web-mobile']['text'].startswith('& '):
        lines.append('（上面是 PowerShell 写法；在 cmd 里去掉开头的「& 」。用脚本跑时用 --json 里的 argv，不经过命令行。）')
    lines += ['注意：' + h for h in r['hints']]
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description='找这台电脑上的 Cocos Creator，打印构建命令（只读）')
    ap.add_argument('--project', type=Path)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--busy', action='store_true')
    ap.add_argument('--preflight', action='store_true', help='构建前一刻：这个终端能不能启动 Creator（沙箱受限退出 3，不要重试）')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.preflight:
        problem = sandbox_problem()
        if a.json:
            print(json.dumps({'sandbox_problem': problem, 'flags': SANDBOX_FLAGS}, ensure_ascii=False))
        else:
            print(sandbox_text(problem) if problem else '这个终端可以启动 Creator（构建命令带 %s）。' % ' '.join(SANDBOX_FLAGS))
        return SANDBOX_EXIT if problem else 0
    if a.busy:
        rows = busy()
        if a.json:
            print(json.dumps({'busy': rows}, ensure_ascii=False))
        elif rows is None:
            print('查不了现在有没有构建在跑（ps / powershell 用不了）。')
        else:
            print('有 %d 个 Creator 构建在跑，等它结束再构建：%s' % (len(rows), '；'.join(r['pid'] for r in rows)) if rows
                  else '现在没有 Creator 构建在跑，可以构建。')
        return 0
    if a.list:
        editors = installed_editors()
        print(json.dumps(editors, ensure_ascii=False, indent=2) if a.json else
              '\n'.join('%s  %s（%s）' % (e['version'], e['exe'], e['source']) for e in editors) or '没找到任何 Cocos Creator。')
        return 0 if editors else 1
    if not a.project:
        ap.error('要 --project、--list 或 --busy')
    try:
        r = report(a.project)
    except (OSError, ValueError) as error:
        print('输入有问题：%s' % error)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.json else say(r))
    if r['sandbox']['problem']:
        return SANDBOX_EXIT
    return 0 if r['editor'] else 1


if __name__ == '__main__':
    sys.exit(main())
