#!/usr/bin/env python3
"""One deterministic TikTok writer, shared by both historical CLI names.

Consume prepared Native bytes and independently bound original evidence. A writer
never finalizes Native, executes storage VM probes or starts a game/browser. Missing
or stale evidence returns to its precise producer. Final ZIP readback, byte identity,
resource/issue guards and per-delivery size/CLI checks retain their existing roles.

Explicit storage producer: writer_proofs.py prepare --project ... --native ... --web ...
Both --app-id and --expected-app-id name the same target parameter.
"""
import argparse
from delivery_continuation import continuing_cli
from regression_scope_gate import scoped_execution
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_native_zip as vnz  # noqa: E402
from audit_upload_startup import audit_invocation  # noqa: E402

FIXED_TIME = (2020, 1, 1, 0, 0, 0)
SKIPPED = []


def native_problems(native, board=None, policy=None, context=None):
    """Refuse before writing anything: EVERY reason the folder that would go into the ZIP is not uploadable.

    Both writers (make_tiktok_zip.py and build_checked_zip.py) call this one function. Sub-checks never stop at
    the first failure: all reasons are returned together (MusicSlice 0f). The shared package gates
    (package_gates.run, board 'remake' | 'localize' | None) run on exactly the files that go into the ZIP; their
    blocks join the problem list and their warnings go to info['package_gates'] for the reports.
    policy / context (v7.7): the writer's finalize policy and record for package_gates.run (kit_parts K4/K5)."""
    out = []
    native = Path(native)
    root = {p.name for p in native.iterdir()}
    rootless = not all(n in root for n in ('game.js', 'game.json', 'project.config.json'))
    if rootless:
        inner = [p for p in native.iterdir() if p.is_dir() and (p / 'game.json').is_file() and (p / 'game.js').is_file()]
        if inner:
            out.append('outer folder: the Native files are inside "%s/" - point --native at that folder so game.js, game.json '
                       'and project.config.json are at the ZIP root' % inner[0].name)
        elif 'index.html' in root:
            out.append('web build: %s has index.html and no game.json - build the TikTok Native mini-game in Cocos (not '
                       'web-mobile) and never rename a Web build as the upload package' % native)
        elif (native / 'assets').is_dir() and any((native / n).exists() for n in ('project.json', 'package.json', 'settings', 'library')):
            out.append('source project: %s is the Cocos project, not its Native build output' % native)
        else:
            out.append('missing root files: game.js, game.json and project.config.json must be at the root of the Native build')
    sizes = {}
    for f in sorted(native.rglob('*')):
        rel = f.relative_to(native).as_posix()
        if f.is_symlink():
            out.append('symlink: %s' % rel)
            continue
        if not f.is_file():
            continue
        why = vnz.forbidden(rel)
        if why == 'Finder/Windows junk file':          # .DS_Store / Thumbs.db / ._x: left out of the ZIP, listed in the report
            if rel not in SKIPPED:
                SKIPPED.append(rel)
            continue
        if why:
            out.append('not allowed: %s - %s' % (rel, why))
            continue
        sizes[rel] = f.stat().st_size
    if rootless:
        return out, sizes, {}   # nothing below can read a package without its root files
    for name in ('game.js', 'game.json', 'project.config.json'):
        if not sizes.get(name):
            out.append('empty root file: %s' % name)
    files = {name: (native / name).read_bytes() for name in sizes}
    from upload_size_gate import enforce_tiktok_host
    try:
        enforce_tiktok_host(files)
    except ValueError as error:
        return out + [str(error)], sizes, {}
    info = {'independent': {}, 'normal': {}}
    try:
        game = json.loads(files.get('game.json', b'{}').decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError) as e:
        out.append('game.json is not valid JSON: %s' % e)
        game = None
    size_error = None
    if game is not None:
        from upload_size_gate import enforce
        try:
            enforce(sizes, game)
        except (ValueError, KeyError, TypeError) as error:
            size_error = str(error)
    from audit_no_ad_simulator import check_entry as player_window
    windows = len(out)
    for name in sorted(files):                     # every Credits/About/simulator hit, not only the first file
        try:
            player_window(name, files[name])
        except ValueError as error:
            out.append(str(error))
    if len(out) > windows:
        # The startup audit runs Node probes on the package JS; never execute a package that still carries an ad
        # simulator / player window (v7.4 boundary). The static package gates below still run and list their reasons.
        out.append('startup audit not run: remove the player window(s) listed above first (the audit executes package JS)')
    else:
        from audit_upload_startup import audit_files
        startup = audit_files(files)
        if not startup['passed']:
            out.extend(startup['errors'])
    subs = game.get('subpackages', []) if isinstance(game, dict) else None
    if game is not None and not isinstance(subs, list):
        out.append('game.json "subpackages" must be an array')
        subs = []
    roots = []
    own_size = []
    for sub in subs or []:
        if not isinstance(sub, dict) or not isinstance(sub.get('root'), str):
            out.append('game.json: each subpackage needs "root"')
            continue
        root_ = sub['root'].strip('/').strip() + '/'
        b = sum(s for n, s in sizes.items() if n.startswith(root_))
        if not any(n.startswith(root_) for n in sizes):
            out.append('subpackage %s is declared in game.json but has no files' % root_)
        roots.append(root_)
        info['independent' if sub.get('independent') is True else 'normal'][root_] = b
    total = sum(sizes.values())
    main = {n: s for n, s in sizes.items() if not any(n.startswith(r) for r in roots)}
    info.update(total=total, main=sum(main.values()))
    if info['main'] > vnz.TIKTOK_MAIN:
        big = sorted(main.items(), key=lambda kv: -kv[1])[:5]
        own_size.append('main package %d bytes > %d (biggest: %s): %s' % (info['main'], vnz.TIKTOK_MAIN,
                                                                         ', '.join('%s %d' % kv for kv in big), vnz.FIX_SIZE))
    if total > vnz.TIKTOK_TOTAL:
        own_size.append('total %d bytes > %d: shrink the art/audio (compress, smaller atlases) - the total limit counts '
                        'every subpackage' % (total, vnz.TIKTOK_TOTAL))
    for r, b in info['independent'].items():
        if b > vnz.TIKTOK_INDEPENDENT:
            own_size.append('independent subpackage %s %d bytes > %d: make it a normal subpackage or split it'
                            % (r, b, vnz.TIKTOK_INDEPENDENT))
    out.extend(own_size)
    if size_error and not own_size:                # same limits; keep the shared gate's reason when ours found nothing
        out.append(size_error)
    try:
        app = json.loads(files.get('project.config.json', b'{}').decode('utf-8-sig')).get('appid')
    except (ValueError, AttributeError, UnicodeDecodeError):
        app = None
    info['appId'] = app
    for rel in sizes:
        if rel.endswith(('.js', '.json')) and vnz.QA_MARKER in files[rel]:
            out.append('test-only level jump %s is still in %s: build the upload package without it' % (vnz.QA_MARKER.decode(), rel))
    import package_gates
    gates = package_gates.run(files, native, board, policy=policy, context=context)
    info['package_gates'] = package_gates.summary(gates)
    info['pre_home_bytes'] = pre_home(files, native, board)
    out.extend(package_gates.messages(gates['blocks']))
    return out, sizes, info


def pre_home(files, root=None, board=None):
    """Bytes downloaded before the home page (main + subpackages the startup loads), printed in every report
    (MusicSlice 6.3; > 15 MB is the W8_prehome_bytes warning, no hard limit yet)."""
    import package_gates
    from package_gates import startup
    try:
        return startup.pre_home_bytes(package_gates.PackageView(files, root, board))
    except Exception as error:  # noqa: BLE001 - reporting only; the gates themselves already ran
        return {'error': repr(error)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


PRE_ENGLISH_LIST = Path('docs/english/pre-english-images.json')


def english_new_image_problems(files, project, board):
    """Board localize only (11.17.14): byte limits of images made during localisation, both writers.

    Reads only the bytes about to be zipped and the pre-English list; it never re-runs art checks, image reviews or
    recordings, so a small fix does not trigger a full re-test. Original Chinese images (SHA in the list) are never
    judged. Restores the v7.5 MusicSlice rule that 11.17.13 dropped together with the aggregate art receipt.
    """
    if board is None and project:
        from tiktok_finalize import read_source_record
        board = (read_source_record(project) or {}).get('board')
    if board != 'localize':
        return []
    if not project:
        return ['english_new_images: 英化写包需要 --project，用来读取 %s' % PRE_ENGLISH_LIST]
    pre = Path(project) / PRE_ENGLISH_LIST
    if not pre.is_file():
        return ['english_new_images: 缺少中文原版图片清单 %s（开工时用 audit_new_english_images.py --make-list '
                '<中文原版工程> --out 这个文件生成；只需一次）' % pre]
    import audit_new_english_images
    try:
        return ['english_new_images: ' + p for p in audit_new_english_images.check(files, pre)['problems']]
    except (OSError, ValueError, TypeError) as error:
        return ['english_new_images: 中文原版图片清单读不了：%s（%s）' % (pre, error)]


def source_record_ref(project):
    """Which source record the writer accepted (path, file sha256, recorded source digest), for report/receipt."""
    import tiktok_finalize as F
    if not project:
        return None
    path = Path(project) / F.SOURCE_RECORD
    if not path.is_file():
        return {'path': str(path), 'present': False}
    record = F.read_source_record(project) or {}
    return {'path': str(path), 'present': True, 'sha256': sha(path), 'source_sha256': record.get('source_sha256'),
            'kit_version': record.get('kit_version'), 'policy': record.get('policy'), 'created': record.get('created')}


def finalize_for_writer(native, project, board, app_id, options=None):
    """Read-only source/production guards and exact prepared Native evidence before writing.

    1. K5: the source record must exist, have no block, match the current project (assets/, build-templates/,
       settings/) and the kit version - checked before the build folder is touched, so a refusal changes nothing.
    2. tiktok_finalize.prepared_native_result: consumes the original standard-parts preparation (the
       adapter rewrite remains at its explicit preparation node). The policy comes from the
       project marker / the frozen legacy list (design section 2).
    -> (record, gate_context, problems). problems non-empty = refuse; record is None when step 1 refused."""
    import tiktok_finalize as F
    from ad_standard_scope import requirement
    ad_policy = F.decide_policy(project=project, native=native, board=board).get('policy')
    if requirement(project, ad_policy)['required'] and (not project or not (Path(project) / 'docs/adboost/ad_nodes.json').is_file()):
        return None, None, ['AD6_manifest_required: 六标准广告制作尚未登记；先按同包ad-boost盘点并补齐六类及新增UI，不写ZIP。']
    options = dict(options or {})
    try:
        kit = F.T.load_manifest()
    except F.T.KitError as error:
        return None, None, ['K_kit_unusable: %s' % error]
    source_board = (F.read_source_record(project) or {}).get('board') if project else None
    board_mismatch = bool(board and source_board and board != source_board)
    if project and not (board or source_board):
        from feature_policy import board_of
        board = board_of(project)[0]
    board = board or source_board
    localize = board == 'localize'
    source = F.check_source_record(project, kit, options)
    problems = ['%s: %s' % (f['id'], f['message']) for f in source]
    if board_mismatch:
        problems.append('K5_source_finalized: writer board differs from the source record')
    if problems:
        return None, None, problems
    base_audio_warning = None
    if board == 'remake':
        # H8 originally shared the aggregate art gate. Check only the original-audio rule here.
        from art_receipt import GATE_BASE_AUDIO, original_audio_message, strictness
        from art_records import base_audio_now
        try:
            same_audio = base_audio_now(project, board)
        except Exception:  # An unreadable provenance record is handled during production.
            same_audio = []
        if same_audio:
            strict, _, _ = strictness(project, board)
            message = original_audio_message(same_audio)
            if strict:
                return None, None, ['%s: %s' % (GATE_BASE_AUDIO, message)]
            base_audio_warning = F.T.finding(GATE_BASE_AUDIO, 'warn', message)
    if localize:
        options['prepared_png_only'] = True
    record = F.prepared_native_result(native, project, board, app_id, manifest=kit, options=options)
    if record is None:
        return None, None, ['K_native_preparation_required: 当前 Native 缺少有效准备记录；回到 tiktok_finalize.py native 准备节点，仅补受影响项，写包不会改动构建。']
    record['source_record'] = source_record_ref(project)
    if base_audio_warning:
        record['warnings'].append(base_audio_warning)
    problems = ['%s: %s' % (b['id'], b['message']) for b in record['blocks']]
    context = {'writer': True, 'finalize_record': record, 'project': project, 'finalize_options': options}
    return record, context, problems


def finalize_report(record):
    """Report form: the receipt summary plus the Chinese parts table for the delivery reply."""
    import tiktok_finalize as F
    out = vnz.finalize_summary(record)
    out['table_markdown'] = F.table_markdown(record)
    return out


def adapter_step(record):
    """The adapter step of a finalize record (v7.5 report key adapter_fix kept for readers of old reports)."""
    for step in (record or {}).get('steps') or []:
        if step.get('step') == 'adapter':
            return step
    return None




CHECK_SCRIPTS = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
if str(CHECK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CHECK_SCRIPTS))


def writer_regressions(folder, adapter, policy, board, rework_of=None, *,
                       project=None, expected_scope_sha256=None):
    """Read complete original ledger results; an empty selection cannot launch CI."""
    import time
    import check_package as checks
    import ad_incremental
    import runtime_incremental
    import ad_regression
    import runtime_regression
    from regression_scope_gate import needs_ad_suite
    started = time.monotonic()
    folder = Path(folder)
    files = checks.native_files(folder)
    out = {'id': 'writer_regressions', 'policy': policy, 'board': board,
           'adapter': str(adapter) if adapter else None, 'blocked': True,
           'problems': [], 'warnings': [], 'rewarded_ad_regression': None,
           'runtime_regression': None}
    try:
        project, adapter, board, policy = checks.regression_context(files, folder, adapter, board, policy, project)
        scope = checks.verify_regression_scope(files, folder, adapter, board, policy, rework_of,
            project=project, expected_scope_sha256=expected_scope_sha256, operation='writer')
        plans = []
        needs_ads = needs_ad_suite(files, adapter, ad_regression, runtime_regression)
        if needs_ads:
            checks.input_gate('rewarded_ad_regression', adapter)
            plans.extend(ad_incremental.run(ad_regression, folder, adapter, plan_only=True))
        if 'game.js' in files:
            checks.input_gate('runtime_regression', adapter)
            plans.extend(runtime_incremental.run(runtime_regression, folder, adapter,
                                                policy=policy, board=board, plan_only=True))
        missing = [p['check_id'] + ': ' + p['why'] for p in plans if p['action'] != 'reuse']
        if missing:
            raise ValueError('writer only consumes existing evidence; return to affected checks: ' + '; '.join(missing))
        # These APIs append only reusable units when selection is empty. They still
        # use the actual production judge and report missing coverage as incomplete.
        ad = (ad_incremental.run(ad_regression, folder, adapter, cases=[]) if needs_ads else
              {'id': 'rewarded_ad_regression', 'status': 'not_applicable',
               'reason': 'no applicable automated rewarded-ad request; manual revive coverage stays at its playtest node'})
        runtime = (runtime_incremental.run(runtime_regression, folder, adapter, suites=[], policy=policy, board=board)
                   if 'game.js' in files else {'id': 'runtime_regression', 'status': 'not_applicable', 'reason': 'no game.js'})
        problem = checks.regression_coverage_problem(ad, runtime, files, adapter, policy)
        if problem:
            raise ValueError(problem)
        if checks.regression_record(ad, runtime) is None:
            raise ValueError('complete passing original regression records are missing')
        out.update(blocked=False, policy=policy, board=board, regression_scope=scope,
                   rewarded_ad_regression=ad, runtime_regression=runtime,
                   warnings=list(runtime.get('warnings') or []))
        if scope.get('baseline'):
            out['rework'] = {'reuse': True, 'old': scope['baseline'],
                             'why': 'canonical writer consumed original independent records',
                             'rerun': [], 'reused': [p['check_id'] for p in plans]}
    except (ValueError, OSError, TypeError, KeyError) as error:
        out['problems'].append(str(error))
    out['seconds'] = round(time.monotonic() - started, 6)
    return out


def resolve_rework(value, out):
    """简化.11.15 (出包后返工): --rework-of -> (the last passed package or None, note). A missing predecessor
    is blocked by scope preflight (rework_scope.resolve; auto = the 最新.txt of the new ZIP folder)."""
    try:
        if str(CHECK_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(CHECK_SCRIPTS))
        import rework_scope
        return rework_scope.resolve(value, out)
    except Exception as error:  # noqa: BLE001
        return None, 'scope_required: rework baseline unavailable (%r)' % (error,)


def rework_record(project, plan):
    """简化.11.15 (出包后返工): after the ZIP is published, the plan this writer used, the pages that use the change and
    the AI's hand checks go to <project>/docs/checks/rework-<time>.json (rework_scope.record_for_writer), so the next AI
    knows what was checked and what changed. Only when an earlier package was compared; never raises."""
    if not isinstance(plan, dict) or not plan.get('old'):
        return None
    try:
        if str(CHECK_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(CHECK_SCRIPTS))
        import rework_scope
        return rework_scope.record_for_writer(project, plan)
    except Exception as error:  # noqa: BLE001 - the ZIP is already published
        return {'error': repr(error)}


def rework_lines(plan, record=None):
    try:
        import rework_scope
        return rework_scope.writer_lines(plan, record)
    except Exception:  # noqa: BLE001
        return []


def regression_receipt(regressions):
    """v7.9 (出包检查提速 S1, 总表 19 ①): the receipt's record of the two regressions this writer passed
    (check_package.regression_record), so prepare_delivery reuses them for the same bytes instead of running them
    again. None when there is nothing to reuse; delivery refuses instead of starting a browser."""
    try:
        import check_package
        return check_package.regression_record(regressions.get('rewarded_ad_regression'),
                                               regressions.get('runtime_regression'))
    except Exception:  # noqa: BLE001 - missing evidence refuses publication
        return None


def write_zip(native, files, target, *, reviewed_files=None):
    from upload_size_gate import enforce, enforce_tiktok_host
    from audit_no_ad_simulator import enforce_files
    payload = reviewed_files if reviewed_files is not None else {rel: (native / rel).read_bytes() for rel in files}
    if set(payload) != set(files):
        raise ValueError('Native file list changed after review')
    enforce({rel: len(data) for rel, data in payload.items()}, json.loads(payload['game.json'].decode('utf-8-sig')))
    enforce_tiktok_host(payload)
    enforce_files(payload)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in sorted(payload):
            zi = zipfile.ZipInfo(rel, FIXED_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, payload[rel])


@audit_invocation()
@scoped_execution
def write_package(native, app_id, out, report=None, interaction_audio_trace=None, resource_manifest=None,
                  project=None, startup_contract=None, loading_recovery_runtime=None, ad_regression=None,
                  board=None, keep_webp_exception=None, keep_old_packages=False, rework_of='auto', *,
                  web=None, build_tag=None, review=None, coverage=None, writer_evidence=None,
                  native_resource_paths_runtime=None, webp_codec_reports=None):
    """The sole official writer. Consume prepared bytes and original passing evidence.

    Both historical CLIs and build_checked_zip.build call this function. Missing
    evidence returns to its producer; this function never finalizes, launches a
    browser, or replays gameplay/storage suites. Static file/host VM guards remain.
    """
    import time
    from types import SimpleNamespace
    import writer_proofs
    import package_obligations
    import check_package
    from audit_packed_assets import audit as packed_assets
    from audit_native_resource_paths import audit as resource_paths
    from audit_final_storage import audit_final_storage
    from audit_final_package_startup import audit_final_startup
    from known_issue_checkpoints import consume_for_writer

    started = time.monotonic()
    native, out = Path(native).resolve(), Path(out).resolve()
    project = Path(project).resolve() if project else None
    if not native.is_dir():
        raise ValueError('Native input directory missing')
    if not isinstance(app_id, str) or not app_id.strip():
        raise ValueError('a nonempty target App ID is required')
    if out.suffix.lower() != '.zip':
        raise ValueError('upload output must end in .zip')
    if out.exists() or out.is_symlink() or out.is_relative_to(native):
        raise ValueError('output must be new and outside Native input')
    report_path = Path(report).resolve() if report else out.with_name(out.stem + '.report.json')
    if report_path.exists() or report_path.is_symlink() or report_path == out or report_path.is_relative_to(native):
        raise ValueError('report must be new, outside Native, and distinct from ZIP')
    receipt_file = vnz.receipt_path(out)
    if receipt_file.exists() or receipt_file.is_symlink() or report_path == receipt_file:
        raise ValueError('receipt already exists or conflicts with report')
    if not project or not project.is_dir():
        raise ValueError('actual --project is required')
    if not resource_manifest:
        raise ValueError('runtime resource manifest required before writing ZIP')
    manifest_path = Path(resource_manifest).resolve()
    review = Path(review).resolve() if review else None
    default_review = project / 'docs/test/known-issue-review.json'
    if review is None and default_review.is_file():
        review = default_review
    reviewed = json.loads(review.read_bytes()) if review else {}
    if not isinstance(reviewed, dict):
        raise ValueError('existing known-issue review must be an object')
    web = writer_proofs.resolve_web(project, native, web, writer_evidence, startup_contract)
    if not web.is_dir():
        raise ValueError('actual current Web directory missing')
    if review is None:
        review = writer_proofs.resolve_registered_review(project, native, web)
        reviewed = json.loads(review.read_bytes()) if review else {}
    a = SimpleNamespace(native=native, app_id=app_id, out=out, report=report_path, project=project,
                        web=web, build_tag=build_tag, review=review, coverage=coverage, board=board,
                        startup_contract=startup_contract, loading_recovery_runtime=loading_recovery_runtime,
                        resource_manifest=manifest_path, ad_regression=ad_regression,
                        keep_webp_exception=keep_webp_exception, keep_old_packages=keep_old_packages,
                        rework_of=rework_of)
    options = {'keep_webp_exception': keep_webp_exception} if keep_webp_exception else {}
    finalized, gate_context, problems = finalize_for_writer(native, project, board, app_id, options)
    if problems:
        raise ValueError('tiktok_finalize: ' + '; '.join(problems))
    board, policy = finalized.get('board') or board, finalized['policy']
    a.board = board
    problems, sizes, info = native_problems(native, board, policy, gate_context)
    if info.get('appId') != app_id:
        problems.append('Root App ID does not match the requested target')
    assets = packed_assets(native)
    problems.extend(assets.get('errors') or [] if not assets['passed'] else [])
    if problems:
        raise ValueError('; '.join(problems))
    files = {name: (native / name).read_bytes() for name in sizes}
    obligations = package_obligations.verify(files, native, project, manifest_path)
    problems = english_new_image_problems(files, project, board)
    if problems:
        raise ValueError('; '.join(problems))
    proof = native_resource_paths_runtime or reviewed.get('native_resource_paths_runtime')
    if proof:
        proof = Path(proof)
        if not proof.is_absolute():
            proof = (review.parent if review else project) / proof
    path_result = resource_paths(native, proof)
    if path_result['status'] != 'pass':
        raise ValueError('native resource path check: ' + '; '.join(path_result['errors']))
    technical_refs = {str(Path(proof).resolve()): sha(proof)} if proof else {}
    if any(name.lower().endswith('.webp') for name in files):
        from check_known_issues import tree_sha, snapshot
        current_codec_inputs = {'source_sha256': snapshot(project)[2],
                                'native_tree_sha256': tree_sha(native), 'web_tree_sha256': tree_sha(web)}
        refs = list(webp_codec_reports or [])
        refs.extend(reviewed.get('checks', {}).get('LOAD-03', {}).get('auto_reports', []))
        codec_ok = False
        for ref in refs:
            value = ref.get('path') if isinstance(ref, dict) else ref
            report_file = Path(value)
            if not report_file.is_absolute():
                report_file = (review.parent if review else project) / report_file
            report_data = json.loads(report_file.read_bytes())
            if isinstance(ref, dict) and ref.get('sha256') and sha(report_file) != ref['sha256']:
                raise ValueError('WebP decoder report reference changed')
            if report_data.get('tool') not in ('audit_loading_recovery', 'audit_native_texture_codec'):
                continue
            if (report_data.get('passed') is not True or report_data.get('failed') != 0
                    or type(report_data.get('checked')) is not int or report_data['checked'] < 1
                    or any((report_data.get('binding') or {}).get(key) != value for key, value in current_codec_inputs.items())):
                raise ValueError('WebP decoder report is failed or stale; return to its affected producer')
            runtime_file = Path(report_data['runtime_file'])
            if not runtime_file.is_absolute():
                runtime_file = report_file.parent / runtime_file
            runtime_data = json.loads(runtime_file.read_bytes())
            if any((runtime_data.get('binding') or {}).get(key) != value for key, value in current_codec_inputs.items()):
                raise ValueError('WebP decoder runtime evidence has stale artifact inputs')
            if report_data.get('tool') == 'audit_loading_recovery':
                from audit_loading_recovery import validate
                errors = validate(runtime_data, runtime_data['binding'], runtime_file.parent)
                if errors:
                    raise ValueError('WebP decoder runtime evidence invalid: ' + '; '.join(errors))
            refs = runtime_data.get('raw_evidence', [])
            indexes = runtime_data.get('codec_evidence_refs', [])
            if not indexes or not all(type(i) is int and 0 <= i < len(refs) for i in indexes):
                raise ValueError('WebP decoder raw evidence references missing')
            for i in indexes:
                raw = (runtime_file.parent / refs[i]['path']).resolve()
                if sha(raw) != refs[i].get('sha256'):
                    raise ValueError('WebP decoder raw evidence missing or changed')
                technical_refs[str(raw)] = sha(raw)
            technical_refs.update({str(report_file.resolve()): sha(report_file), str(runtime_file.resolve()): sha(runtime_file)})
            codec_ok = codec_ok or (runtime_data.get('native_codec_verified') is True and bool(runtime_data.get('codec_evidence_refs')))
        if not codec_ok:
            raise ValueError('Native WebP files require current decoder evidence; return to LOAD-03 producer')
    observed = None
    if interaction_audio_trace:
        from audit_interaction_audio import audit
        observed = audit(interaction_audio_trace, native)
        if not observed['passed']:
            raise ValueError('interaction/audio: ' + '; '.join(observed['errors']))
    import project_qa
    profile = project_qa.review_policy(a, reviewed)
    from cocos1_compat import engine_file as creator1_engine
    creator1 = creator1_engine(files) is not None
    if creator1:
        from creator1_compatibility_contract import writer_evidence as creator1_evidence
        producer_proofs, creator1_scope, creator1_record, creator1_runtime, creator1_ads = creator1_evidence(project, native, web)
    else:
        producer_proofs = writer_proofs.consume(project, native, web, coverage, writer_evidence,
            require_coverage=not (profile and profile.get('legacy_coverage_override')))
    producer_proofs['refs'].update(technical_refs)
    qa_proof = writer_proofs.consume_project_qa(a, reviewed, profile, writer_evidence) if profile else None
    # Existing summaries can show unmapped duties; they cannot manufacture a pass.
    checkpoints = consume_for_writer(project, native, web, build_tag=build_tag, review=review, board=board)
    storage = audit_final_storage(native, project, startup_contract, review=review)
    summary = vnz.finalize_summary(finalized) if 'decision' in finalized else finalized
    problem = vnz.finalize_problem(summary, {name: hashlib.sha256(data).hexdigest() for name, data in files.items()})
    if problem:
        raise ValueError('finalize record does not match the ZIP: ' + problem)
    previous, rework_note = resolve_rework(rework_of, out)
    if creator1:
        scope, regression_record = creator1_scope, creator1_record
        startup = dict(passed=True, native_tree_sha256=creator1_scope['native_tree'],
                       runtime_execution='existing_evidence_only_no_game_execution', record=creator1_record['compatibility'],
                       boundary=creator1_runtime['boundary'])
        regressions = dict(blocked=False, rewarded_ad_regression=creator1_ads, runtime_regression=creator1_runtime,
                           rework=dict(reuse=False, scope='creator1_registered_integration_repair',
                                       baseline='original received source/native archives; no prior writer approval inferred',
                                       record=creator1_record['compatibility']))
    else:
        scope = check_package.verify_regression_scope(files, native, ad_regression, board, policy, previous,
                                                      project=project, operation='writer')
        startup = audit_final_startup(native, project, startup_contract, loading_recovery_runtime, reuse_only=True)
        regressions = writer_regressions(native, ad_regression, policy, board, previous, project=project,
                                         expected_scope_sha256=(scope or {}).get('plan_sha256'))
        if regressions['blocked']:
            raise ValueError('; '.join(regressions['problems']))
        regression_record = regression_receipt(regressions)
        if regression_record is None:
            raise ValueError('writer did not find complete passing regression evidence')
    static_seconds = time.monotonic() - started
    out.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.tiktok-zip-', dir=out.parent) as folder:
        tmpdir = Path(folder)
        temporary = tmpdir / out.name
        write_zip(native, sizes, temporary, reviewed_files=files)
        result = vnz.verify(temporary, app_id)
        expected = {rel: hashlib.sha256(data).hexdigest() for rel, data in files.items()}
        if result['file_sha256'] != expected:
            raise ValueError('ZIP differs from the exact reviewed Native bytes')
        extracted = tmpdir / 'extracted copy'
        with zipfile.ZipFile(temporary) as archive:
            archive.extractall(extracted)
        if {p.relative_to(extracted).as_posix(): sha(p) for p in extracted.rglob('*') if p.is_file()} != expected:
            raise ValueError('independent extraction differs from the ZIP listing')
        receipt = vnz.make_receipt('make_tiktok_zip', temporary, result['sha256'], result['file_sha256'],
            info['package_gates'], board, {'tool_sha256': sha(Path(__file__)), 'canonical_backend': 'make_tiktok_zip.write_package',
            'regression_scope': scope, 'regressions': regression_record,
            'writer_producer_proofs': producer_proofs}, finalize=finalized)
        result.update(tool='make_tiktok_zip', canonical_backend='make_tiktok_zip.write_package',
            status='tiktok_upload_zip_ready', passed=True, failed=0, archive=str(out), zip=str(out),
            sha256=result['sha256'], zip_sha256=result['sha256'], zip_bytes=temporary.stat().st_size,
            native=str(native), app_id=app_id, appId=app_id, board=board, expected_tree_exact=True,
            entry='official', entry_label=vnz.ENTRY_LABEL['official'],
            entry_reason='matching canonical writer receipt', receipt=str(receipt_file),
            package_gates=info['package_gates'], package_obligations=obligations,
            packed_resource_check=assets, native_storage_contract=storage, final_startup_runtime=startup,
            native_resource_paths=path_result, writer_producer_proofs=producer_proofs,
            project_qa_proof=qa_proof, known_issue_coverage=checkpoints,
            finalize=finalize_report(finalized), adapter_fix=adapter_step(finalized),
            pre_home_bytes=info.get('pre_home_bytes'), native_pre_home_bytes=info.get('pre_home_bytes'),
            rewarded_ad_regression=regressions['rewarded_ad_regression'], runtime_regression=regressions['runtime_regression'],
            regression_scope=scope, rework=regressions.get('rework') or {'reuse': False, 'why': rework_note},
            runtime_execution='existing_evidence_only_no_game_execution',
            sizes={'main_bytes': info['main'], 'main_limit': vnz.TIKTOK_MAIN, 'total_bytes': info['total'],
                   'total_limit': vnz.TIKTOK_TOTAL, 'normal_subpackages': info['normal'],
                   'independent_subpackages': info['independent'], 'independent_limit': vnz.TIKTOK_INDEPENDENT},
            check_timings={'static_preflight_seconds': round(static_seconds, 6),
                           'total_seconds': round(time.monotonic() - started, 6)})
        if observed is not None:
            result['interaction_audio_check'] = observed
        result['tool_identity'] = check_package.tools_in_use()
        if reviewed.get('binding'):
            result['binding'] = reviewed['binding']
        receipt_tmp = tmpdir / 'receipt.json'
        receipt_tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        # All validations have finished. Publish new files under the same guards;
        # never overwrite a concurrently created ZIP, receipt or report.
        with package_obligations.publication_guard(files, native, project, manifest_path, obligations):
            writer_proofs.unchanged(producer_proofs)
            if qa_proof:
                writer_proofs.unchanged(qa_proof)
            published = []
            try:
                os.link(receipt_tmp, receipt_file)
                published.append(receipt_file)
                os.link(temporary, out)
                published.append(out)
                with report_path.open('x', encoding='utf-8') as stream:
                    json.dump(result, stream, ensure_ascii=False, indent=2)
                    stream.write('\n')
                published.append(report_path)
            except BaseException:
                for path in reversed(published):
                    path.unlink(missing_ok=True)
                raise
    import delivery_folder
    result['delivery_folder'] = delivery_folder.tidy(out, app_id, 'make_tiktok_zip', result['sha256'], keep=keep_old_packages)
    record = rework_record(project, result.get('rework'))
    if record:
        result['rework_record'] = record
    # Post-publication housekeeping is report metadata, never another validation.
    report_tool_identity(result, project, out)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def report_tool_identity(result, project, out):
    """Retain modified-tool diagnostics once in the canonical writer only."""
    import check_package
    identity = result.get('tool_identity')
    if not isinstance(identity, dict) or identity.get('status') != 'modified':
        return
    result['modified_tools'] = identity.get('summary') or []
    warnings = result.setdefault('warnings', [])
    for item in result['modified_tools']:
        warning = '改过的工具: ' + item
        if warning not in warnings:
            warnings.append(warning)
    draft = check_package.feedback_draft(identity, Path(project).name if project else Path(out).stem)
    if draft:
        result['tool_feedback_draft'] = draft


def add_writer_arguments(parser):
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--app-id', '--expected-app-id', dest='app_id', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--web', type=Path, help='exact current Web artifact, or its existing producer record')
    parser.add_argument('--build-tag')
    parser.add_argument('--review', type=Path, help='existing known-issue evidence; no handfilled table is required')
    parser.add_argument('--coverage', type=Path)
    parser.add_argument('--writer-evidence', type=Path, help='writer_proofs.py prepare manifest; read-only consumption')
    parser.add_argument('--native-resource-paths-runtime', type=Path)
    parser.add_argument('--webp-codec-report', dest='webp_codec_reports', action='append', type=Path)
    parser.add_argument('--interaction-audio-trace', type=Path)
    parser.add_argument('--resource-manifest', type=Path, required=True)
    parser.add_argument('--startup-contract', type=Path)
    parser.add_argument('--loading-recovery-runtime', type=Path)
    parser.add_argument('--ad-regression', type=Path)
    parser.add_argument('--board', choices=['localize', 'remake'])
    parser.add_argument('--keep-webp-exception', metavar='REASON')
    parser.add_argument('--keep-old-packages', action='store_true')
    parser.add_argument('--rework-of', default='auto')
    return parser


@continuing_cli('writer')
def main(argv=None):
    parser = add_writer_arguments(argparse.ArgumentParser(description='One official TikTok writer; consume prepared bytes and existing evidence.'))
    args = parser.parse_args(argv)
    result = write_package(**vars(args))
    print(json.dumps({key: result.get(key) for key in ('archive', 'sha256', 'archive_bytes', 'main_bytes',
        'uncompressed_total_bytes', 'expected_tree_exact', 'check_timings', 'pre_home_bytes', 'entry', 'receipt', 'canonical_backend')}, ensure_ascii=False))
    print('finalize (policy %s):\n%s' % (result['finalize']['policy'], result['finalize']['table_markdown']))
    if result.get('rework', {}).get('scope') == 'creator1_registered_integration_repair':
        print('Creator1：按登记的原始包逐文件比较，兼容修复的必需节点已通过；不声明全玩法或真机通过。')
    elif result.get('rework'):
        print('\n'.join(rework_lines(result['rework'], result.get('rework_record'))))
    import delivery_folder
    print('\n'.join(delivery_folder.describe(result['delivery_folder'])))
    if result.get('modified_tools'):
        print('改过的工具：%s%s' % ('; '.join(result['modified_tools']),
              '（反馈草稿：%s）' % result['tool_feedback_draft'] if result.get('tool_feedback_draft') else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
