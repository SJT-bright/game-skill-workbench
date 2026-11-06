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
    # 简化.11.15: Cocos Creator 2.x names the TikTok (ByteDance) mini-game platform 'bytedance' (build/bytedance);
    # only 3.x calls it 'bytedance-mini-game'. 2.4.15 given the 3.x name stops with "Cannot read property 'isNative' of
    # undefined" and then hangs (found 11-05 on a copy of 割草小能手; the delivered builds all used platform=bytedance).
    if platform_name == 'bytedance-mini-game' and major == 2:
        platform_name = 'bytedance'
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


# 生成时预防 R4F1 (#11, P02-3): every printed build command starts with `tiktok_finalize.py sync` (about 1 s: the
# platform-kit files put back to their KIT_MANIFEST bytes, GameUIKit / RunSession / FxPool / ShopTx for new games, squashed
# pictures reported) so a build never runs on parts that drifted; before, only SKILL.md said "run sync before every
# build" (普查 startup_stuck 34 款, touch_coord_missing 28 款). A sync that exits 1 stops the build (&&).
FINALIZE = Path(__file__).resolve().parents[2] / 'remake-core' / 'scripts' / 'tiktok_finalize.py'
BOARDS = ('remake', 'localize')


def board_of(project):
    """The board in the project's new-game marker (.tiktok-kit/policy.json); English pack default localize."""
    try:
        board = json.loads((Path(project) / '.tiktok-kit' / 'policy.json').read_text(encoding='utf-8')).get('board')
    except (OSError, ValueError, AttributeError):
        board = None
    return board if board in BOARDS else 'localize'


def sync_argv(project, board, finalize=None, python=None):
    """[python, tiktok_finalize.py, sync, --project P, --board B], or None when remake-core is not installed."""
    finalize = Path(finalize) if finalize else FINALIZE
    if not finalize.is_file():
        return None
    return [python or sys.executable or 'python3', str(finalize), 'sync', '--project', str(Path(project).resolve()),
            '--board', board]


def chain(first, second, platform):
    """Copy-paste text that runs `second` only when `first` exits 0."""
    if platform == 'win32':
        return '%s; if ($LASTEXITCODE -eq 0) { %s }' % (quote(first, platform), quote(second, platform))
    return '%s && %s' % (quote(first, platform), quote(second, platform))


# 生成时预防 R4J4 (P02-3, after R4F1): the TikTok build command also ends with `tiktok_finalize.py sync --native <the
# build folder>`, so the startup parts, touch fix, storage layer, host-shim and guards go into the build that was just
# made (普查 startup_stuck 34/42 款, touch_coord_missing 28/34 款: English builds packaged without that step). The folder
# comes from the build argv: buildPath (2.4 default `build`, also read from the Build panel's saved buildPath; 3.x
# default `project://build`) + the platform name (2.4 `bytedance`; 3.x outputName, default `bytedance-mini-game`).
# configPath or anything it cannot read: no --native step, and the output says to run it by hand.
BUILD_OK = {2: (0,), 3: (0, 36)}     # Creator 3.x command-line builds that succeed may exit 36


def build_options(argv):
    """{'platform': ..., 'buildPath': ...} from the `--build "k=v;k=v"` argument; {} when there is none."""
    if '--build' not in argv or argv.index('--build') + 1 >= len(argv):
        return {}
    out = {}
    for item in argv[argv.index('--build') + 1].split(';'):
        key, eq, value = item.partition('=')
        if eq and key.strip():
            out[key.strip()] = value.strip()
    return out


def native_dir(argv, project, major):
    """(build folder, None) for a TikTok build argv, or (None, why) when it cannot be worked out from the arguments."""
    opts, project = build_options(argv), Path(project).resolve()
    platform_name = opts.get('platform')
    if platform_name not in ('bytedance', 'bytedance-mini-game'):
        return None, '不是 TikTok 构建（platform=%s）' % platform_name
    if opts.get('configPath'):
        return None, '构建参数用了 configPath，构建目录写在那个配置文件里'
    base = opts.get('buildPath')
    if base is None and major == 2:     # 2.4: with no buildPath on the command line Creator uses the Build panel's one
        for saved in (project / 'local' / 'builder.json', project / 'settings' / 'builder.json'):
            try:
                value = json.loads(saved.read_text(encoding='utf-8-sig')).get('buildPath')
            except (OSError, ValueError, AttributeError):
                continue
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    return None, '%s 里的 buildPath 看不懂（%r）' % (saved.name, value)
                base = value
                break
    base = (base or 'build').strip()
    if base.startswith('project://'):
        base = base[len('project://'):]
    if '://' in base:
        return None, 'buildPath=%s 不是普通路径' % base
    folder = Path(base) if Path(base).is_absolute() else project / base
    name = opts.get('outputName') if major == 3 else None
    return folder / (name or platform_name), None


def native_sync_argv(sync, folder):
    """The `sync` argv with `--native <build folder>` added (same project and board)."""
    return list(sync) + ['--native', str(folder)]


def chain_native(sync, build, native, platform, major):
    """sync, then the build, then `sync --native` when the build exit code means success (2.4: 0; 3.x: 0 or 36)."""
    ok = BUILD_OK.get(major, (0,))
    if platform == 'win32':
        test = ' -or '.join('$LASTEXITCODE -eq %d' % c for c in ok)
        return '%s; if ($LASTEXITCODE -eq 0) { %s; if (%s) { %s } }' % (
            quote(sync, platform), quote(build, platform), test, quote(native, platform))
    if ok == (0,):
        return '%s && %s && %s' % (quote(sync, platform), quote(build, platform), quote(native, platform))
    test = ' || '.join('[ "$rc" -eq %d ]' % c for c in ok)
    return '%s && { %s; rc=$?; %s; } && %s' % (quote(sync, platform), quote(build, platform), test,
                                                quote(native, platform))


def report(project, platform=None, env=None, home=None, sandbox_probe=True, board=None, finalize=None):
    platform = sys.platform if platform is None else platform
    version, major = project_version(project)
    editors = installed_editors(platform, home, env)
    pick = choose(version, editors)
    r = {'project': str(Path(project).resolve()), 'version': version, 'major': major, 'installed': editors, **pick,
         'hints': hints(version, platform),
         'sandbox': {'flags': list(SANDBOX_FLAGS), 'problem': sandbox_problem(env, home, probe=sandbox_probe)}}
    board = board or board_of(project)
    sync = sync_argv(project, board, finalize)
    r['sync'] = {'board': board, 'argv': sync}
    if sync is None:
        r['hints'].append('没找到 remake-core/scripts/tiktok_finalize.py（remake-core 没装全）：构建命令前面没带 sync，'
                          '先把整个英化包装好再构建')
    if pick['editor']:
        for name in ('web-mobile', 'bytedance-mini-game'):
            argv = build_argv(pick['editor'], project, major, name)
            r.setdefault('commands', {})[name] = {
                'argv': argv, 'sync_argv': sync, 'steps': [a for a in (sync, argv) if a],
                'text': chain(sync, argv, platform) if sync else quote(argv, platform)}
        tt = r['commands']['bytedance-mini-game']    # R4J4: after the TikTok build, sync --native <build folder>
        folder, why = native_dir(tt['argv'], project, major)
        tt['native_dir'], tt['build_ok_exit'] = (str(folder) if folder else None), list(BUILD_OK.get(major, (0,)))
        if sync and folder:
            tt['native_sync_argv'] = native_sync_argv(sync, folder)
            tt['steps'].append(tt['native_sync_argv'])
            tt['text'] = chain_native(sync, tt['argv'], tt['native_sync_argv'], platform, major)
        elif sync:
            r['hints'].append('TikTok 构建命令后面没接 sync --native（%s）：构建完成后手跑 tiktok_finalize.py sync '
                              '--project <工程> --board %s --native <构建日志里的产物目录>' % (why, board))
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
    if r.get('commands') and (r.get('sync') or {}).get('argv'):
        lines.append('每条构建命令前面都带 tiktok_finalize.py sync（板块 %s，约 1 秒：平台包文件按哈希换回，新游戏装 GameUIKit、'
                     'RunSession、FxPool、ShopTx，报压扁的图）；sync 没过就不构建，先改它报的问题。用脚本跑时按 --json 里的 '
                     'steps 依次跑。' % r['sync']['board'])
    if (r.get('commands', {}).get('bytedance-mini-game') or {}).get('native_sync_argv'):
        tt = r['commands']['bytedance-mini-game']
        lines.append('TikTok 构建成功后（退出码 %s）自动再跑 sync --native %s，把启动件、触摸修正、存档层、host-shim、guard 装进构建；'
                     '它没过就先改它报的问题，别拿这个构建出包。用脚本跑时 steps 第 3 条只在构建退出码是 build_ok_exit 里的数时跑。'
                     % ('/'.join(str(c) for c in tt['build_ok_exit']), tt['native_dir']))
    if r.get('commands') and r['commands']['web-mobile']['text'].startswith('& '):
        lines.append('（上面是 PowerShell 写法；在 cmd 里去掉开头的「& 」，把「; if ($LASTEXITCODE -eq 0) { … }」写成「&& …」。'
                     '用脚本跑时用 --json 里的 steps，不经过命令行。）')
    lines += ['注意：' + h for h in r['hints']]
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description='找这台电脑上的 Cocos Creator，打印构建命令（只读）')
    ap.add_argument('--project', type=Path)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--busy', action='store_true')
    ap.add_argument('--preflight', action='store_true', help='构建前一刻：这个终端能不能启动 Creator（沙箱受限退出 3，不要重试）')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--board', choices=BOARDS, help='sync 用的板块（默认读工程 .tiktok-kit/policy.json，没有就是 localize）')
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
        r = report(a.project, board=a.board)
    except (OSError, ValueError) as error:
        print('输入有问题：%s' % error)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.json else say(r))
    if r['sandbox']['problem']:
        return SANDBOX_EXIT
    return 0 if r['editor'] else 1


if __name__ == '__main__':
    sys.exit(main())
