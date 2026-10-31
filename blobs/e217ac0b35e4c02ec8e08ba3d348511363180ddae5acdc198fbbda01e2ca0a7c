#!/usr/bin/env python3
"""Final-package checks; shared production verifier, no gameplay CI.

v7.8 (总表 B17): run as a command on a ZIP without a matching writer receipt, the verdict is
"只读预检，不可交付（非官方入口）" (status unofficial_not_deliverable, exit 3); 丛林荡藤 v6 and 剪刀达人 v30 were
called a pass that way. --structure-only keeps the old answer for diagnosis. check() itself is unchanged: both
writers and prepare_delivery import it.

v7.8 (总表 B32 d): check() adds tool_identity (tool_identity.py): the check tools in use compared with the Skill's
release record and the installed copies. Changed or not-installed tools are 「改过的工具」 (result modified_tools and a
warning; never a refusal); this command and build_checked_zip then write a feedback draft into ！Skill更新/
(反馈草稿_改过的工具_<游戏>_<日期>.md, new file only; $COCOS_SKILL_FEEDBACK_DIR moves it, for tests)."""
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


READ_ONLY_VERDICT = '只读预检，不可交付（非官方入口）'
READ_ONLY_DIR = '只读预检，不可交付（Native 目录不是上传包；上传包只能由 build_checked_zip.py 或 make_tiktok_zip.py 写出）'
OFFICIAL_VERDICT = '官方入口写出的包，本地检查通过（不代表平台或真机验收）'
UNOFFICIAL_CLI = (READ_ONLY_VERDICT + ': %s. Only a ZIP written by build_checked_zip.py or make_tiktok_zip.py (with '
                  '<zip>.receipt.json beside it, or a receipt for the same ZIP bytes in that folder) may be delivered; '
                  'add --structure-only for a read-only check that does not judge delivery')


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


def runtime_gate(files, folder, adapter=None, policy=None, board=None):
    """Mandatory runtime regression (runtime_regression.py, references/runtime-regression.md) on the same staged
    bytes and the same adapter as the rewarded-ad regression. Every package with game.js runs the suites shipped
    in runtime_regression/suites that apply to it; a missing adapter/field/browser or a failed case refuses.
    policy (v7.8): the package gates' policy ('new' | 'legacy'), so a writer's finalize record decides the runtime
    suites too (dead_shell: FoxDenDash v1's record says new, its bytes say legacy); None = judged from the bytes.
    board (v7.8, 总表 B30): 'remake' | 'localize' picks layout_state's home rules; None = not checked (warning).
    The writers have no trial link, so trial_link never runs here (summary not_run says so)."""
    if 'game.js' not in files:
        return {'id': 'runtime_regression', 'status': 'not_applicable', 'reason': 'no game.js at package root'}
    adapter = adapter or os.environ.get(runtime_regression_gate.ENV_ADAPTER)
    try:
        names = runtime_regression_gate.required_suites(files, adapter)
        return runtime_regression_gate.run(folder, adapter, names, policy=policy,
                                           board=board if board in runtime_regression_gate.BOARDS else None)
    except runtime_regression_gate.RuntimeRefused as error:
        raise ValueError(str(error))


NO_ADAPTER_HINT = ('write the game\'s adapter JSON (usually <project>/qa/ad-regression.json; fields: '
                   'cocos-game-check/package-check/references/runtime-regression.md and '
                   'remake-ads/references/ad-timeout-and-regression.md) and pass it with --ad-regression or $%s'
                   % ad_regression_gate.ENV_ADAPTER)


def writer_regressions(files, folder, adapter=None, policy=None, board=None):
    """v7.8 (W97, 总表 22.6 D/E): the rewarded-ad and runtime regressions for make_tiktok_zip.py, which does not call
    check(). Same two gates as check() (rewarded_ad_gate, then runtime_gate with the same adapter, policy and board) on
    the staged bytes of the ZIP about to be published. Never raises: -> {blocked, problems, warnings, policy, adapter,
    rewarded_ad_regression, runtime_regression, seconds}. policy 'legacy' (the writer's finalize record: a game on the
    frozen legacy list) turns every refusal into a warning; anything else (new, or None judged from the bytes as new
    when the bytes cannot decide) refuses. check() and build_checked_zip are unchanged."""
    import time
    started = time.monotonic()
    adapter = adapter or os.environ.get(ad_regression_gate.ENV_ADAPTER) or None
    legacy = policy == 'legacy'
    out = {'id': 'writer_regressions', 'policy': policy, 'board': board, 'adapter': str(adapter) if adapter else None,
           'rewarded_ad_regression': None, 'runtime_regression': None, 'problems': [], 'warnings': []}
    reasons = []
    for key, gate in (('rewarded_ad_regression', lambda: rewarded_ad_gate(files, folder, adapter)),
                      ('runtime_regression', lambda: runtime_gate(files, folder, adapter, policy=policy, board=board))):
        try:
            out[key] = gate()
        except Exception as error:  # noqa: BLE001 - fail closed: a crash refuses a new game like a failed case
            text = str(error) if isinstance(error, ValueError) else '%s crashed: %r' % (key, error)
            if not adapter and not any(NO_ADAPTER_HINT in r for r in reasons):
                text += ' - no adapter given: ' + NO_ADAPTER_HINT
            reasons.append(text)
            partial = getattr(error.__context__, 'summary', None)   # runtime_gate re-raises RuntimeRefused as ValueError
            out[key] = dict(partial, status='failed') if isinstance(partial, dict) else {'id': key, 'status': 'failed',
                                                                                         'error': text[:2000]}
    if isinstance(out['runtime_regression'], dict):
        out['warnings'].extend(out['runtime_regression'].get('warnings') or [])
    if legacy:
        out['warnings'].extend('%s [legacy game: warning]' % r for r in reasons)
    else:
        out['problems'] = reasons
    out['blocked'] = bool(out['problems'])
    out['seconds'] = round(time.monotonic() - started, 1)
    return out


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
            runtime = runtime_gate(verified_files, folder, ad_regression, policy=gates.get('policy'), board=board)
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
    # v7.8 (S8 补): the static estimate above (W8_prehome_bytes, 15 MB warning) next to what the host measured
    # (layout_state startup_size / startup_audio: 10 MiB and no sound, the number that blocks)
    if isinstance(result['pre_home_bytes'], dict) and isinstance(runtime, dict):
        result['pre_home_bytes']['measured'] = runtime.get('startup_measured')
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
    # v7.8 (总表 B32 d): which check tools judged this package; changed / not installed ones are listed, never a refusal.
    result['tool_identity'] = tools_in_use()
    if result['tool_identity'].get('status') == 'modified':
        result['modified_tools'] = result['tool_identity']['summary']
        result.setdefault('warnings', []).append('改过的工具: ' + '; '.join(result['tool_identity']['summary']))
    return result


def tools_in_use():
    """tool_identity.identity() of the tools in this folder; an error is reported, never raised."""
    try:
        import tool_identity
        return tool_identity.identity(Path(__file__).resolve().parent)
    except Exception as error:  # noqa: BLE001 - reporting only
        return {'status': 'error', 'error': repr(error)[:300], 'modified': [], 'summary': []}


def feedback_draft(identity, game):
    """Write the 改过的工具 feedback draft into ！Skill更新/ (tool_identity.write_draft). -> path or None."""
    if not isinstance(identity, dict) or identity.get('status') != 'modified':
        return None
    try:
        import tool_identity
        path = tool_identity.write_draft(identity, game)
        return str(path) if path else None
    except Exception as error:  # noqa: BLE001 - a draft that cannot be written never changes the verdict
        print('改过的工具：反馈草稿没写成：%r' % (error,), file=sys.stderr)
        return None


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
    parser.add_argument('--structure-only', action='store_true',
                        help='read-only diagnosis: run every check but do not refuse a ZIP without a matching writer '
                        'receipt (the answer is then not a delivery approval)')
    args = parser.parse_args()
    refused = None
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
            result['verdict'] = READ_ONLY_DIR
        else:
            result = check(args.input, args.expected_app_id, args.expected_tree, args.ad_regression, args.board, args.policy)
            # v7.8 (总表 B17): check() is unchanged (the writers import it); only this command refuses a ZIP that no
            # official writer wrote, as verify_native_zip.py / upload_preflight.py do since v7.7.4.
            if result.get('entry') == 'official':
                result['verdict'] = OFFICIAL_VERDICT
            elif args.structure_only:
                result.update(verdict=READ_ONLY_VERDICT, mode='structure-only (not a delivery approval)')
            else:
                refused = UNOFFICIAL_CLI % result.get('entry_reason')
                result.update(status='unofficial_not_deliverable', verdict=READ_ONLY_VERDICT, refused=refused)
        # v7.8 (总表 B32 d): changed tools get a feedback draft for the Skill session (new file in ！Skill更新/).
        draft = feedback_draft(result.get('tool_identity'), args.input.stem)
        if draft:
            result['tool_feedback_draft'] = draft
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('file_sha256', 'packed_resource_check', 'tool_identity')}, ensure_ascii=False))
        if result.get('modified_tools'):
            print('改过的工具: %s%s' % ('; '.join(result['modified_tools']),
                                     '（反馈草稿：%s）' % draft if draft else ''), file=sys.stderr)
        print('结论: %s' % result['verdict'], file=sys.stderr)
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        identity = tools_in_use()       # a refusal made with changed tools is reported the same way
        out = {'status': 'refuse', 'error': str(error)}
        if identity.get('status') == 'modified':
            out.update(modified_tools=identity['summary'], tool_feedback_draft=feedback_draft(identity, args.input.stem))
        print(json.dumps(out, ensure_ascii=False))
        return 1
    if refused:
        print('REFUSED: ' + refused, file=sys.stderr)
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
