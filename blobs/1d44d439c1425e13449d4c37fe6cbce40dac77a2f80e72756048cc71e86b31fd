#!/usr/bin/env python3
"""Make the ONE allowed upload package: the TikTok platform package (user 2026-10-23, SquareRush UPLOADFIX).

Every package the user asks for - 打包, 出包, 上传测试包, 检测包, 压缩包, TikTok 平台包 - is this form and nothing else:
the files of the real Cocos Native (mini-game) build at the ZIP root (game.js, game.json, project.config.json), big
resources in a normal subpackage, within the TikTok limits, no outer folder, no Web build, no source, no zip-in-zip,
no Finder junk. The old SquareRush package was rejected: assets/resources stayed in the main package (8,754,975 bytes
> 4,000,000). This writer refuses BEFORE any ZIP is written, then writes to a temp file, re-reads and checks it
(verify_native_zip.py: CRC, safe paths, root entry, App ID, no QA level jump, limits, every file byte-equal to the
Native tree), extracts it again into a folder with spaces and compares, and only then moves it to --out.

  python make_tiktok_zip.py --native <Native build folder> --app-id <App ID> --out <Game_TikTok_test_v3.zip>
         --project <game> --web <web build> --build-tag v3 --review docs/test/known-issue-review.json [--board localize|remake]
         --resource-manifest <current resource manifest.json>
         --startup-contract <current startup contract.json> --loading-recovery-runtime <current recovery runtime.json>
         --ad-regression <project>/qa/ad-regression.json [--report <new report.json>]

For every package the mandatory --review known-issue gate (check_known_issues.py check --stage pre_scan) runs first and a failure stops it
(BUILD-03; use this script as the game's writer for test_writer_refusal.py). Exit codes: 0 ZIP written and verified,
1 refused (no ZIP written), 2 bad input. A passing ZIP is a local structure check only - not platform acceptance.
The report (<out>.report.json; tool make_tiktok_zip, bound to the review's binding) goes into BUILD-04 auto_reports.
v7.5: before any check the stock Cocos 2.4 ByteDance adapter forms are rewritten in the Native folder
(package_gates/adapter_fix.py, listed in the report; an unrecognised adapter is refused). native_problems() lists
EVERY reason at once and runs the shared package gates (package_gates.run: bundle names, analytics domains,
cross-promotion, growth APIs, startup, WebP, static ad code). A written ZIP gets <out>.receipt.json; without it
verify_native_zip.py calls a ZIP unofficial and prepare_delivery.py refuses it.
v7.7 (design D77 1.1, 1.5): the source record <project>/.tiktok-kit/finalize-source.json must match the project and
the kit version (K5; `tiktok_finalize.py source` before the Cocos build), then tiktok_finalize.finalize_native installs
the platform-kit standard parts in the Native folder in place of the v7.5 adapter_fix call (adapter_fix is its first
step) and the package gates run with the finalize record (K4) and its policy (new | legacy). Report and receipt carry
`finalize` (receipt schema 2). --keep-webp-exception REASON is the design 3.6 WebP exception (kit probe installed).
For test_writer_refusal.py give this script a separate --out (its normal case makes one ZIP; existing ZIPs are never
overwritten) and delete that check ZIP afterwards.
v7.8 (总表 B32 b): after the ZIP is written, older packages of the same game in the --out folder (same App ID and the
same game's own files, delivery_folder.py) move into 旧包/ with their receipts, and 最新.txt says which file to upload,
its sha256 and time; the moved files are listed in the output and in the report (delivery_folder). Source ZIPs and
everything else stay. --keep-old-packages (or TIKTOK_KEEP_OLD_PACKAGES=1) leaves the folder as it is: use it, or an
own folder, for the test_writer_refusal check ZIP.
v7.8 (W97, 总表 22.6 D/E): after the written ZIP is re-read and extracted, the rewarded-ad regression and the runtime
regression suites (startup, network, dead_shell, layout_state, button_sweep, ad_entries, popin, frame_rate, ...) run on
that extraction through check_package.writer_regressions - the same gates build_checked_zip runs in check_package.check()
- with --ad-regression <adapter JSON> (or $TIKTOK_AD_REGRESSION_ADAPTER), the finalize policy and --board. A new game
is refused (no adapter, no Ego browser, an incomplete environment and a failed case all refuse); a game on the frozen
legacy list gets warnings and its ZIP. Results go into the report (rewarded_ad_regression, runtime_regression). The
suites take minutes; for test_writer_refusal give the same --ad-regression in the writer command (its normal case).
"""
import argparse
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


def english_image_problems(files, project, board):
    """Board localize only (v7.5, MusicSlice items 6-7): the upload images need the main agent's review record
    <project>/docs/english/image-review.json (audit_image_review_record.py) and every NEW English image (SHA not in
    <project>/docs/english/pre-english-images.json) must be <= 800 KB (audit_new_english_images.py). A missing record or
    list refuses. The 2.5x-display rule needs prefab sizes and is not run here (warning until Saul decides)."""
    if board != 'localize':
        return []
    if project is None:
        return ['English image checks need --project (docs/english/image-review.json and pre-english-images.json)']
    import audit_image_review_record
    import audit_new_english_images
    docs = Path(project) / 'docs' / 'english'
    problems = ['image review: ' + p for p in audit_image_review_record.check(files, docs / 'image-review.json')['problems']]
    pre = docs / 'pre-english-images.json'
    if not pre.is_file():
        problems.append('pre-English image list missing: %s (audit_new_english_images.py --make-list <Chinese original '
                        'project> --out it, before the first English image is made)' % pre)
    else:
        try:
            problems.extend(audit_new_english_images.check(files, pre)['problems'])
        except (OSError, ValueError, TypeError) as error:
            problems.append('pre-English image list unreadable: %s (%s)' % (pre, error))
    return problems


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    """v7.7, both writers (make_tiktok_zip.main and build_checked_zip.build), BEFORE any other package check.

    1. K5: the source record must exist, have no block, match the current project (assets/, build-templates/,
       settings/) and the kit version - checked before the build folder is touched, so a refusal changes nothing.
    2. tiktok_finalize.finalize_native(native, project, board, app_id): installs the standard parts in place (the
       v7.5 adapter_fix rewrite is its first step). The writers never pass --policy: the policy comes from the
       project marker / the frozen legacy list (design section 2).
    v7.8 (U7 补): with step 1 the art receipt <project>/.tiktok-kit/art-receipt.json is CHECKED (art_receipt.check,
       never a new art run): a new remake game whose receipt is missing, not a pass, or whose images changed is
       refused here, before the build folder is touched; legacy / English games and "3.x 未覆盖" get a warning and a
       row in the finalize table (record['art_receipt']).
    -> (record, gate_context, problems). problems non-empty = refuse; record is None when step 1 refused."""
    import tiktok_finalize as F
    options = dict(options or {})
    try:
        kit = F.T.load_manifest()
    except F.T.KitError as error:
        return None, None, ['K_kit_unusable: %s' % error]
    problems = ['%s: %s' % (f['id'], f['message']) for f in F.check_source_record(project, kit, options=options)]
    art = art_receipt_check(project, board)
    if art and art['level'] == 'block':
        problems.append('%s: %s' % (art['gate'], art['message']))
    if problems:
        return None, None, problems
    record = F.finalize_native(native, project, board, app_id, manifest=kit, options=options)
    record['source_record'] = source_record_ref(project)
    add_art_receipt(record, art)
    problems = ['%s: %s' % (b['id'], b['message']) for b in record['blocks']]
    context = {'writer': True, 'finalize_record': record, 'project': project, 'finalize_options': options}
    return record, context, problems


def art_receipt_check(project, board):
    """v7.8 U7（补）, both writers via finalize_for_writer: CHECK the art receipt (art_receipt.py), never re-run the art
    check (Saul 10-24). Board/policy come from the writer and the K5-checked source record. None without --project."""
    if not project:
        return None
    import art_receipt
    return art_receipt.check(project, board)


def add_art_receipt(record, art):
    """Put the receipt result in the finalize record: a warning (legacy / English / 3.x 未覆盖) goes to `warnings`,
    which the ZIP receipt and the report carry, and every result is one row of the delivery table."""
    if not art:
        return
    import art_receipt
    record['art_receipt'] = art_receipt.summary(art)
    item = art_receipt.finding(art)
    if item and item['level'] == 'warn':
        record.setdefault('warnings', []).append(dict(item, step='art_receipt'))
    record.setdefault('table', []).append(art_receipt.table_row(art))


def finalize_report(record):
    """Report form: the receipt summary plus the Chinese parts table for the delivery reply."""
    import tiktok_finalize as F
    out = vnz.finalize_summary(record)
    out['table_markdown'] = F.table_markdown(record)
    if record.get('art_receipt'):
        out['art_receipt'] = record['art_receipt']        # v7.8: which art receipt the writer checked
    return out


def adapter_step(record):
    """The adapter step of a finalize record (v7.5 report key adapter_fix kept for readers of old reports)."""
    for step in (record or {}).get('steps') or []:
        if step.get('step') == 'adapter':
            return step
    return None




CHECK_SCRIPTS = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'


def writer_regressions(folder, adapter, policy, board):
    """v7.8 (W97): check_package.writer_regressions on the files of `folder` (the independent extraction of the ZIP
    about to be published). The import or a crash is a refusal for a new game, never a skip."""
    folder = Path(folder)
    files = {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob('*')) if p.is_file()}
    try:
        if str(CHECK_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(CHECK_SCRIPTS))
        import check_package
    except Exception as error:  # noqa: BLE001
        text = 'rewarded-ad / runtime regression not run: cocos-game-check package-check unusable (%r)' % (error,)
        legacy = policy == 'legacy'
        return {'id': 'writer_regressions', 'policy': policy, 'board': board, 'blocked': not legacy,
                'problems': [] if legacy else [text], 'warnings': [text + ' [legacy game: warning]'] if legacy else [],
                'rewarded_ad_regression': None, 'runtime_regression': None, 'adapter': str(adapter) if adapter else None}
    return check_package.writer_regressions(files, folder, str(adapter) if adapter else None, policy=policy, board=board)


def write_zip(native, files, target):
    from upload_size_gate import enforce
    enforce({rel: (native / rel).stat().st_size for rel in files}, json.loads((native / 'game.json').read_text(encoding='utf-8-sig')))
    from audit_no_ad_simulator import enforce_files
    payload = {rel: (native / rel).read_bytes() for rel in files}
    enforce_files(payload)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in sorted(files):
            zi = zipfile.ZipInfo(rel, FIXED_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, payload[rel])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--native', type=Path, required=True, help='the Cocos Native (mini-game) build output folder')
    ap.add_argument('--app-id', required=True, help='App ID of the target TikTok app (project.config.json appid)')
    ap.add_argument('--out', type=Path, required=True, help='new ZIP path (game, use, version in the name); never overwritten')
    ap.add_argument('--report', type=Path, help='new report path (default: <out>.report.json next to the ZIP)')
    ap.add_argument('--project', type=Path)
    ap.add_argument('--web', type=Path)
    ap.add_argument('--build-tag')
    ap.add_argument('--review', type=Path, help='known-issue review JSON: runs the pre_scan gate first (BUILD-03)')
    ap.add_argument('--coverage', type=Path, help='final source/Web/Native storage ownership evidence; default project/docs/test/runtime-coverage.json')
    ap.add_argument('--board', choices=['localize', 'remake'], help='remake | localize; package gates use it only to choose block vs warning')
    ap.add_argument('--startup-contract', type=Path)
    ap.add_argument('--loading-recovery-runtime', type=Path)
    ap.add_argument('--resource-manifest', type=Path, help='complete current production resource requests; shared mandatory gate')
    ap.add_argument('--keep-webp-exception', metavar='REASON', help='design D77 3.6: keep WebP (still over 30 MB after '
                    'shrinking); finalize installs the kit WebP probe. Same reason as `tiktok_finalize.py source`')
    ap.add_argument('--keep-old-packages', action='store_true', help='v7.8: leave older packages of this game in the '
                    'output folder and do not write 最新.txt (e.g. a writer-refusal test ZIP); default: they go into 旧包/')
    ap.add_argument('--ad-regression', type=Path, help='v7.8: adapter JSON for the rewarded-ad and runtime regressions, '
                    'as build_checked_zip.py (default $TIKTOK_AD_REGRESSION_ADAPTER; usually <project>/qa/'
                    'ad-regression.json). A new game is refused without it; a legacy game gets a warning')
    a = ap.parse_args()
    if not (a.review and a.project and a.web and a.build_tag):
        print('REFUSED, no ZIP written: all upload/test/detection packages require --review, --project, --web and --build-tag; use verify_native_zip.py --structure-only for read-only structure diagnosis', file=sys.stderr)
        return 2
    native = a.native.resolve()
    if not native.is_dir():
        print('make_tiktok_zip: --native %s is not a folder (give the Native build folder, not a ZIP)' % native, file=sys.stderr)
        return 2
    out = a.out.resolve()
    if out.suffix.lower() != '.zip':
        print('make_tiktok_zip: --out must end in .zip', file=sys.stderr)
        return 2
    if out.exists():
        print('make_tiktok_zip: %s already exists - give the new version its own name' % out, file=sys.stderr)
        return 2
    try:
        out.relative_to(native)
        print('make_tiktok_zip: --out must be outside the Native folder', file=sys.stderr)
        return 2
    except ValueError:
        pass
    report_path = (a.report or out.with_name(out.stem + '.report.json')).resolve()
    if report_path.exists():
        print('make_tiktok_zip: report %s already exists' % report_path, file=sys.stderr)
        return 2
    receipt_file = vnz.receipt_path(out)
    if receipt_file.exists() or receipt_file.is_symlink():
        print('make_tiktok_zip: receipt %s already exists' % receipt_file, file=sys.stderr)
        return 2
    # v7.7: the source record must be current (K5), then finalize installs the platform-kit standard parts in the
    # Native folder BEFORE any check (its first step is the v7.5 adapter_fix rewrite; unknown adapter = refused).
    options = {'keep_webp_exception': a.keep_webp_exception} if a.keep_webp_exception else {}
    finalized, gate_context, finalize_problems = finalize_for_writer(native, a.project, a.board, a.app_id, options)
    if finalize_problems:
        print('REFUSED, no ZIP written (tiktok_finalize):\n- ' + '\n- '.join(finalize_problems), file=sys.stderr)
        return 1
    gate_policy = finalized['policy']
    # Cocos bundle URLs can contain ../ even when every ZIP entry is safe.
    try:
        from audit_native_resource_paths import audit as audit_resource_paths
        path_review=json.loads(a.review.read_text(encoding='utf-8'))
        proof=path_review.get('native_resource_paths_runtime')
        if proof:
            proof=Path(proof)
            if not proof.is_absolute(): proof=a.review.parent/proof
        resource_result=audit_resource_paths(native,proof)
        if resource_result['status']!='pass':
            raise ValueError('; '.join(resource_result['errors']))
    except (OSError,ValueError,TypeError) as error:
        print('REFUSED, no ZIP written: native resource path check: '+str(error),file=sys.stderr)
        return 1
    # Reject size and missing/moved local art BEFORE replaying the expensive review.
    # This never substitutes for the full review gate below.
    early_problems, early_sizes, _ = native_problems(native, a.board, gate_policy, gate_context)
    from audit_packed_assets import audit as audit_packed_assets
    asset_result = audit_packed_assets(native)
    if early_problems or not asset_result['passed']:
        print('REFUSED, no ZIP written: ' + '\n'.join(early_problems + asset_result['errors']), file=sys.stderr)
        return 1
    import package_obligations
    try:
        obligation_files = {name: (native/name).read_bytes() for name in early_sizes}
        obligations = package_obligations.verify(obligation_files, native, a.project, a.resource_manifest)
    except (ValueError, OSError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
        print('REFUSED, no ZIP written: ' + str(error), file=sys.stderr)
        return 1
    english_problems = english_image_problems(obligation_files, a.project, a.board)
    if english_problems:
        print('REFUSED, no ZIP written: ' + '\n'.join(english_problems), file=sys.stderr)
        return 1
    from audit_final_package_startup import audit_final_startup
    try:
        audit_final_startup(native, a.project, a.startup_contract, a.loading_recovery_runtime, replay=False)
    except (ValueError, OSError, TypeError, KeyError) as error:
        print('REFUSED, no ZIP written: ' + str(error), file=sys.stderr)
        return 1
    # Native WebP texture selection can fail even when canvas encoding works.
    # Detect actual packed formats instead of trusting a hand-filled 'unchanged' flag.
    if any(p.is_file() and p.suffix.lower() == '.webp' for p in native.rglob('*')):
        try:
            review_data = json.loads(a.review.read_text(encoding='utf-8'))
            refs = review_data['checks']['LOAD-03']['auto_reports']
            codec_ok = False
            for ref in refs:
                report_file = Path(ref['path'])
                if not report_file.is_absolute():
                    report_file = a.review.parent / report_file
                report_data = json.loads(report_file.read_text(encoding='utf-8'))
                if report_data.get('tool') not in ('audit_loading_recovery', 'audit_native_texture_codec'):
                    continue
                runtime_file = Path(report_data['runtime_file'])
                if not runtime_file.is_absolute():
                    runtime_file = report_file.parent / runtime_file
                runtime_data = json.loads(runtime_file.read_text(encoding='utf-8'))
                codec_ok = codec_ok or (runtime_data.get('native_codec_verified') is True and bool(runtime_data.get('codec_evidence_refs')))
            if not codec_ok:
                raise ValueError('Native WebP files require decoder evidence in LOAD-03 runtime')
        except (KeyError, TypeError, ValueError, OSError) as error:
            print('REFUSED, no ZIP written: ' + str(error), file=sys.stderr)
            return 1
    # Execute known production-runtime regressions before accepting any attested
    # coverage table. This is not satisfied by a handwritten pass row.
    probe_cmd = [sys.executable, str(HERE / 'run_reward_storage_probe.py'), '--native', str(native), '--web', str(a.web)]
    probe_run = subprocess.run(probe_cmd, capture_output=True, text=True)
    if probe_run.returncode:
        print('REFUSED, no ZIP written: executable Native/Web reward storage probe failed:\n' +
              (probe_run.stdout + probe_run.stderr)[-2500:], file=sys.stderr)
        return 1
    try:
        storage_probe = json.loads(probe_run.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print('REFUSED, no ZIP written: reward storage probe produced no valid result', file=sys.stderr)
        return 1
    gate = {'ran': False, 'reward_storage_probe': storage_probe}
    if a.review is not None:
        if not (a.project and a.web and a.build_tag):
            print('make_tiktok_zip: --review needs --project, --web and --build-tag for the gate', file=sys.stderr)
            return 2
        cmd = [sys.executable, str(HERE / 'check_known_issues.py'), 'check', '--project', str(a.project), '--native', str(native),
               '--web', str(a.web), '--build-tag', a.build_tag, '--review', str(a.review), '--stage', 'pre_scan']
        if a.board:
            cmd += ['--board', a.board]
        if not a.review.is_file():
            print('REFUSED, no ZIP written: the known-issue review %s is missing (BUILD-03)' % a.review, file=sys.stderr)
            return 1
        p = subprocess.run(cmd, capture_output=True, text=True)
        gate = {'reward_storage_probe': storage_probe, 'ran': True, 'exit': p.returncode, 'command': cmd[1:], 'tail': (p.stdout + p.stderr).strip()[-600:]}
        if p.returncode != 0:
            print('REFUSED, no ZIP written: the known-issue gate failed (exit %d):\n%s' % (p.returncode, gate['tail']), file=sys.stderr)
            return 1
    reviewed = json.loads(a.review.read_text(encoding='utf-8')) if a.review else {}
    import project_qa
    profile = project_qa.review_policy(a, reviewed)
    if profile and profile.get('writer_path'):
        addition = project_qa.invoke(profile, 'legacy_coverage', a, native, reviewed, HERE, field='writer_path')
        if not isinstance(addition, dict):
            print('REFUSED, no ZIP written: project coverage gate failed', file=sys.stderr)
            return 1
        gate.update(addition)
    if not (profile and profile.get('legacy_coverage_override')):
        source_root = a.project / 'assets'
        if not source_root.is_dir():source_root = a.project / 'src'
        coverage = a.coverage or a.project / 'docs/test/runtime-coverage.json'
        coverage_cmd = [sys.executable, str(HERE / 'audit_runtime_coverage.py'), '--source', str(source_root), '--native', str(native), '--web', str(a.web), '--coverage', str(coverage)]
        coverage_result = subprocess.run(coverage_cmd, capture_output=True, text=True)
        if coverage_result.returncode:
            print('REFUSED, no ZIP written: actual runtime persistence coverage failed:\n'+(coverage_result.stdout+coverage_result.stderr)[-2000:], file=sys.stderr)
            return 1
        gate['runtime_coverage_sha256'] = sha(coverage)
    problems, sizes, info = native_problems(native, a.board, gate_policy, gate_context)
    if 'appId' in info and info['appId'] != a.app_id:
        problems.append('App ID: project.config.json appid is %r, the target is %r - rebuild with the right App ID'
                        % (info.get('appId'), a.app_id))
    if problems:
        print('REFUSED, no ZIP written - not the uploadable TikTok platform package:\n- ' + '\n- '.join(problems), file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix='.tiktok-zip-', dir=out.parent))
    try:
        tmp = tmpdir / out.name
        write_zip(native, sizes, tmp)
        result = vnz.verify(tmp, a.app_id)                    # built-in TikTok limits, forbidden entries, CRC, root entry
        tree = {rel: sha(native / rel) for rel in sizes}
        if tree != result['file_sha256']:
            raise ValueError('ZIP and the Native build differ in paths or file bytes')
        check = tmpdir / 'extracted copy'                     # independent extraction into a folder with a space
        with zipfile.ZipFile(tmp) as z:
            z.extractall(check)
        again = {f.relative_to(check).as_posix(): sha(f) for f in check.rglob('*') if f.is_file()}
        if again != result['file_sha256']:
            raise ValueError('independent extraction differs from the ZIP listing')
        # v7.8 (W97, 总表 22.6 D/E): the rewarded-ad and runtime regressions build_checked_zip runs through
        # check_package.check(), here on the extracted bytes of the ZIP about to be published (same adapter, policy
        # and board). A new game is refused; a game on the frozen legacy list gets warnings.
        regressions = writer_regressions(check, a.ad_regression, gate_policy, a.board)
        if regressions['blocked']:
            print('REFUSED, no ZIP written (rewarded-ad / runtime regression, policy %s):\n- %s'
                  % (gate_policy, '\n- '.join(regressions['problems'])), file=sys.stderr)
            return 1
        if hashlib.sha256(tmp.read_bytes()).hexdigest() != result['sha256']:
            raise ValueError('ZIP changed during the runtime regression')
        receipt = vnz.make_receipt('make_tiktok_zip', tmp, result['sha256'], result['file_sha256'],
                                   info['package_gates'], a.board,
                                   {'tool_sha256': sha(Path(__file__))}, finalize=finalized)
        receipt_tmp = tmpdir / receipt_file.name
        receipt_tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        with package_obligations.publication_guard(obligation_files, native, a.project, a.resource_manifest, obligations):
            os.link(receipt_tmp, receipt_file)          # never overwrites; published together with the ZIP
            try:
                os.replace(tmp, out)
            except OSError:
                receipt_file.unlink()
                raise
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as e:
        print('REFUSED, no ZIP written: the written ZIP failed its own check: %s' % e, file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(tmpdir, True)
    result['archive'] = str(out)
    result.update(vnz.receipt_status(out, sha(out), result['file_sha256']))
    report = {'tool': 'make_tiktok_zip', 'status': 'tiktok_upload_zip_ready', 'passed': True, 'failed': 0,
              'package_obligations': obligations,
              'checked': result['files'], 'zip': str(out), 'zip_sha256': sha(out),
              'zip_bytes': out.stat().st_size, 'native': str(native), 'appId': a.app_id, 'gate': gate,
              'sizes': {'main_bytes': info['main'], 'main_limit': vnz.TIKTOK_MAIN, 'total_bytes': info['total'],
                        'total_limit': vnz.TIKTOK_TOTAL, 'normal_subpackages': info['normal'],
                        'independent_subpackages': info['independent'], 'independent_limit': vnz.TIKTOK_INDEPENDENT},
              'files': result['files'], 'checks': ['refused before writing: outer folder, Web build, source, junk, zip-in-zip, '
                                                   'non-ASCII paths, QA level jump, App ID, limits',
                                                   'written ZIP re-read: CRC, safe paths, root entry, App ID, limits',
                                                   'every file byte-equal to the Native tree',
                                                   'independent extraction (folder with a space) equal'],
              'warnings': result.get('warnings', []) + regressions['warnings'], 'left_out_junk': SKIPPED, 'limits_source': vnz.LIMITS_SOURCE,
              'upload': 'upload this ZIP directly - do not unzip, re-zip or wrap it',
              'not_verified': result['not_verified'],
              'board': a.board, 'package_gates': info['package_gates'], 'pre_home_bytes': info['pre_home_bytes'],
              'finalize': finalize_report(finalized), 'adapter_fix': adapter_step(finalized),
              'entry': result['entry'], 'receipt': str(receipt_file),
              # v7.8 (W97): same keys as check_package.check() / build_checked_zip reports
              'rewarded_ad_regression': regressions['rewarded_ad_regression'],
              'runtime_regression': regressions['runtime_regression'],
              'regressions': {k: regressions.get(k) for k in ('policy', 'board', 'adapter', 'problems', 'warnings',
                                                              'seconds')}}
    if isinstance(info.get('pre_home_bytes'), dict) and isinstance(regressions['runtime_regression'], dict):
        info['pre_home_bytes']['measured'] = regressions['runtime_regression'].get('startup_measured')
    if a.review is not None:            # BUILD-04 auto report: bound to this build like every other automatic check
        try:
            report['binding'] = json.loads(a.review.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError):
            pass
    # v7.8 (总表 B32 b): older packages of this game go into 旧包/, the folder keeps this one package and 最新.txt.
    import delivery_folder
    report['delivery_folder'] = delivery_folder.tidy(out, a.app_id, 'make_tiktok_zip', report['zip_sha256'],
                                                     keep=a.keep_old_packages)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'zip', 'zip_sha256', 'zip_bytes', 'appId', 'sizes', 'warnings',
                                             'pre_home_bytes', 'entry')},
                     ensure_ascii=False, indent=2))
    print('finalize (policy %s, kit %s):\n%s' % (finalized['policy'], finalized['kit_version'],
                                                 report['finalize']['table_markdown']))
    runtime = regressions['runtime_regression'] or {}
    print('rewarded-ad / runtime regression (policy %s, %s s): suites %s%s' % (
        gate_policy, regressions.get('seconds'), ', '.join(runtime.get('required') or []) or '-',
        ''.join('\n  warning: %s' % w for w in regressions['warnings'])))
    print('report: %s' % report_path)
    print('\n'.join(delivery_folder.describe(report['delivery_folder'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
