#!/usr/bin/env python3
"""tiktok_finalize (v7.7, design D77 sections 1-2): install the platform-kit standard parts at packaging time.

    tiktok_finalize.py init    --project P --board remake|localize      write the new-game marker (start of a project)
    tiktok_finalize.py adopt   --project P                               a legacy game switches to the kit (marker)
    tiktok_finalize.py decide  [--project P] [--native N | --zip Z]      new or legacy, and why
    tiktok_finalize.py source  --project P --board B [--app-id ID]      source phase, BEFORE the Cocos build
    tiktok_finalize.py native  --native N --project P --board B [--app-id ID]
                                                                         native phase on the build folder (in place)
    tiktok_finalize.py inventory --project P                             list the original's platform code (English)
    --policy new|legacy on source/native/decide is for tests and calibration only; the package writers never pass it.

Library (the two package writers call these; package_gates.kit_parts reuses the checks):
    finalize_source(project, board, ...) -> record   (also written to <project>/.tiktok-kit/finalize-source.json)
    finalize_native(native, project, board, app_id, ...) -> record   (goes into the writer report and receipt)
    check_source_record(project, options=None) -> findings (K5_source_finalized; with the writer's options it also
        requires the same --keep-webp-exception as the source record's `options`)
    check_finalize_record(record, files) -> findings (K4_finalize_ran)
A record with any block means: refuse the package.
"""
import argparse
import hashlib
import importlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402

SOURCE_RECORD = Path('.tiktok-kit') / 'finalize-source.json'
SOURCE_TREES = ('assets', 'build-templates', 'settings')
SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', '.tiktok-kit', '__MACOSX'}
SOURCE_STEPS = T.SOURCE_STEPS                       # images, kit_sources, build_templates, settings
# startup runs before touch/storage: whether main.js is the kit main.js decides where their load lines go.
NATIVE_STEPS = ('adapter', 'startup', 'touch', 'storage', 'login', 'appid', 'png', 'structure')
JUNK = ('.DS_Store', 'Thumbs.db')


def source_sha256(project):
    """sha256 over (relative path, sha256 of content) of every file in assets/, build-templates/, settings/
    (same scheme as logic_regressions.source_digest, wider scope). Tool and cache folders are skipped."""
    project = Path(project)
    digest = hashlib.sha256()
    for tree in SOURCE_TREES:
        base = project / tree
        if not base.is_dir():
            continue
        for p in sorted(base.rglob('*')):
            rel = p.relative_to(project)
            if not p.is_file() or p.is_symlink() or SKIP & set(rel.parts) or p.name in JUNK or p.name.startswith('._'):
                continue
            digest.update(rel.as_posix().encode('utf-8') + b'\0' + hashlib.sha256(p.read_bytes()).digest())
    return digest.hexdigest()


def _step(name):
    return importlib.import_module('tiktok_finalize_steps.' + name)


def _run_steps(ctx, names):
    results = []
    for name in names:
        try:
            module = _step(name)
        except Exception as error:  # noqa: BLE001 - a missing or broken step refuses, never passes
            results.append({'step': name, 'state': 'error', 'changed': [], 'warnings': [], 'info': [],
                            'blocks': [T.finding('K_step_missing', 'block', 'finalize step %s not importable: %r'
                                                 % (name, error))]})
            continue
        try:
            out = module.apply(ctx)
        except T.KitError as error:
            out = {'step': name, 'state': 'error', 'changed': [], 'warnings': [], 'info': [],
                   'blocks': [T.finding('K_kit_unusable', 'block', str(error))]}
        except Exception as error:  # noqa: BLE001
            out = {'step': name, 'state': 'error', 'changed': [], 'warnings': [], 'info': [],
                   'blocks': [T.finding('K_step_error', 'block', 'finalize step %s raised: %r' % (name, error))]}
        out = dict(out)
        out.setdefault('step', name)
        for key in ('changed', 'blocks', 'warnings', 'info'):
            out.setdefault(key, [])
        results.append(out)
    return results


def _collect(results):
    blocks = [dict(b, step=r['step']) for r in results for b in r['blocks']]
    warnings = [dict(w, step=r['step']) for r in results for w in r['warnings']]
    return blocks, warnings


def decide_policy(project=None, native=None, files=None, override=None, legacy=None, record=None):
    """Design section 2. override is for tests/calibration only. A source record that says new keeps it new
    (a policy can only become stricter)."""
    if override:
        if override not in T.POLICIES:
            raise ValueError('policy must be new or legacy')
        return {'policy': override, 'reason': '--policy %s (tests / calibration only)' % override,
                'scene_uuids': [], 'legacy_match': []}
    out = P.decide(project=project, native=native, files=files, legacy=legacy)
    if record and record.get('policy') == 'new' and out['policy'] != 'new':
        out = dict(out, policy='new', reason='source record says new (%s); a policy only becomes stricter'
                   % record.get('decision', {}).get('reason'))
    return out


def _trim_decision(decision):
    out = {k: decision.get(k) for k in ('policy', 'reason', 'legacy_match', 'legacy_list', 'legacy_frozen')}
    out['scene_uuids'] = list(decision.get('scene_uuids') or [])[:20]
    return out


# Options the source stage records and the writer must repeat exactly (W-D1 request 3; K5 compares them).
RECORDED_OPTIONS = ('keep_webp_exception',)


def recorded_options(options):
    """The options a finalize run is held to, normalised: {'keep_webp_exception': '<reason>' or ''}."""
    options = options or {}
    return {k: str(options.get(k) or '').strip() for k in RECORDED_OPTIONS}


def webp_exception_3x(engine, options):
    """DECISIONS 13:25: v7.7 has no 3.x WebP exception. -> [block finding] or []."""
    if engine == 3 and recorded_options(options)['keep_webp_exception']:
        from tiktok_finalize_steps import images
        return [T.finding('K_webp_exception_3x', 'block', images.WEBP_EXCEPTION_3X)]
    return []


def finalize_source(project, board, engine=None, policy=None, app_id=None, manifest=None, legacy=None,
                    options=None, steps=SOURCE_STEPS, write_record=True):
    project = Path(project)
    manifest = manifest or T.load_manifest()
    engine = engine or P.engine_of_project(project)
    decision = decide_policy(project=project, override=policy, legacy=legacy)
    ctx = T.Ctx('source', project, project=project, board=board, engine=engine, policy=decision['policy'],
                manifest=manifest, app_id=app_id, options=options)
    refused = webp_exception_3x(engine, options)
    results = [] if refused else _run_steps(ctx, steps)       # a refused option changes nothing
    blocks, warnings = _collect(results)
    blocks = refused + blocks
    if engine not in (2, 3):
        blocks.append(T.finding('K_engine_unknown', 'block', 'Cocos version of the project not readable'))
    record = {'kind': 'finalize-source', 'kit_version': manifest.version, 'policy': decision['policy'],
              'decision': _trim_decision(decision), 'board': board, 'engine': engine,
              'policy_override': bool(policy), 'options': recorded_options(options), 'steps': results,
              'blocks': blocks, 'warnings': warnings,
              'created': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'source_sha256': source_sha256(project),
              'backups': str(project / '.tiktok-kit')}
    if write_record:
        path = project / SOURCE_RECORD
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return record


def read_source_record(project):
    try:
        return json.loads((Path(project) / SOURCE_RECORD).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return None


def check_source_record(project, manifest=None, options=None):
    """K5_source_finalized (package writers only): the source record exists, has no block, was made with this kit
    version and the project has not changed since (assets/, build-templates/, settings/). options = the writer's
    finalize options (None = not compared, e.g. preflight): --keep-webp-exception must equal the source record's."""
    fix = 'run `tiktok_finalize.py source --project %s --board <board>` and build again' % project
    if not project:
        return [T.finding('K5_source_finalized', 'block', 'no --project given: the source record cannot be checked; '
                          + fix)]
    manifest = manifest or T.load_manifest()
    record = read_source_record(project)
    if not record:
        return [T.finding('K5_source_finalized', 'block', 'source record %s missing; %s' % (SOURCE_RECORD, fix))]
    out = []
    if record.get('kit_version') != manifest.version:
        out.append(T.finding('K5_source_finalized', 'block', 'source record is for kit %s, current kit %s; %s'
                             % (record.get('kit_version'), manifest.version, fix)))
    if record.get('source_sha256') != source_sha256(project):
        out.append(T.finding('K5_source_finalized', 'block', 'project changed after the source phase; ' + fix))
    if record.get('blocks'):
        out.append(T.finding('K5_source_finalized', 'block', 'source phase refused: %s'
                             % '; '.join('%s: %s' % (b['id'], b['message']) for b in record['blocks'][:3])))
    if record.get('policy_override'):
        out.append(T.finding('K5_source_finalized', 'block', 'source record was made with --policy (tests only); '
                             + fix))
    if options is not None:
        have = recorded_options(record.get('options'))     # a record without options used none
        want = recorded_options(options)
        for key in RECORDED_OPTIONS:
            if have[key] != want[key]:
                flag = '--' + key.replace('_', '-')
                out.append(T.finding('K5_source_finalized', 'block', '%s differs: source phase %s, writer %s; '
                                     'the source and native phases must use the same option (%s)' % (
                                         flag, repr(have[key]) if have[key] else 'without it',
                                         repr(want[key]) if want[key] else 'without it',
                                         fix if not want[key] else fix + ' ' + flag + ' <same reason>'),
                                     {'option': key, 'source': have[key], 'writer': want[key]}))
    return out


def _native_files(native):
    return T.Ctx('native', native).files()


def finalize_native(native, project=None, board=None, app_id=None, policy=None, manifest=None, legacy=None,
                    options=None, steps=NATIVE_STEPS):
    native = Path(native)
    manifest = manifest or T.load_manifest()
    names = [p.relative_to(native).as_posix() for p in native.rglob('*') if p.is_file()]
    engine = P.engine_of_names(names)
    record_src = read_source_record(project) if project else None
    decision = decide_policy(project=project, native=native, override=policy, legacy=legacy, record=record_src)
    ctx = T.Ctx('native', native, project=project, board=board, engine=engine, policy=decision['policy'],
                manifest=manifest, app_id=app_id, options=options)
    refused = webp_exception_3x(engine, options)
    results = [] if refused else _run_steps(ctx, steps)       # a refused option changes nothing
    blocks, warnings = _collect(results)
    blocks = refused + blocks
    if engine not in (2, 3):
        blocks.append(T.finding('K_engine_unknown', 'block', 'not a Cocos 2.4 / 3.x mini-game build: %s' % native))
    final = {}
    for r in results:
        for c in r['changed']:
            final[c['file']] = c['after_sha256']
    record = {'kind': 'finalize-native', 'kit_version': manifest.version, 'policy': decision['policy'],
              'decision': _trim_decision(decision), 'board': board, 'engine': engine,
              'policy_override': bool(policy), 'steps': results, 'blocks': blocks, 'warnings': warnings,
              'files_after': final, 'removed_dir': str(ctx.removed_dir),
              'created': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    record['table'] = summary_table(record)
    return record


def check_finalize_record(record, files):
    """K4_finalize_ran (package writers only): the native record of THIS run exists, has no block, and every file
    it wrote is in the package with exactly the bytes it wrote (a moved-away file is not in the package)."""
    if not record or record.get('kind') != 'finalize-native':
        return [T.finding('K4_finalize_ran', 'block', 'no finalize record for this package (finalize_native did not '
                          'run in the writer)')]
    out = []
    if record.get('blocks'):
        out.append(T.finding('K4_finalize_ran', 'block', 'finalize refused: %s' % '; '.join(
            '%s: %s' % (b['id'], b['message']) for b in record['blocks'][:3])))
    for rel, sha in sorted((record.get('files_after') or {}).items()):
        have = files.get(rel)
        if sha is None and have is not None:
            out.append(T.finding('K4_finalize_ran', 'block', '%s was moved away by finalize but is in the package'
                                 % rel))
        elif sha is not None and (have is None or T.sha256(have) != sha):
            out.append(T.finding('K4_finalize_ran', 'block', '%s differs from what finalize wrote' % rel))
    return out


ROW = {'absent': '已装', 'kit_current': '原本就有', 'kit_old': '换成新版标准件', 'own': '换成标准件',
       'n/a': '不适用', 'skipped': '不适用', 'conflict': '拒绝', 'error': '拒绝'}


def summary_table(record):
    """Chinese rows for the delivery reply: one per step."""
    rows = []
    for r in record['steps']:
        state = r.get('state') or 'n/a'
        if r['blocks']:
            text = '拒绝：' + r['blocks'][0]['message'][:80]
        elif record['policy'] == 'legacy' and any(w['id'].startswith(('K_W_own', 'K3', 'K_W_kit')) for w in r['warnings']):
            text = '旧游戏保留自写（警告）'
        elif state in ('absent', 'own', 'kit_old') and not r['changed']:
            text = '旧游戏保留自写（警告）' if record['policy'] == 'legacy' and state != 'absent' else \
                '没有装（%s）' % ('旧游戏不装' if record['policy'] == 'legacy' else state)
        elif state == 'kit_current' and r['changed']:
            # W-D4 request 4: the file was already the kit's (3.x: copied from build-templates/), but this run
            # changed something, e.g. inserted its load line in game.js. "原本就有" would hide that.
            text = '已装（插加载行）' if any('load line' in (c.get('what') or '') for c in r['changed']) \
                else '已装（本次有改动）'
        else:
            text = ROW.get(state, state)
        rows.append({'step': r['step'], 'result': text, 'changed': len(r['changed']), 'warnings': len(r['warnings'])})
    return rows


def table_markdown(record):
    lines = ['| 标准件 | 结果 | 改动文件 | 警告 |', '|---|---|---|---|']
    lines += ['| %s | %s | %d | %d |' % (r['step'], r['result'], r['changed'], r['warnings']) for r in record['table']]
    return '\n'.join(lines)


# ---------------------------------------------------------------- inventory (English originals, design section 4)
INVENTORY = {
    'rewarded_ad': r'createRewardedVideoAd|ShowVideo\s*\(|showRewardedVideo',
    'growth_missions': r'addShortcut|checkShortcut|startEntranceMission|getShortcutMissionReward|'
                       r'getEntranceMissionReward',
    'touch': r'onTouchStart|getTouchesByEvent|screenX',
    'startup': r'loadSubpackage|cc\.assetManager\.loadBundle|downloader',
    'storage': r'getStorageSync|setStorageSync|localStorage\.(?:get|set)Item',
    'share_jump_stats': r'shareAppMessage|navigateToMiniProgram|reportAnalytics|showShareMenu|aldSendEvent',
    'login': r'\.login\s*\(',
}


def inventory(project):
    import re
    project = Path(project)
    out = {k: [] for k in INVENTORY}
    rx = {k: re.compile(v) for k, v in INVENTORY.items()}
    for p in sorted((project / 'assets').rglob('*')) if (project / 'assets').is_dir() else []:
        if p.suffix not in ('.js', '.ts') or not p.is_file() or SKIP & set(p.relative_to(project).parts):
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        for key, r in rx.items():
            n = len(r.findall(text))
            if n:
                out[key].append({'file': p.relative_to(project).as_posix(), 'hits': n})
    return {'project': str(project), 'created': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'categories': out}


def _print(record):
    print(json.dumps({k: record[k] for k in ('policy', 'engine', 'blocks', 'warnings') if k in record} |
                     {'decision': record.get('decision', {}).get('reason')}, ensure_ascii=False, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('init', 'adopt', 'decide', 'source', 'native', 'inventory'):
        p = sub.add_parser(name)
        p.add_argument('--project')
        p.add_argument('--board', choices=('remake', 'localize'))
        p.add_argument('--native')
        p.add_argument('--zip')
        p.add_argument('--app-id')
        p.add_argument('--policy', choices=T.POLICIES, help='tests and calibration only')
        p.add_argument('--keep-webp-exception', metavar='REASON')
    args = ap.parse_args(argv)
    options = {'keep_webp_exception': args.keep_webp_exception} if args.keep_webp_exception else {}
    if args.cmd in ('init', 'adopt'):
        if not args.project:
            ap.error('--project is required')
        manifest = T.load_manifest()
        data = P.write_marker(args.project, args.board, manifest.version, reason=args.cmd)
        print(json.dumps(data, ensure_ascii=False))
        return 0
    if args.cmd == 'inventory':
        result = inventory(args.project)
        path = Path(args.project) / 'docs' / 'english' / 'platform-inventory.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(path)
        return 0
    if args.cmd == 'decide':
        if args.zip:
            ident = P.identity_from_zip(args.zip)
            out = P.decide(uuids=ident['scenes'], assets=ident['assets'])
        else:
            out = decide_policy(project=args.project, native=args.native, override=args.policy)
        print(json.dumps(out, ensure_ascii=False, indent=1, default=sorted))
        return 0
    if not args.board:
        ap.error('--board is required')
    if args.cmd == 'source':
        record = finalize_source(args.project, args.board, policy=args.policy, app_id=args.app_id, options=options)
    else:
        if not args.native:
            ap.error('--native is required')
        record = finalize_native(args.native, args.project, args.board, args.app_id, policy=args.policy,
                                 options=options)
        print(table_markdown(record))
    _print(record)
    return 1 if record['blocks'] else 0


if __name__ == '__main__':
    sys.exit(main())
