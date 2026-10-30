#!/usr/bin/env python3
"""Final-package checks; shared production verifier, no gameplay CI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ad_regression as ad_regression_gate
import runtime_regression as runtime_regression_gate
SHARED = Path(__file__).resolve().parents[3] / 'remake-core' / 'scripts'
sys.path.insert(0, str(SHARED))
import verify_native_zip as verifier
from audit_packed_assets import audit as packed_assets


def native_files(root):
    files = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('symlink in Native: ' + str(path))
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        why = verifier.forbidden(name)
        if why == 'Finder/Windows junk file':
            continue
        if why:
            raise ValueError(name + ': ' + why)
        files[name] = path.read_bytes()
    return files


def write_archive(path, files):
    from upload_size_gate import enforce_files
    enforce_files(files)
    from audit_no_ad_simulator import enforce_files as enforce_no_simulator
    enforce_no_simulator(files)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)


def rewarded_ad_gate(files, folder, adapter=None):
    """Mandatory rewarded-ad regression on the exact verified bytes staged in folder
    (Basil timeout rule, remake-ads/references/ad-timeout-and-regression.md). Refuses unless
    every case passes; a missing adapter or browser is a refusal, never a skip."""
    if not ad_regression_gate.needs_regression(files):
        return {'id': 'rewarded_ad_regression', 'status': 'not_applicable',
                'reason': 'no createRewardedVideoAd call in package JavaScript'}
    try:
        return ad_regression_gate.run(folder, adapter or os.environ.get(ad_regression_gate.ENV_ADAPTER))
    except ad_regression_gate.RegressionRefused as error:
        raise ValueError(str(error))


def runtime_gate(files, folder, adapter=None):
    """Mandatory runtime regression (runtime_regression.py, references/runtime-regression.md) on the same staged
    bytes and the same adapter as the rewarded-ad regression. Every package with game.js runs the suites shipped
    in runtime_regression/suites that apply to it; a missing adapter/field/browser or a failed case refuses."""
    if 'game.js' not in files:
        return {'id': 'runtime_regression', 'status': 'not_applicable', 'reason': 'no game.js at package root'}
    adapter = adapter or os.environ.get(runtime_regression_gate.ENV_ADAPTER)
    try:
        names = runtime_regression_gate.required_suites(files, adapter)
        return runtime_regression_gate.run(folder, adapter, names)
    except runtime_regression_gate.RuntimeRefused as error:
        raise ValueError(str(error))


def _fallback_entries(archive):
    """Entries of a ZIP the verifier refused, so the remaining checks can still list their reasons.
    Unsafe or forbidden names are left out (they are already the verifier's reason)."""
    out = {}
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if info.is_dir() or info.flag_bits & 1:
                continue
            try:
                verifier.safe_name(info.filename)
            except ValueError:
                continue
            if verifier.forbidden(info.filename):
                continue
            out[info.filename] = z.read(info)
    return out


def check(archive, app_id=None, tree=None, ad_regression=None, board=None, policy=None, context=None):
    """Read-only final check of the exact bytes. Every reason is collected and the package is refused ONCE with
    all of them (verifier, Credits/no-ad-simulator, startup, packed assets, shared package gates, rewarded-ad
    and runtime regressions) instead of stopping at the first (MusicSlice 0f).

    ad_regression: adapter JSON path for the mandatory rewarded-ad regression; falls back to
    $TIKTOK_AD_REGRESSION_ADAPTER. A package that can request a rewarded video is refused
    without a passing regression (no adapter, no browser and a failed case all refuse).
    board: 'remake' | 'localize' | None; the package gates use it only to choose block vs warning.
    policy (v7.7): 'new' | 'legacy' from a writer's finalize record; None (check_package.py given only a ZIP, and
    prepare_delivery.py) = judged from the package bytes (scene / asset uuids against LEGACY_GAMES.json, not listed
    = new). context: writer-only kit_parts attributes (finalize record, project) for K4/K5."""
    import package_gates
    start_sha = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    reasons = []
    verified_files = {}
    try:
        result = verifier.verify(archive, expected_app_id=app_id, _verified_files=verified_files)
    except ValueError as error:
        reasons.append('verifier: ' + str(error))
        result = None
        verified_files = _fallback_entries(archive)
        from audit_no_ad_simulator import check_entry
        window_hit = False
        for name in sorted(verified_files):
            try:
                check_entry(name, verified_files[name])
            except ValueError as entry_error:
                window_hit = True
                if str(entry_error) not in reasons[0]:
                    reasons.append(str(entry_error))
        # Same boundary as make_tiktok_zip.native_problems: never run the startup audit (Node probes execute
        # package JS) on a package that still carries a player window; the static package gates still run.
        if 'game.js' in verified_files and not window_hit:
            from audit_upload_startup import audit_files
            startup = audit_files(verified_files)
            reasons.extend(e for e in startup['errors'] if e not in reasons[0])
    if tree is not None and result is not None:
        expected = {name: hashlib.sha256(data).hexdigest() for name, data in native_files(Path(tree)).items()}
        if expected != result['file_sha256']:
            reasons.append('final ZIP differs from actual Native input paths/bytes')
        else:
            result['expected_tree_exact'] = True
    gates = package_gates.run(verified_files, None, board, policy=policy, context=context)
    reasons.extend(package_gates.messages(gates['blocks']))
    regression = runtime = None
    with tempfile.TemporaryDirectory(prefix='TikTok package extract ') as folder:
        # Paths and CRC were validated above; stage those exact bytes, not a second ZIP read.
        for name, data in verified_files.items():
            target = Path(folder) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        assets = packed_assets(folder)
        if not assets['passed']:
            reasons.append('packed resource check: ' + '; '.join(assets['errors']))
        try:
            regression = rewarded_ad_gate(verified_files, folder, ad_regression)
        except ValueError as error:
            reasons.append(str(error))
        try:
            runtime = runtime_gate(verified_files, folder, ad_regression)
        except ValueError as error:
            reasons.append(str(error))
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != (result['sha256'] if result else start_sha):
        raise ValueError('ZIP changed during package checks')
    if reasons:
        if len(reasons) == 1:
            raise ValueError(reasons[0])
        raise ValueError('%d reasons, all listed: ' % len(reasons) + ' || '.join(reasons))
    result['packed_resource_check'] = assets
    result['rewarded_ad_regression'] = regression
    result['runtime_regression'] = runtime
    result['package_gates'] = package_gates.summary(gates)
    from make_tiktok_zip import pre_home
    result['pre_home_bytes'] = pre_home(verified_files, None, board)
    result['board'] = board
    result['policy'] = gates.get('policy')
    result['policy_reason'] = gates.get('policy_reason')
    # Encoding and decoding are distinct capabilities. Never silently treat
    # a successful static archive check as WebP runtime coverage.
    webp = sorted(name for name in result['file_sha256'] if name.lower().endswith('.webp'))
    result['runtime_requirements'] = []
    if webp:
        result['runtime_requirements'].append({
            'id': 'webp_decode_capability', 'status': 'requires_runtime_evidence',
            'resource_count': len(webp), 'resources': webp,
            'reference': 'cocos-game-check/package-check/references/webp-decode-capability.md',
            'cases': ['png_only_encoder_working_decoder_old_failure',
                      'png_only_encoder_working_decoder_fixed_success',
                      'normal_encoder_control', 'decoder_error_not_enabled',
                      'decoder_timeout_not_enabled', 'zero_dimensions_not_enabled',
                      'duplicate_terminal_once'],
            'boundary': 'Static detection only. Use actual final Native engine/adapter; do not force webp=true or count Canvas encoding as decoding.'})
    result['runtime_execution'] = 'not_executed_by_static_package_checker'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--expected-app-id')
    parser.add_argument('--expected-tree', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--ad-regression', type=Path, help='adapter JSON for the mandatory rewarded-ad and runtime regressions '
                        '(default $%s)' % ad_regression_gate.ENV_ADAPTER)
    parser.add_argument('--board', choices=['remake', 'localize'], help='remake | localize; package gates use it only '
                        'to choose block vs warning (default: unknown)')
    parser.add_argument('--policy', choices=['new', 'legacy'], help='tests and calibration only (design D77 3): '
                        'judge the package as a new or a legacy game. Default: from the package itself (frozen '
                        'legacy list; not listed = new). The writers and prepare_delivery.py never pass it')
    args = parser.parse_args()
    try:
        if args.report and args.report.exists():
            raise ValueError('refuse to overwrite report')
        if args.input.is_dir():
            with tempfile.TemporaryDirectory(prefix='TikTok Native preflight ') as temp:
                zipped = Path(temp) / 'candidate.zip'
                write_archive(zipped, native_files(args.input))
                result = check(zipped, args.expected_app_id, args.input, args.ad_regression, args.board, args.policy)
                result['input'] = str(args.input.resolve())
                result.pop('archive', None)
        else:
            result = check(args.input, args.expected_app_id, args.expected_tree, args.ad_regression, args.board, args.policy)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('file_sha256', 'packed_resource_check')}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(json.dumps({'status':'refuse', 'error':str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
