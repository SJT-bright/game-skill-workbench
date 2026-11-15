#!/usr/bin/env python3
"""Prepare and prove the source baseline for a Creator 2.0–2.3 to 2.4.15 migration."""
import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import threading
from uuid import uuid4

import find_creator

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1] / 'remake-core' / 'scripts'
REPORT = Path('docs/english/creator-migration.json')
INSPECT = HERE / 'inspect_creator_migration.cjs'
SMOKE = HERE / 'creator_migration_smoke.mjs'
SCHEMA = 'english-creator-migration.v1'
TARGET = '2.4.15'
LEGACY_MINORS = {(2, 0), (2, 1), (2, 2), (2, 3)}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.close()
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def signature(root, files):
    rows = sorted((p.relative_to(root).as_posix(), file_sha(p)) for p in files)
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


def source_signature(project):
    """Scope of the migration snapshot, excluding images, caches and QA outputs."""
    filenames = ('project.json', 'tsconfig.json', 'jsconfig.json', 'package.json',
                 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml')
    files = [project / name for name in filenames if (project / name).is_file()]
    suffixes = {'.js', '.ts', '.json', '.fire', '.scene', '.prefab'}
    for folder in ('assets', 'settings', 'packages'):
        for p in (project / folder).rglob('*'):
            if not p.is_file() or 'node_modules' in p.relative_to(project).parts:
                continue
            if p.suffix in suffixes or (p.suffix == '.meta' and p.with_suffix('').suffix in suffixes):
                files.append(p)
    return signature(project, files)


def tool_signature():
    skills = HERE.parents[1]
    runtime = skills / 'cocos-game-check/package-check/scripts/runtime_regression'
    return signature(skills, [Path(__file__), HERE / 'find_creator.py', INSPECT, SMOKE,
                              HERE / 'browser_env.py', CORE / 'vendor/acorn.cjs',
                              runtime.parent / 'ego_test_page.mjs',
                              *(runtime / name for name in ('lib.mjs', 'engine_adapter.mjs'))])


def relative_web(project, path):
    name = PurePosixPath(path)
    if name.is_absolute() or '..' in name.parts or '\\' in path or ':' in path:
        raise ValueError('迁移记录的导出路径必须是工程相对路径。')
    web = (project / path).resolve()
    if not web.is_relative_to(project) or not (web / 'index.html').is_file():
        raise ValueError('迁移导出缺失。按记录恢复同版 Web，或用 build 生成迁移基线。')
    return web


def load(project):
    data = read(project / REPORT)
    if data.get('schema') != SCHEMA or data.get('target_version') != TARGET:
        raise ValueError('迁移记录的版本或格式无法识别。')
    return data


def prepare(project, original):
    if project == original:
        raise ValueError('迁移记录要写到独立工作副本。')
    version, _ = find_creator.project_version(original)
    if find_creator.parse_version(version)[:2] not in LEGACY_MINORS:
        return {'status': 'not_applicable', 'original_version': version}
    if not (project / 'assets').is_dir():
        raise ValueError('请先复制可编辑的 Cocos 工程。')
    original_config = original / 'project.json'
    copied_config = project / 'project.json'
    origin_id = read(original_config).get('id')
    copied_id = read(copied_config).get('id')
    if file_sha(original_config) != file_sha(copied_config) and not (origin_id and copied_id == origin_id):
        raise ValueError('原工程和工作副本的项目身份不一致。')
    identity = {'schema': SCHEMA, 'original_version': version, 'target_version': TARGET,
                'original_project_json_sha256': file_sha(original_config)}
    if (project / REPORT).exists():
        existing = load(project)
        if any(existing.get(k) != v for k, v in identity.items()):
            raise ValueError('已有迁移记录属于另一份原工程。')
        return existing
    result = {**identity, 'status': 'pending_build'}
    write(project / REPORT, result)
    return result


def audit(web):
    node = shutil.which('node')
    if not node:
        raise ValueError('此迁移路线需要 Node.js 来解析构建，使用随包解析器，无需安装 npm 库。')
    tables = []
    for bundle in sorted((web / 'assets').glob('*/index*.js')):
        result = subprocess.run([node, str(INSPECT)], input=bundle.read_bytes(), capture_output=True, timeout=45)
        if result.returncode:
            raise ValueError('无法解析迁移导出的模块表 %s：%s' %
                             (bundle.relative_to(web).as_posix(), result.stderr.decode('utf-8', 'replace')[-220:]))
        tables.extend(dict(row, bundle=bundle.relative_to(web).as_posix()) for row in json.loads(result.stdout))
    loaded = [row for row in tables if row['modules']]
    if not loaded or any(row['loader'] == 'unknown' for row in loaded):
        raise ValueError('未识别到可核对的 Creator 2.4 Web 模块表。使用目标编辑器的 debug Web 构建，先定位具体格式。')
    return {'status': 'blocked' if any(row['findings'] for row in loaded) else 'passed',
            'tables': loaded}


def candidate_web(project, record):
    candidate = record.get('candidate')
    if not candidate or find_creator.project_version(project)[0] != record['target_version']:
        raise ValueError('还没有目标引擎的迁移构建。')
    if candidate['source_sha256'] != source_signature(project) or candidate['tool_sha256'] != tool_signature():
        raise ValueError('迁移源码或专检规则已变化。重新核对受影响的迁移基线。')
    web = relative_web(project, candidate['web'])
    if signature(web, (p for p in web.rglob('*') if p.is_file())) != candidate['web_sha256']:
        raise ValueError('迁移导出和已核对的文件不同。恢复原导出或从修好的源码重新构建。')
    return web


def build(project):
    project = project.resolve()
    record = load(project)
    try:
        candidate_web(project, record)
    except (OSError, ValueError, KeyError):
        pass
    else:
        return record
    version, major = find_creator.project_version(project)
    if version != record['target_version'] or major != 2:
        raise ValueError(f'请先用 Creator {record["target_version"]} 打开工作副本升级。')
    if not shutil.which('node'):
        raise ValueError('迁移专检需要 Node.js。先在本机准备 Node.js 后继续。')
    editor = find_creator.choose(version, find_creator.installed_editors())['editor']
    if not editor or editor['version'] != version:
        raise ValueError(f'本机未找到 Creator {version}。先用 Creator Dashboard 安装该版本。')
    build_root = Path('build') / 'creator-migration' / uuid4().hex[:12]
    # Creator's asset registry keys and module resolution must see the same physical path.
    argv = find_creator.build_argv(editor, project, 2, 'web-mobile')
    argv[argv.index('--build') + 1] += ';md5Cache=false;buildPath=' + build_root.as_posix()
    before = source_signature(project)
    log = project / REPORT.parent / 'creator-migration-build.log'
    sys.path.insert(0, str(CORE))
    from preparation_cache import project_lock
    with project_lock(Path(tempfile.gettempdir()) / 'creator-migration-editor-slot'):
        if find_creator.busy() != []:
            raise ValueError('当前有 Creator 构建在运行，或无法确认构建占用。用 find_creator.py --busy 核对。')
        record.pop('candidate', None)
        record.pop('smoke', None)
        record['status'] = 'pending_build'
        write(project / REPORT, record)
        with log.open('wb') as output:
            result = subprocess.run(argv, cwd=project, stdout=output, stderr=subprocess.STDOUT, timeout=600)
    if result.returncode != 0:
        raise ValueError('Creator 构建失败，查看 docs/english/creator-migration-build.log。')
    web_name = (build_root / 'web-mobile').as_posix()
    web = relative_web(project, web_name)
    if before != source_signature(project):
        raise ValueError('构建中迁移输入发生变化。确认编辑器迁移已保存，再用当前源码构建。')
    result = audit(web)
    record['candidate'] = {'web': web_name, 'source_sha256': before, 'tool_sha256': tool_signature(),
                           'web_sha256': signature(web, (p for p in web.rglob('*') if p.is_file())), 'audit': result}
    record['status'] = 'blocked' if result['status'] == 'blocked' else 'awaiting_smoke'
    write(project / REPORT, record)
    return record


def observe(project, web, play, ready_node, ready_scene):
    import browser_env

    route = browser_env.plan('ego')
    if not route['route']:
        raise ValueError(route['problem'])
    ego = route['ego_browser']

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

    with ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(web))) as server:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        lib = HERE.parents[1] / 'cocos-game-check/package-check/scripts/runtime_regression/lib.mjs'
        settings = {'lib': lib.as_uri(), 'base': f'http://127.0.0.1:{server.server_port}', 'hostPage': '/index.html',
                    'space': browser_env.space_name('creator-migration', project.name), 'play': play,
                    'ready_node': ready_node, 'ready_scene': ready_scene}
        try:
            code = 'globalThis.CFG=' + json.dumps(settings) + ';\n' + SMOKE.read_text(encoding='utf-8')
            result = subprocess.run([ego, 'nodejs', '-e', code], capture_output=True, timeout=95)
        finally:
            server.shutdown()
            t.join()
    transcript = (result.stdout + b'\n' + result.stderr).decode('utf-8', 'replace')
    rows = [line for line in transcript.splitlines() if line.startswith('MIGRATION_EGO ')]
    if result.returncode or len(rows) != 1:
        detail = transcript.strip()[-900:]
        raise ValueError('Ego Lite 未返回本轮首页与开局证据。' + (f' 本轮输出 {detail}' if detail else ''))
    evidence = json.loads(rows[0].removeprefix('MIGRATION_EGO '))
    if (evidence.get('browser_route') != 'ego_taskspace' or evidence.get('space_finished') is not True
            or evidence.get('home') is not True or evidence.get('entered') is not True
            or evidence.get('engine') != TARGET):
        raise ValueError('Ego Lite 结果缺少目标引擎或实际开局证据。')
    return evidence


def smoke(project, play, ready_node, ready_scene):
    record = load(project)
    web = candidate_web(project, record)
    if record['candidate']['audit']['status'] != 'passed':
        raise ValueError('请先修复报告里的模块引用，再从同一份源码构建。')
    controls = {'play_node': play, 'ready_node': ready_node, 'ready_scene': ready_scene}
    if record['status'] == 'passed' and record.get('smoke', {}).get('controls') == controls:
        return record
    record.pop('smoke', None)
    record['status'] = 'awaiting_smoke'
    write(project / REPORT, record)
    evidence = observe(project, web, play, ready_node, ready_scene)
    candidate_web(project, record)
    record['smoke'] = dict(evidence, controls=controls, web_sha256=record['candidate']['web_sha256'])
    record['status'] = 'passed'
    write(project / REPORT, record)
    return record


def require_ready(project):
    """Stage 2 consumes the existing proof. Ordinary projects do no scan or browser work."""
    if not (project / REPORT).exists():
        version = ()
        try:
            value, _ = find_creator.project_version(project)
            version = find_creator.parse_version(value) or ()
        except ValueError:
            pass
        route_note = project / REPORT.parent / 'engine.txt'
        recorded_upgrade = route_note.is_file() and re.search(
            r'原工程\s+2\.[0-3]\.\d+[^\n]*2\.4\.15', route_note.read_text(encoding='utf-8-sig'))
        if version[:2] in LEGACY_MINORS or recorded_upgrade:
            raise ValueError('已识别到旧引擎迁移。先用 creator_migration.py prepare 登记中文原工程和工作副本。')
        return
    record = load(project)
    evidence = record.get('smoke') or {}
    if (record['status'] != 'passed' or evidence.get('entered') is not True or evidence.get('home') is not True
            or evidence.get('browser_route') != 'ego_taskspace' or evidence.get('space_finished') is not True
            or evidence.get('engine') != TARGET or record.get('candidate', {}).get('audit', {}).get('status') != 'passed'
            or evidence.get('web_sha256') != record.get('candidate', {}).get('web_sha256')):
        raise ValueError('旧引擎迁移待完成。先运行 creator_migration.py build，再用 smoke 核对首页和开局。')
    candidate_web(project, record)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for cmd in ('prepare', 'build', 'smoke', 'check'):
        p = sub.add_parser(cmd)
        p.add_argument('--project', required=True, type=Path)
        if cmd == 'prepare':
            p.add_argument('--original', required=True, type=Path)
        if cmd == 'smoke':
            p.add_argument('--play-node', required=True)
            target = p.add_mutually_exclusive_group(required=True)
            target.add_argument('--ready-node')
            target.add_argument('--ready-scene')
    p = sub.add_parser('audit', help='只读诊断现成 Web，不写迁移通过记录')
    p.add_argument('--web', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == 'audit':
            result = audit(args.web.resolve())
        else:
            sys.path.insert(0, str(CORE))
            from preparation_cache import project_lock
            project = args.project.resolve()
            with project_lock(project):
                if args.cmd == 'prepare':
                    result = prepare(project, args.original.resolve())
                elif args.cmd == 'build':
                    result = build(project)
                elif args.cmd == 'smoke':
                    result = smoke(project, args.play_node, args.ready_node, args.ready_scene)
                else:
                    require_ready(project)
                    result = load(project) if (project / REPORT).exists() else {'status': 'not_applicable'}
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
