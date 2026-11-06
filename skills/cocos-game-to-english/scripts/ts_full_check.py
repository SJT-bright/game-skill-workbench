#!/usr/bin/env python3
"""Full TypeScript check of a Cocos Creator 3.x project that never reads the project's temp/ (R4O5).

Why: a project's tsconfig.json extends ./temp/tsconfig.cocos.json, and temp/declarations/cc.d.ts is a
`/// <reference path="...">` to the engine declarations of the machine that last opened the project. An archived project
(SLS35, 补查2 第 5 节) still pointed at a Windows Cocos install, so `tsc -p tsconfig.json` on this machine failed on
"Cannot find module 'cc'" for every file and hid the real errors. This tool writes its own tsconfig in a scratch folder:
the engine declarations come from the local Creator (find_creator.py), cc/env and cc/userland/macro come from a small
shim, only assets/**/*.ts is checked, and temp/, library/, build/ ... are never read. The project is not changed.

  python3 ts_full_check.py --project <3.x project> [--creator <CocosCreator exe or .app>] [--tsc <tsc.js>] [--json]
Exit 0 passed, 1 type errors, 2 not_run (no 3.x Creator / tsc / node found: reported, never guessed).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import find_creator  # noqa: E402

NEVER_READ = ('temp', 'library', 'local', 'build', 'profiles', 'node_modules', 'settings', 'extensions', 'packages')
# Option names whose values point into temp/ or at one machine's paths: dropped from the project's own options.
MACHINE_OPTIONS = ('types', 'typeRoots', 'paths', 'baseUrl', 'rootDir', 'rootDirs', 'outDir', 'tsBuildInfoFile')
ENV_FLAGS = ('HTML5 NATIVE ANDROID IOS MAC WINDOWS LINUX OHOS OPEN_HARMONY WECHAT WECHAT_MINI_PROGRAM XIAOMI ALIPAY '
             'TAOBAO TAOBAO_MINIGAME BYTEDANCE OPPO VIVO HUAWEI MIGU HONOR COCOS_RUNTIME SUD SUDV2 NODEJS EDITOR '
             'EDITOR_NOT_IN_PREVIEW PREVIEW BUILD TEST DEBUG DEV MINIGAME RUNTIME_BASED SUPPORT_JIT JSB').split()


def strip_json_comments(text):
    """tsconfig.json allows /* */ and // comments and trailing commas; strings are kept as they are."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith('//', i):
            i = text.find('\n', i) if text.find('\n', i) >= 0 else n
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r',(\s*[}\]])', r'\1', ''.join(out))


def project_options(project):
    """compilerOptions from the project's own tsconfig.json, without following `extends` (it points into temp/)."""
    path = Path(project) / 'tsconfig.json'
    try:
        data = json.loads(strip_json_comments(path.read_text(encoding='utf-8')))
    except (OSError, ValueError):
        return {}
    opts = dict(data.get('compilerOptions') or {})
    for key in MACHINE_OPTIONS:
        opts.pop(key, None)
    return opts


def resources_of(exe):
    """The Creator Resources folder for an executable (macOS .app/Contents/MacOS/x, Windows <dir>/CocosCreator.exe)."""
    exe = Path(exe)
    for cand in (exe.parent.parent / 'Resources', exe.parent / 'resources', exe.parent / 'Resources', exe / 'Contents' / 'Resources'):
        if (cand / 'resources' / '3d' / 'engine').is_dir():
            return cand
    return None


def local_toolchain(creator=None, tsc=None):
    """{'declarations': <dir with cc.d.ts>, 'tsc': <tsc.js or tsc>, 'creator': ...} from the local 3.x Creator."""
    editors = []
    if creator:
        exe = find_creator.executable_of(Path(creator), sys.platform) or Path(creator)
        editors = [{'version': find_creator.app_version(exe) or '?', 'exe': str(exe)}]
    else:
        editors = [e for e in find_creator.installed_editors() if str(e.get('version', '')).startswith('3.')]
    for editor in editors:
        res = resources_of(editor['exe'])
        if not res:
            continue
        decl = res / 'resources' / '3d' / 'engine' / 'bin' / '.declarations'
        if not (decl / 'cc.d.ts').is_file():
            continue
        found = Path(tsc) if tsc else next((p for p in (
            res / 'resources' / '3d' / 'engine' / 'node_modules' / 'typescript' / 'lib' / 'tsc.js',
            res / 'app.asar.unpacked' / 'node_modules' / 'typescript' / 'lib' / 'tsc.js') if p.is_file()), None)
        if found is None and shutil.which('tsc'):
            found = Path(shutil.which('tsc'))
        if found:
            return {'declarations': decl, 'tsc': found, 'creator': editor}
    return None


def write_config(project, declarations, out_dir):
    """Write env shim + tsconfig into out_dir (outside the project). -> tsconfig path. Nothing under temp/ is named."""
    project, out_dir = Path(project).resolve(), Path(out_dir)
    shim = out_dir / 'cc-local-env.d.ts'
    shim.write_text('/// <reference path=%s/>\ndeclare const cc: never;\ndeclare module "cc/userland/macro" {}\n'
                    "declare module 'cc/env' {\n%s}\n" % (
                        json.dumps((Path(declarations) / 'cc.d.ts').as_posix()),
                        ''.join('    export const %s: boolean;\n' % k for k in ENV_FLAGS) +
                        '    export const NET_MODE: number;\n'), encoding='utf-8')
    opts = {'target': 'ES2015', 'module': 'ES2015', 'strict': False, 'experimentalDecorators': True,
            'isolatedModules': True, 'moduleResolution': 'node', 'forceConsistentCasingInFileNames': True,
            'lib': ['es2017', 'dom']}
    opts.update(project_options(project))
    opts.update({'noEmit': True, 'skipLibCheck': True, 'types': [], 'baseUrl': project.as_posix(),
                 'paths': {'db://assets/*': [(project / 'assets').as_posix() + '/*']}})
    cfg = {'compilerOptions': opts, 'files': [shim.as_posix()],
           'include': [(project / 'assets').as_posix() + '/**/*.ts'],
           'exclude': [(project / d).as_posix() for d in NEVER_READ]}
    path = out_dir / 'tsconfig.json'
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def stale_temp(project):
    """Engine paths named by temp/declarations that do not exist here (informational: the check never uses them)."""
    folder = Path(project) / 'temp' / 'declarations'
    missing = []
    for f in sorted(folder.glob('*.d.ts')) if folder.is_dir() else []:
        for ref in re.findall(r'<reference path="([^"]+)"', f.read_text(encoding='utf-8', errors='replace')):
            if not Path(ref).is_file():
                missing.append(ref)
    return missing


def run(project, creator=None, tsc=None, node=None, timeout=600):
    project = Path(project).resolve()
    result = {'project': str(project), 'skipped': [d + '/' for d in NEVER_READ], 'stale_temp_references': stale_temp(project)}
    if not (project / 'assets').is_dir():
        return dict(result, status='not_run', reason='no assets/ folder: not a Cocos 3.x project')
    tools = local_toolchain(creator, tsc)
    if not tools:
        return dict(result, status='not_run', reason='no Cocos Creator 3.x with engine declarations and tsc found '
                    '(find_creator.py); pass --creator or --tsc')
    tsc_path = Path(tools['tsc'])
    if tsc_path.suffix == '.js':
        node = node or shutil.which('node')
        if not node:
            return dict(result, status='not_run', reason='node not found (needed to run %s)' % tsc_path)
        argv = [node, str(tsc_path)]
    else:
        argv = [str(tsc_path)]
    with tempfile.TemporaryDirectory(prefix='ts-full-check-') as tmp:
        cfg = write_config(project, tools['declarations'], tmp)
        proc = subprocess.run(argv + ['-p', str(cfg), '--pretty', 'false'], capture_output=True, text=True,
                              errors='replace', timeout=timeout, stdin=subprocess.DEVNULL)
    lines = [l for l in (proc.stdout + proc.stderr).splitlines() if 'error TS' in l]
    return dict(result, status='passed' if proc.returncode == 0 else 'failed', errors=lines[:200],
                error_count=len(lines), tsc=str(tsc_path), declarations=str(tools['declarations']),
                creator=tools['creator'].get('version'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--project', required=True)
    ap.add_argument('--creator')
    ap.add_argument('--tsc')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    res = run(args.project, args.creator, args.tsc)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print('ts_full_check: %s%s' % (res['status'], ' (%s)' % res['reason'] if res.get('reason') else ''))
        if res.get('stale_temp_references'):
            print('  temp/declarations names %d engine path(s) missing on this machine; not used'
                  % len(res['stale_temp_references']))
        for line in res.get('errors', [])[:50]:
            print('  ' + line)
    return {'passed': 0, 'failed': 1}.get(res['status'], 2)


if __name__ == '__main__':
    sys.exit(main())
