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
         [--report <new report.json>]

For every package the mandatory --review known-issue gate (check_known_issues.py check --stage pre_scan) runs first and a failure stops it
(BUILD-03; use this script as the game's writer for test_writer_refusal.py). Exit codes: 0 ZIP written and verified,
1 refused (no ZIP written), 2 bad input. A passing ZIP is a local structure check only - not platform acceptance.
The report (<out>.report.json; tool make_tiktok_zip, bound to the review's binding) goes into BUILD-04 auto_reports.
For test_writer_refusal.py give this script a separate --out (its normal case makes one ZIP; existing ZIPs are never
overwritten) and delete that check ZIP afterwards.
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


def native_problems(native):
    """Refuse before writing anything: what is wrong with the folder that would go into the ZIP."""
    out = []
    root = {p.name for p in native.iterdir()}
    if not all(n in root for n in ('game.js', 'game.json', 'project.config.json')):
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
            SKIPPED.append(rel)
            continue
        if why:
            out.append('not allowed: %s - %s' % (rel, why))
            continue
        sizes[rel] = f.stat().st_size
    for name in ('game.js', 'game.json', 'project.config.json'):
        if name in root and not sizes.get(name):
            out.append('empty root file: %s' % name)
    if out:
        return out, sizes, {}
    from upload_size_gate import enforce
    try:
        enforce(sizes, json.loads((native / 'game.json').read_text(encoding='utf-8-sig')))
    except (ValueError, KeyError, TypeError) as error:
        return [str(error)], sizes, {}
    from audit_no_ad_simulator import enforce_files as enforce_player_windows
    try:
        enforce_player_windows({name: (native / name).read_bytes() for name in sizes})
    except ValueError as error:
        return [str(error)], sizes, {}
    from audit_upload_startup import audit_files
    startup = audit_files({name: (native / name).read_bytes() for name in sizes})
    if not startup['passed']:
        return startup['errors'], sizes, {}
    try:
        game = json.loads((native / 'game.json').read_text(encoding='utf-8-sig'))
        subs = game.get('subpackages', []) if isinstance(game, dict) else None
    except ValueError as e:
        return ['game.json is not valid JSON: %s' % e], sizes, {}
    if not isinstance(subs, list):
        return ['game.json "subpackages" must be an array'], sizes, {}
    roots, info = [], {'independent': {}, 'normal': {}}
    for sub in subs:
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
        out.append('main package %d bytes > %d (biggest: %s): %s' % (info['main'], vnz.TIKTOK_MAIN,
                                                                    ', '.join('%s %d' % kv for kv in big), vnz.FIX_SIZE))
    if total > vnz.TIKTOK_TOTAL:
        out.append('total %d bytes > %d: shrink the art/audio (compress, smaller atlases) - the total limit counts every '
                   'subpackage' % (total, vnz.TIKTOK_TOTAL))
    for r, b in info['independent'].items():
        if b > vnz.TIKTOK_INDEPENDENT:
            out.append('independent subpackage %s %d bytes > %d: make it a normal subpackage or split it' % (r, b, vnz.TIKTOK_INDEPENDENT))
    try:
        app = json.loads((native / 'project.config.json').read_text(encoding='utf-8-sig')).get('appid')
    except (ValueError, AttributeError):
        app = None
    info['appId'] = app
    for rel in sizes:
        p = native / rel
        if p.suffix in ('.js', '.json') and vnz.QA_MARKER in p.read_bytes():
            out.append('test-only level jump %s is still in %s: build the upload package without it' % (vnz.QA_MARKER.decode(), rel))
    return out, sizes, info


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()




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
    ap.add_argument('--board', choices=['localize', 'remake'])
    ap.add_argument('--startup-contract', type=Path)
    ap.add_argument('--loading-recovery-runtime', type=Path)
    ap.add_argument('--resource-manifest', type=Path, help='complete current production resource requests; shared mandatory gate')
    a = ap.parse_args()
    if not (a.review and a.project and a.web and a.build_tag):
        print('REFUSED, no ZIP written: all upload/test/detection packages require --review, --project, --web and --build-tag; use verify_native_zip.py for read-only structure diagnosis', file=sys.stderr)
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
    early_problems, early_sizes, _ = native_problems(native)
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
    problems, sizes, info = native_problems(native)
    if not problems and info.get('appId') != a.app_id:
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
        with package_obligations.publication_guard(obligation_files, native, a.project, a.resource_manifest, obligations):
            os.replace(tmp, out)
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as e:
        print('REFUSED, no ZIP written: the written ZIP failed its own check: %s' % e, file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(tmpdir, True)
    result['archive'] = str(out)
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
              'warnings': result.get('warnings', []), 'left_out_junk': SKIPPED, 'limits_source': vnz.LIMITS_SOURCE,
              'upload': 'upload this ZIP directly - do not unzip, re-zip or wrap it',
              'not_verified': result['not_verified']}
    if a.review is not None:            # BUILD-04 auto report: bound to this build like every other automatic check
        try:
            report['binding'] = json.loads(a.review.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError):
            pass
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'zip', 'zip_sha256', 'zip_bytes', 'appId', 'sizes', 'warnings')},
                     ensure_ascii=False, indent=2))
    print('report: %s' % report_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
