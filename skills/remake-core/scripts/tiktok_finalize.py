#!/usr/bin/env python3
"""tiktok_finalize (v7.7, design D77 sections 1-2): install the platform-kit standard parts at packaging time.

    tiktok_finalize.py init    --project P --board remake|localize      write the new-game marker (start of a project)
                               [--base <base folder or source ZIP> | --no-base-why "..."]
                                   v7.8 H8: also record the base game's images and sounds (art_records.py)
    tiktok_finalize.py adopt   --project P                               a legacy game switches to the kit (marker)
    tiktok_finalize.py decide  [--project P] [--native N | --zip Z]      new or legacy, and why
    tiktok_finalize.py source  --project P --board B [--app-id ID]      prepare source and check Sprite ratios before trial
    tiktok_finalize.py check-source --project P                        verify the existing source record after trial
    tiktok_finalize.py native  --native N --project P --board B [--app-id ID]
                                                                         native phase on the build folder (in place)
    tiktok_finalize.py inventory --project P                             list the original's platform code (English)
                               生成时预防 P01/P14/P10: also rewire_todo, delete_list, kit_copies (tiktok_rewire.py)
    tiktok_finalize.py rewire-ads --project P                            stage 2: rewire the original's rewarded ads
                               to RewardedService (generated AdBridge.js) and hard-coded growth rewards to
                               growthReward(); what it cannot recognise stays in rewire_todo (tiktok_rewire.py)
    tiktok_finalize.py sync    --project P --board B [--native N]       生成时预防 P02: before EVERY build (and on the
                               bytedance build folder after it, --native): put the standard parts back to the kit
                               bytes (kit_sources, build_templates; with --native also startup, touch, storage) and
                               install parts/GameUIKit.js (3.x: parts-3x/GameUIKit.ts, R4B); R4B: host-shim and
                               the 3.x boot guard lines (startup step). No images / PNG / settings / art steps, ~1 s.
                               Legacy games: report only, nothing written. Record: <project>/.tiktok-kit/sync.json
                               (it is not the source record: the writers still need `source`).
    --policy new|legacy on source/native/decide is for tests and calibration only; the package writers never pass it.

Library (the two package writers call these; package_gates.kit_parts reuses the checks):
    finalize_source(project, board, ...) -> record   (also written to <project>/.tiktok-kit/finalize-source.json)
    finalize_native(native, project, board, app_id, ...) -> record   (goes into the writer report and receipt)
    check_source_record(project, options=None) -> findings (K5_source_finalized; with the writer's options it also
        requires the same --keep-webp-exception as the source record's `options`)
    check_finalize_record(record, files) -> findings (K4_finalize_ran)
A record with any block means: refuse the package.
v7.8 (U7 补): `source` reads the art receipt (<project>/.tiktok-kit/art-receipt.json, art_receipt.py) before its steps
and, only when every image still matched it, carries it to the image bytes its `images` step wrote (record key
`art_receipt`). The source step `art_static` blocks squashed SIMPLE/CUSTOM sprites and colliders without a visible picture (no
popup-dim opacity limit since Saul 10-31).
v7.8 (H8 / H10): `source` also follows its own image conversions in docs/art/generated.json (derived entries) and
docs/art/base-assets.json (record key `art_records`), so a recorded picture never needs a manual re-record after it.
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
from preparation_cache import serialized  # noqa: E402

SOURCE_RECORD = Path('.tiktok-kit') / 'finalize-source.json'
SOURCE_TREES = ('assets', 'build-templates', 'settings')
SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', '.tiktok-kit', '__MACOSX'}
SOURCE_STEPS = T.SOURCE_STEPS        # images, kit_sources, build_templates, settings, orientation, art_static
# startup runs before touch/storage: whether main.js is the kit main.js decides where their load lines go.
NATIVE_STEPS = ('adapter', 'startup', 'touch', 'storage', 'rewarded', 'login', 'appid', 'png', 'structure')  # rewarded: R4F1
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


def _preparation_session(ctx):
    """Reuse is optional; inability to fingerprint never substitutes for executing a step."""
    if ctx.phase != 'source' or ctx.policy != 'new' or not ctx.project:
        return None
    try:
        from preparation_cache import Session
        return Session(ctx)
    except Exception:  # Optional reuse never replaces real preparation on lookup errors.
        return None


def _run_steps(ctx, names, preparation=None):
    results = []
    preparation = preparation or _preparation_session(ctx)
    for name in names:
        try:
            module = _step(name)
        except Exception as error:  # noqa: BLE001 - a missing or broken step refuses, never passes
            results.append({'step': name, 'state': 'error', 'changed': [], 'warnings': [], 'info': [],
                            'blocks': [T.finding('K_step_missing', 'block', 'finalize step %s not importable: %r'
                                                 % (name, error))]})
            continue
        try:
            out = preparation.apply(name, lambda: module.apply(ctx)) if preparation else module.apply(ctx)
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


def decide_policy(project=None, native=None, files=None, override=None, legacy=None, record=None, board=None):
    """Design section 2. override is for tests/calibration only. A source record that says new keeps it new
    (a policy can only become stricter). board: v7.8 B27, a remake is never legacy by sub-asset uuids alone."""
    if override:
        if override not in T.POLICIES:
            raise ValueError('policy must be new or legacy')
        return {'policy': override, 'reason': '--policy %s (tests / calibration only)' % override,
                'scene_uuids': [], 'legacy_match': []}
    out = P.decide(project=project, native=native, files=files, legacy=legacy, board=board)
    if record and record.get('policy') == 'new' and out['policy'] != 'new':
        out = dict(out, policy='new', reason='source record says new (%s); a policy only becomes stricter'
                   % record.get('decision', {}).get('reason'))
    return out


def _trim_decision(decision):
    out = {k: decision.get(k) for k in ('policy', 'reason', 'legacy_match', 'legacy_list', 'legacy_frozen')}
    for key in ('auto_new', 'marker_written'):          # v7.8 B27
        if decision.get(key):
            out[key] = decision[key]
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


@serialized
def finalize_source(project, board, engine=None, policy=None, app_id=None, manifest=None, legacy=None,
                    options=None, steps=SOURCE_STEPS, write_record=True):
    project = Path(project)
    manifest = manifest or T.load_manifest()
    engine = engine or P.engine_of_project(project)
    decision = decide_policy(project=project, override=policy, legacy=legacy, board=board)
    if decision.get('auto_new') and write_record:
        # v7.8 B27: a game opened from a starter pack (or a remake) that only sub-asset uuids tie to a listed game is
        # new; write the marker now so callers without a board (writers, art_receipt, logic_check) agree, even when
        # the session never ran init.
        P.write_marker(project, board, manifest.version, reason='source (auto: %s)' % decision['auto_new'])
        decision = dict(decision, marker_written=True)
    ctx = T.Ctx('source', project, project=project, board=board, engine=engine, policy=decision['policy'],
                manifest=manifest, app_id=app_id, options=options)
    ctx.preparation_policy_override = bool(policy)
    refused = webp_exception_3x(engine, options)
    art_before = _art_receipt_before(project, board, decision['policy']) if write_record else None
    records_before = _art_records_before(project) if write_record else None
    preparation_session = _preparation_session(ctx)
    results = [] if refused else _run_steps(ctx, steps, preparation_session)  # a refused option changes nothing
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
    # Preserve the exact preparation conditions separately from the historical public
    # RECORDED_OPTIONS contract. Consumers can verify existing evidence, not invent a pass.
    from preparation_cache import context as preparation_context
    record['preparation_context'] = preparation_context(ctx)
    if art_before is not None:
        record['art_receipt'] = _art_receipt_carry(project, art_before)
    if records_before is not None:
        record['art_records'] = _art_records_carry(project, records_before)
    if decision['policy'] == 'new' and not blocks:
        try:
            from preparation_cache import source_pipeline_binding
            record['preparation_binding'] = source_pipeline_binding(ctx, steps, preparation_session)
        except Exception:
            pass  # Unknown scopes still executed; there is no fabricated reuse proof.
    if write_record:
        path = project / SOURCE_RECORD
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return record


def _art_receipt_before(project, board, policy):
    """v7.8 U7（补）: the art receipt as it stands BEFORE any source step (art_receipt.check, read only)."""
    try:
        import art_receipt
        return art_receipt.check(project, board, policy)
    except Exception as error:  # noqa: BLE001 - never stops the source phase; the writers check the receipt again
        return {'state': 'error', 'level': 'warn', 'message': repr(error)}


def _art_receipt_carry(project, before):
    """The images step converts WebP and shrinks textures, so the bytes art_check fingerprinted change here. Only when
    every image matched the receipt before this run is the receipt moved to the bytes this run wrote (art_receipt.carry);
    otherwise it is left alone and the writers still say 重跑 art_check. -> short note for the source record."""
    note = {'before': before.get('state'), 'carried': False}
    try:
        import art_receipt
        if art_receipt.carry(project, 'tiktok_finalize source', before) is not None:
            after = art_receipt.check(project, before.get('board'), before.get('policy'))
            note.update(carried=True, after=after.get('state'))
    except Exception as error:  # noqa: BLE001
        note['error'] = repr(error)
    return note


def _art_records_before(project):
    """v7.8 H8 / H10: image and sound hashes before the steps, so the pictures the images step converts or shrinks stay
    recorded (docs/art/generated.json gets derived entries, base-assets.json keeps knowing a converted base file)."""
    try:
        import art_records
        return art_records.snapshot(project)
    except Exception:  # noqa: BLE001 - recording never stops the source phase
        return None


def _art_records_carry(project, before):
    try:
        import art_records
        return art_records.carry(project, before, 'tiktok_finalize source')
    except Exception as error:  # noqa: BLE001
        return {'error': repr(error)}


def record_base_at_init(project, board, base=None, no_base_why=None):
    """v7.8 H8, `init --base <folder or ZIP>` / `init --no-base-why "..."`: record the base game's images and sounds
    (docs/art/base-assets.json) at project start. -> short text for the console (None for English games)."""
    import art_records
    if base:
        data = art_records.record_base(project, base)
        return '底子已记下：%s（图 %d、模型内嵌贴图 %d、声音 %d）→ %s' % (
            data['base'], data['counts']['images'], data['counts']['embedded'], data['counts']['audio'],
            Path(project) / art_records.BASE_FILE)
    if no_base_why:
        art_records.record_none(project, no_base_why)
        return '已记下没有底子：%s' % no_base_why
    if board == 'remake' and not (Path(project) / art_records.BASE_FILE).is_file():
        return ('还没记底子（H8：美术检查会因此不通过）。有底子：init 加 --base <底子工程文件夹或源码 ZIP>，或跑 %s；'
                '从零做：--no-base-why "<原因>"' % (art_records.BASE_CMD % project))
    return None


def read_source_record(project):
    try:
        record = json.loads((Path(project) / SOURCE_RECORD).read_text(encoding='utf-8'))
        return record if isinstance(record, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def check_source_record(project, manifest=None, options=None):
    """K5_source_finalized (package writers only): the source record exists, has no block, was made with this kit
    version and the project has not changed since (assets/, build-templates/, settings/). options = the writer's
    finalize options (None = not compared, e.g. preflight): --keep-webp-exception must equal the source record's."""
    fix = ('run `tiktok_finalize.py source --project %s --board <board>`; unchanged steps reuse their '
           'content-bound evidence; only changed or unproved dependencies execute') % project
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
    # New receipts also bind external inputs and rule bytes which the old source hash
    # did not cover. Old receipts remain old receipts; they are never re-labelled cached.
    preparation = record.get('preparation_context')
    if isinstance(preparation, dict) and record.get('preparation_binding') and record.get('policy') == 'new':
        from preparation_cache import source_pipeline_binding
        ctx = T.Ctx('source', Path(project), project=Path(project), board=record.get('board'),
                    engine=P.engine_of_project(Path(project)), policy=record.get('policy'), manifest=manifest,
                    app_id=preparation.get('app_id'), options=preparation.get('options') or {})
        ctx.preparation_policy_override = bool(record.get('policy_override'))
        names = [r.get('step') for r in record.get('steps') or [] if r.get('step')]
        try:
            current_binding = source_pipeline_binding(ctx, names)
        except Exception:
            current_binding = None
        if current_binding != record['preparation_binding']:
            pending = source_preparation_plan(project, manifest=manifest, record=record).get('execute', [])
            out.append(T.finding('K5_source_finalized', 'block',
                                'preparation dependencies changed or have no current proof: %s; %s'
                                % (', '.join(pending) or 'pipeline identity', fix), {'steps': pending}))
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


def source_preparation_plan(project, manifest=None, record=None):
    """Read-only plan for the exact steps in a source receipt; no source/writer mutation."""
    record = record or read_source_record(project) or {}
    prior = record.get('preparation_context') or {}
    manifest = manifest or T.load_manifest()
    ctx = T.Ctx('source', Path(project), project=Path(project), board=record.get('board'),
                engine=P.engine_of_project(Path(project)), policy=record.get('policy'), manifest=manifest,
                app_id=prior.get('app_id'), options=prior.get('options') or {})
    ctx.preparation_policy_override = bool(record.get('policy_override'))
    session = _preparation_session(ctx)
    plan = {'reuse': [], 'execute': []}
    for result in record.get('steps') or []:
        name = result.get('step')
        if not name:
            continue
        hit = None
        try:
            hit = session.lookup(name)[2] if session else None
        except Exception:
            pass
        plan['reuse' if hit and not result.get('blocks') else 'execute'].append(name)
    return plan


def check_trial_source(project, board, manifest=None, options=None):
    """Read the current source record, including the already executed Sprite ratio check."""
    problems = check_source_record(project, manifest, options)
    if problems:
        return problems
    record = read_source_record(project) or {}
    if record.get('board') != board or not any(
        step.get('step') == 'art_static' and step.get('state') in ('kit_current', 'n/a') and not step.get('blocks')
        for step in (record.get('steps') or []) if isinstance(step, dict)
    ):
        return [T.finding('K_trial_sprite_aspect', 'block',
                          '试玩前缺当前 Sprite 比例检查记录，请先执行 tiktok_finalize.py source --project <工程> --board ' + board)]
    return []


PREPARED_NATIVE = Path('.tiktok-kit/native-prepared')


def prepared_source_identity(project):
    record = read_source_record(project)
    if not record or not record.get('source_sha256'):
        raise ValueError('缺少当前源码段记录')
    keys = ('source_sha256', 'kit_version', 'board', 'policy', 'options')
    return {key: record.get(key) for key in keys}


def record_prepared_native(project, native, source_identity):
    """Seal successful English Native preparation, before preview reads the build."""
    import os
    import tempfile
    from verify_native_zip import native_directory_digest

    if prepared_source_identity(project) != source_identity:
        raise ValueError('源码记录在 Native 处理期间变化，请重新核对候选')
    native_sha = native_directory_digest(native)
    folder = Path(project) / PREPARED_NATIVE
    folder.mkdir(parents=True, exist_ok=True)
    record = {'schema': 'english-prepared-native.v1', 'source': source_identity,
              'native_tree_sha256': native_sha}
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=folder, delete=False) as f:
        temp = Path(f.name)
        try:
            json.dump(record, f, ensure_ascii=False)
            f.write('\n')
            f.close()
            os.replace(temp, folder / (native_sha + '.json'))
        finally:
            temp.unlink(missing_ok=True)
    return native_sha


def check_prepared_native(project, native):
    """Return the current candidate identity and its independent preparation record."""
    from verify_native_zip import native_directory_digest

    native_sha = native_directory_digest(native)
    path = Path(project) / PREPARED_NATIVE / (native_sha + '.json')
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
        if record != {'schema': 'english-prepared-native.v1',
                       'source': prepared_source_identity(project), 'native_tree_sha256': native_sha}:
            raise ValueError('记录与当前源码或 Native 不符')
    except (OSError, ValueError) as exc:
        raise ValueError('当前 Native 缺少同版准备证据。请核对实际构建来源，在试玩前执行 '
                         'tiktok_finalize.py native --project <工程> --native <候选> --board localize '
                         '--app-id <目标AppID>。') from exc
    return native_sha, path


def _native_files(native):
    return T.Ctx('native', native).files()


@serialized
def finalize_native(native, project=None, board=None, app_id=None, policy=None, manifest=None, legacy=None,
                    options=None, steps=NATIVE_STEPS):
    native = Path(native)
    manifest = manifest or T.load_manifest()
    names = [p.relative_to(native).as_posix() for p in native.rglob('*') if p.is_file()]
    engine = P.engine_of_names(names)
    record_src = read_source_record(project) if project else None
    decision = decide_policy(project=project, native=native, override=policy, legacy=legacy, record=record_src,
                             board=board)
    ctx = T.Ctx('native', native, project=project, board=board, engine=engine, policy=decision['policy'],
                manifest=manifest, app_id=app_id, options=options)
    ctx.preparation_policy_override = bool(policy)
    refused = webp_exception_3x(engine, options)
    from preparation_cache import native_guard, native_lookup, native_store, reused_result, stamp
    if not refused:
        row, path = native_lookup(ctx, steps)
        if row:
            reused = reused_result(row, path)
            reused['removed_dir'] = str(ctx.removed_dir)
            reused['table'] = summary_table(reused)
            return reused
    started, tick = stamp(), time.monotonic()
    try:
        guard = native_guard(ctx, steps)
    except Exception:
        guard = None
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
    native_store(ctx, steps, record, started, time.monotonic() - tick, guard)
    return record


def prepared_native_result(native, project=None, board=None, app_id=None, policy=None, manifest=None, legacy=None,
                           options=None, steps=NATIVE_STEPS):
    """Read-only exact Native preparation proof, or None. Never prepares a raw build.

    Writer, rework planning and preview may share this result only while candidate bytes,
    source dependencies, policy, engine, tools and options match the original execution.
    """
    if not project:
        return None
    tick = time.monotonic()
    from preparation_cache import native_lookup, reused_result
    native = Path(native)
    manifest = manifest or T.load_manifest()
    names = [p.relative_to(native).as_posix() for p in native.rglob('*') if p.is_file()]
    engine = P.engine_of_names(names)
    decision = decide_policy(project=project, native=native, override=policy, legacy=legacy,
                             record=read_source_record(project), board=board)
    if webp_exception_3x(engine, options):
        return None
    ctx = T.Ctx('native', native, project=project, board=board, engine=engine, policy=decision['policy'],
                manifest=manifest, app_id=app_id, options=options)
    ctx.preparation_policy_override = bool(policy)
    row, path = native_lookup(ctx, steps)
    if not row:
        return None
    record = reused_result(row, path)
    record['preparation']['binding_seconds'] = time.monotonic() - tick
    record['removed_dir'] = str(ctx.removed_dir)
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
    import tiktok_rewire      # 生成时预防 P01/P14/P10: rewire_todo, delete_list, kit_copies
    return dict({'project': str(project), 'created': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'categories': out},
                **tiktok_rewire.plan(project))


_inventory_before_audio = inventory   # 生成时预防 R4O6 (补查2 第 12 组): + audio_todo / audio_summary, read only


def inventory(project):  # noqa: F811 - R4O6 wraps the inventory above
    import audio_inventory
    return dict(_inventory_before_audio(project), **audio_inventory.plan(project))


_inventory_before_reward = inventory   # 生成时预防 R4Q4 (补查3 第 4 组): + reward_todo / reward_summary, read only


def inventory(project):  # noqa: F811 - R4Q4 wraps the inventory above
    import reward_inventory
    return dict(_inventory_before_reward(project), **reward_inventory.plan(project))


# ---------------------------------------------------------------- sync (生成时预防 P02: parts from the first build on)
# The standard parts used to arrive only at `source` (just before packaging), so every trial build and self-test before
# it ran on code without them (射击高手 v81 / 小熊拳击 R27 without the touch fix, 指尖麻将 v55 lost a patch on rebuild,
# 拇指弹球 kept an old RewardedService.js). `sync` is the fast part of `source`: hash check, put the kit bytes back.
SYNC_RECORD = Path('.tiktok-kit') / 'sync.json'
SYNC_SOURCE_STEPS = ('kit_sources', 'build_templates', 'startup',   # startup: 生成时预防 R4B (3.x template game.js)
                     'frame_scan')   # frame_scan: 生成时预防 P18-3 (read only, ~1 s)
SYNC_NATIVE_STEPS = ('startup', 'touch', 'storage')      # same order as NATIVE_STEPS: startup decides main.js first
UI_KIT_KEY = 'parts/GameUIKit.js'                         # P05: the shared popup / button part (Cocos 2.4)
UI_KIT_KEYS = {2: UI_KIT_KEY, 3: 'parts-3x/GameUIKit.ts'}   # 生成时预防 R4B (P05 3.x): sync installs GameUIKit.ts too
UI_KIT_DEFAULT_DEST = {2: 'assets/tiktok-platform/GameUIKit.js', 3: 'assets/tiktok-platform/GameUIKit.ts'}
SYNC_SOURCE_STEPS += ('art_static',)   # 生成时预防 R4F1: Sprite aspect warnings before the first build
SYNC_NATIVE_STEPS += ('rewarded',)     # 生成时预防 R4F1: rewarded-guard for a 2.4 package that keeps its own main.js
SYNC_SOURCE_STEPS += ('home_entry_scan',)  # 生成时预防 R4M2 (R4L1 leftover): 3.x hand-placed home entries at every build, read only (<0.1 s)
SYNC_SOURCE_STEPS += ('game_name_scan',)  # 生成时预防 R4O1 (Saul 11-05): game-name text before every build, read only
SYNC_SOURCE_STEPS += ('skin_preview_scan',)  # 生成时预防 R4P4 (R4O2 leftover): skin previews before every build, read only, only with a skin table
SYNC_SOURCE_STEPS += ('slot_overlap_scan',)  # 生成时预防 R4Q1 (补查3 group 1): old label over a whole button picture, two layout owners, read only
SYNC_SOURCE_STEPS += ('reward_order_scan',)  # 生成时预防 R4Q4 (补查3 第 4 组): the game's own rewards paid in animation callbacks / without rollback / x2 rounded two ways, read only
SYNC_SOURCE_STEPS += ('debug_leftover_scan',)  # 生成时预防 R4Q5 (补查3 第 5 组): stats code, active debug nodes, launch-scene splash before every build, read only
SYNC_SOURCE_STEPS += ('ui_kit_scan',)  # 生成时预防 R4J2 (R4F3 leftover): hand-built popups, mask values, dev text before every build, read only
SYNC_END_STEPS = ('save_read_scan', 'plugin3x_scan')   # 生成时预防 R4N6, after sync_run_parts (read only): save reads that lose 0 / false, split ad receipts, level cap vs level files; 3.x plugin imported by path, plugin .meta flags


def _detect_only(ctx, names):
    """Legacy games: what sync WOULD change, nothing written (same rule as `source`: old games keep their own)."""
    out = []
    for name in names:
        try:
            state = _step(name).detect(ctx)
        except Exception as error:  # noqa: BLE001 - a report never refuses
            state = 'error: %r' % (error,)
        out.append({'step': name, 'state': state, 'changed': [], 'blocks': [], 'warnings': [], 'info': ['report only']})
    return out


def sync_ui_kit(ctx):
    """Install / restore the GameUIKit part at its project_path for new games (P05): Cocos 2.4 parts/GameUIKit.js,
    Cocos 3.x parts-3x/GameUIKit.ts (生成时预防 R4B; before it 3.x games copied the .ts by hand). -> step result."""
    r = T.Result('ui_kit')
    key = UI_KIT_KEYS.get(ctx.engine)
    spec = ctx.manifest.files.get(key) if key else None
    if not isinstance(spec, dict):
        r.state = 'n/a'
        return r.as_dict()
    dest = spec.get('project_path') or UI_KIT_DEFAULT_DEST[ctx.engine]
    src = ctx.manifest.kit_dir / key
    kit = src.read_bytes() if src.is_file() else None
    if kit is None or T.sha256(kit) != spec.get('sha256'):
        r.block('K_kit_unusable', 'kit file %s missing or differs from KIT_MANIFEST' % key)
        return r.as_dict()
    have = ctx.read(dest)
    r.state = 'absent' if have is None else ('kit_current' if have == kit else
                                             ('kit_old' if T.sha256(have) in set(spec.get('previous_sha256') or [])
                                              else 'own'))
    if r.state == 'kit_current':
        return r.as_dict()
    if ctx.policy == 'legacy':
        r.info.append('%s %s (legacy game: report only)' % (dest, r.state))
        return r.as_dict()
    if have is not None:
        r.info.append('moved %s to %s' % (dest, ctx.move_away(dest)))
    ctx.write(dest, kit)
    r.change(dest, have, kit, 'GameUIKit %s' % ('added' if have is None else 'restored (%s)' % r.state))
    return r.as_dict()


def sync_run_parts(ctx):
    """生成时预防 R4F1 (#28, P11 / P18; Saul 11-05 agreed): new remake / self-made games get parts/RunSession.js and
    parts/FxPool.js from sync (KIT_MANIFEST files entries with "sync_install"), before they were copied by hand when
    needed. Cocos 2.4: the file at its project_path (require('RunSession')); 3.x: the same file plus a .meta that
    imports it as a plugin (globals TikTokRunSession / TikTokFxPool). English (localize) and legacy games: not
    installed (the English pack keeps the original gameplay code). -> step result."""
    from tiktok_finalize_steps import kit_sources
    r = T.Result('run_parts')
    specs = [(k, s) for k, s in sorted(ctx.manifest.files.items())
             if isinstance(s, dict) and isinstance(s.get('sync_install'), dict)]
    rule = lambda s: s['sync_install']
    if ctx.engine not in (2, 3) or not specs:
        r.state = 'n/a'
        return r.as_dict()
    if ctx.policy != 'new' or ctx.board not in rule(specs[0][1]).get('board', ['remake']):
        r.state = 'n/a'
        r.info.append('%s not installed (%s)' % (' / '.join(Path(s['project_path']).stem for _, s in specs),   # R4M2: names from KIT_MANIFEST (ShopTx too)
                                                 'legacy game' if ctx.policy != 'new' else
                                                 'board %s keeps the original gameplay' % ctx.board))
        return r.as_dict()
    states = []
    for key, spec in specs:
        dest = spec['project_path']
        src = ctx.manifest.kit_dir / key
        kit = src.read_bytes() if src.is_file() else None
        if kit is None or T.sha256(kit) != spec.get('sha256'):
            r.block('K_kit_unusable', 'kit file %s missing or differs from KIT_MANIFEST' % key)
            continue
        name = Path(dest).name
        clash = [p.relative_to(ctx.root).as_posix() for p in (ctx.root / 'assets').rglob(name)
                 if p.is_file() and p.relative_to(ctx.root).as_posix() != dest
                 and not ({'library', 'temp', 'build'} & set(p.relative_to(ctx.root).parts))] \
            if (ctx.root / 'assets').is_dir() else []
        if clash:
            r.warn('K_W_kit_module_duplicate', 'game script %s has the kit module name %s; %s not installed (two '
                   'scripts with one module name stop the Cocos build), rename the game script' % (clash[0], name, key),
                   {'file': clash[0], 'kit_file': dest})
            states.append('own')
            continue
        have = ctx.read(dest)
        state = 'absent' if have is None else ('kit_current' if have == kit else
                                               ('kit_old' if T.sha256(have) in set(spec.get('previous_sha256') or [])
                                                else 'own'))
        states.append(state)
        if state != 'kit_current':
            if have is not None:
                r.info.append('moved %s to %s' % (dest, ctx.move_away(dest)))
            ctx.write(dest, kit)
            r.change(dest, have, kit, '%s %s' % (name, 'added' if have is None else 'restored (%s)' % state))
        if ctx.engine == 3 and rule(spec).get('plugin_3x'):
            old = ctx.read(dest + '.meta')
            new = kit_sources.plugin_meta(old, dest)
            if new != old:
                ctx.write(dest + '.meta', new)
                r.change(dest + '.meta', old, new, 'import as plugin (3.x)')
    r.state = next((s for s in ('own', 'kit_old', 'absent') if s in states), 'kit_current')
    return r.as_dict()


@serialized
def finalize_sync(project, board, native=None, policy=None, manifest=None, legacy=None, write_record=True):
    """`sync`: kit_sources + build_templates (+ ui_kit) on the project, startup + touch + storage on --native.
    New games: kit bytes put back. Legacy games: detect only. -> record (also <project>/.tiktok-kit/sync.json)."""
    started = time.monotonic()
    project = Path(project)
    manifest = manifest or T.load_manifest()
    engine = P.engine_of_project(project)
    decision = decide_policy(project=project, override=policy, legacy=legacy, board=board)
    ctx = T.Ctx('source', project, project=project, board=board, engine=engine, policy=decision['policy'],
                manifest=manifest)
    ctx.preparation_policy_override = bool(policy)
    preparation = _preparation_session(ctx)
    if decision['policy'] == 'legacy':
        results = _detect_only(ctx, SYNC_SOURCE_STEPS)
    else:
        results = _run_steps(ctx, SYNC_SOURCE_STEPS, preparation)
    results.append(preparation.apply('ui_kit', lambda: sync_ui_kit(ctx)) if preparation else sync_ui_kit(ctx))
    results.append(preparation.apply('run_parts', lambda: sync_run_parts(ctx)) if preparation else sync_run_parts(ctx))
    results += _detect_only(ctx, SYNC_END_STEPS) if decision['policy'] == 'legacy' else _run_steps(ctx, SYNC_END_STEPS, preparation)
    if native:
        native = Path(native)
        names = [p.relative_to(native).as_posix() for p in native.rglob('*') if p.is_file()]
        nctx = T.Ctx('native', native, project=project, board=board, engine=P.engine_of_names(names),
                     policy=decision['policy'], manifest=manifest)
        results += _detect_only(nctx, SYNC_NATIVE_STEPS) if decision['policy'] == 'legacy' else \
            _run_steps(nctx, SYNC_NATIVE_STEPS)
    blocks, warnings = _collect(results)
    if engine not in (2, 3):
        blocks.append(T.finding('K_engine_unknown', 'block', 'Cocos version of the project not readable'))
    record = {'kind': 'finalize-sync', 'kit_version': manifest.version, 'policy': decision['policy'],
              'decision': _trim_decision(decision), 'board': board, 'engine': engine, 'native': str(native or ''),
              'steps': results, 'blocks': blocks, 'warnings': warnings,
              'changed': [c['file'] for r in results for c in r['changed']],
              'created': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'seconds': round(time.monotonic() - started, 3)}
    if write_record:
        path = project / SYNC_RECORD
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return record


def _print(record):
    print(json.dumps({k: record[k] for k in ('policy', 'engine', 'blocks', 'warnings') if k in record} |
                     {'decision': record.get('decision', {}).get('reason')}, ensure_ascii=False, indent=1))


def ensure_first_screen(project, board):
    """R4F2 #7 (普查 size_over_limit 39 款): `source` on a project without docs/startup/first-screen.json runs
    first_screen.py first, so the home-page list, the size ledger and the font check exist before any package is
    written. Never stops the source phase; first_screen's problems are printed and the writers check them again."""
    import first_screen
    project = Path(project)
    if project.joinpath(*first_screen.OUT).is_file() or not (project / 'assets').is_dir():
        return None
    try:
        report = first_screen.analyze(project, 'localize' if board == 'localize' else 'new')
        first_screen.write(project, report)
    except Exception as error:  # noqa: BLE001 - a missing list is reported, the source steps still run
        return 'first-screen.json 没生成（%s）：AI 补跑 first_screen.py --project' % repr(error)[:160]
    return 'first-screen.json 已生成：%s，问题 %d 条%s' % (
        '/'.join(first_screen.OUT), len(report['problems']),
        ''.join('\n  ' + p[:200] for p in report['problems'][:5]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('init', 'adopt', 'decide', 'source', 'check-source', 'native', 'inventory', 'sync', 'rewire-ads'):
        p = sub.add_parser(name)
        p.add_argument('--project')
        p.add_argument('--board', choices=('remake', 'localize'))
        p.add_argument('--native')
        p.add_argument('--zip')
        p.add_argument('--app-id')
        p.add_argument('--policy', choices=T.POLICIES, help='tests and calibration only')
        p.add_argument('--keep-webp-exception', metavar='REASON')
        if name == 'init':     # v7.8 H8: record the base game at project start
            p.add_argument('--base', help='底子工程文件夹或源码 ZIP（重塑开工时记下底子的图和声音）')
            p.add_argument('--no-base-why', help='从零做、没有底子时写原因')
    args = ap.parse_args(argv)
    options = {'keep_webp_exception': args.keep_webp_exception} if args.keep_webp_exception else {}
    if args.cmd == 'check-source':
        if not args.project:
            ap.error('--project is required')
        if args.board == 'localize':
            blocks = check_trial_source(args.project, args.board, options=options or None)
        else:
            blocks = check_source_record(args.project, options=options or None)
        _print({'blocks': blocks, 'decision': {'reason': '只读核对已有源码段记录'}})
        return 1 if blocks else 0
    if args.cmd in ('init', 'adopt'):
        if not args.project:
            ap.error('--project is required')
        manifest = T.load_manifest()
        if args.cmd == 'init' and args.base and args.no_base_why:
            ap.error('--base and --no-base-why exclude each other')
        data = P.write_marker(args.project, args.board, manifest.version, reason=args.cmd)
        print(json.dumps(data, ensure_ascii=False))
        if args.cmd == 'init':
            try:
                note = record_base_at_init(args.project, args.board, args.base, args.no_base_why)
            except ValueError as error:
                print('底子没记下：%s' % error, file=sys.stderr)
                return 1
            if note:
                print(note)
        return 0
    if args.cmd == 'rewire-ads':          # 生成时预防 P01/P14: logic in tiktok_rewire.py
        import tiktok_rewire
        if not args.project:
            ap.error('--project is required')
        record = tiktok_rewire.rewire(args.project)
        args.cmd = 'inventory'            # rewrite docs/english/platform-inventory.json from the new code
        print('rewire-ads: %d rewired, %d left in rewire_todo, %d in delete_list' % (
            len(record['rewired']), len(record['rewire_todo']), len(record['delete_list'])))
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
            out = P.decide(uuids=ident['scenes'], assets=ident['assets'], board=args.board,
                           sub_assets=ident.get('sub_assets'))
        else:
            out = decide_policy(project=args.project, native=args.native, override=args.policy, board=args.board)
        print(json.dumps(out, ensure_ascii=False, indent=1, default=sorted))
        return 0
    if not args.board:
        ap.error('--board is required')
    if args.cmd == 'sync':
        if not args.project:
            ap.error('--project is required')
        record = finalize_sync(args.project, args.board, native=args.native, policy=args.policy)
        print('sync: %s, %d file(s) put back, %.2f s%s' % (record['policy'], len(record['changed']), record['seconds'],
                                                           ''.join('\n  ' + c for c in record['changed'])))
        _print(record)
        return 1 if record['blocks'] else 0
    if args.cmd == 'source':
        if not args.project:
            ap.error('--project is required')
        note = ensure_first_screen(args.project, args.board)    # R4F2 #7
        if note:
            print(note)
        record = finalize_source(args.project, args.board, policy=args.policy, app_id=args.app_id, options=options)
    else:
        if not args.native:
            ap.error('--native is required')
        prepared_source = None
        if (args.board == 'localize' and args.project and not args.policy
                and not check_trial_source(args.project, args.board, options=options)):
            prepared_source = prepared_source_identity(args.project)
        record = finalize_native(args.native, args.project, args.board, args.app_id, policy=args.policy,
                                 options=options)
        if prepared_source and not record['blocks']:
            try:
                record['prepared_native_sha256'] = record_prepared_native(args.project, args.native, prepared_source)
            except (OSError, ValueError) as exc:
                record['blocks'].append(T.finding('K_trial_native_prepared', 'block', str(exc)))
        print(table_markdown(record))
    _print(record)
    return 1 if record['blocks'] else 0


if __name__ == '__main__':
    sys.exit(main())
