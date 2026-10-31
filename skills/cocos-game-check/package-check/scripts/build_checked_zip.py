#!/usr/bin/env python3
"""Finished-product writer: final-file checks without rerunning gameplay CI.

v7.5: rewrites the stock Cocos 2.4 ByteDance adapter forms first (package_gates/adapter_fix.py), runs the same
native_problems() as make_tiktok_zip.py (all reasons at once, shared package gates, --board remake|localize), and
publishes <out>.receipt.json with the ZIP; prepare_delivery.py refuses a ZIP without a matching receipt.

v7.7 (design D77 1.1-1.2): --project is required. The source record <project>/.tiktok-kit/finalize-source.json must
match the project and kit version (K5, checked before the build folder is touched), then
make_tiktok_zip.finalize_for_writer runs tiktok_finalize.finalize_native in place of adapter_fix.apply (same function
as make_tiktok_zip.py), the App ID is compared after finalize wrote it, and every package gate runs with the finalize
record (K4) and its policy. Report and receipt carry `finalize`.

v7.8 (U7 补): the same finalize_for_writer also CHECKS the art receipt <project>/.tiktok-kit/art-receipt.json written by
art_check.py (remake-core/scripts/art_receipt.py; the art check itself is never re-run here, Saul 10-24). A new remake
game without a passing receipt whose image fingerprints equal the project's is refused before the build folder is
touched; legacy and English games get a warning, a Cocos 3.x receipt "3.x 未覆盖" passes with a warning, and the result
is a row of the finalize table printed below.

v7.8 (总表 B32 b, d): after the ZIP is published, older packages of the same game in the --out folder go into 旧包/
with their receipts and 最新.txt names the file to upload (remake-core/scripts/delivery_folder.py; --keep-old-packages
leaves the folder alone); check() lists check tools that are not the released / installed ones (tool_identity.py,
result modified_tools) and a feedback draft goes into ！Skill更新/ (new file only)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import check_package as package_checks
from check_package import native_files, write_archive, check
from audit_final_package_startup import audit_final_startup
import package_obligations


def build(native, app_id, out, report=None, interaction_audio_trace=None, resource_manifest=None, project=None, startup_contract=None, loading_recovery_runtime=None, ad_regression=None, board=None, keep_webp_exception=None, keep_old_packages=False):
    started = time.monotonic()
    native, out = Path(native).resolve(), Path(out).resolve()
    if not native.is_dir():
        raise ValueError('Native input directory missing')
    if out.suffix.lower() != '.zip':
        raise ValueError('upload output must end in .zip')
    if out.exists() or out.is_relative_to(native):
        raise ValueError('output must be new and outside Native input')
    report = Path(report).resolve() if report else None
    if report and (report.exists() or report == out or report.is_relative_to(native)):
        raise ValueError('report must be new, outside Native, and distinct from ZIP')
    # Target/config mistakes are deterministic; refuse before parsing the
    # whole package or starting the reviewed Native/browser runner.
    if not isinstance(app_id, str) or not app_id.strip():
        raise ValueError('a nonempty target App ID is required')
    if not resource_manifest:
        raise ValueError('runtime resource manifest required: expand actual business load requests before writing ZIP')
    import verify_native_zip as verifier
    receipt_file = verifier.receipt_path(out)
    if receipt_file.exists() or receipt_file.is_symlink():
        raise ValueError('receipt already exists next to the output ZIP')
    out.parent.mkdir(parents=True, exist_ok=True)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
    # v7.7: source record current (K5, nothing changed when refused), then finalize installs the platform-kit
    # standard parts BEFORE any check; its first step is the v7.5 adapter_fix rewrite (unknown adapter = refused).
    from make_tiktok_zip import adapter_step, finalize_for_writer, finalize_report, native_problems
    options = {'keep_webp_exception': keep_webp_exception} if keep_webp_exception else {}
    finalized, gate_context, finalize_problems = finalize_for_writer(native, project, board, app_id, options)
    if finalize_problems:
        raise ValueError('tiktok_finalize: ' + '; '.join(finalize_problems))
    gate_policy = finalized['policy']
    # finalize wrote the App ID (appid step); the build must now carry exactly the requested target.
    config = json.loads((native / 'project.config.json').read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict) or config.get('appid') != app_id:
        raise ValueError('Root App ID does not match the requested target')
    # Use the production byte limits before creating even a temporary archive.
    # native_problems lists every reason at once, including the shared package gates.
    problems, _, sizes = native_problems(native, board, gate_policy, gate_context)
    if problems:
        raise ValueError('; '.join(problems))
    files = native_files(native)
    manifest_path = Path(resource_manifest).resolve()
    manifest_bytes = manifest_path.read_bytes()
    obligations = package_obligations.verify(files, native, project, manifest_path)
    from make_tiktok_zip import english_image_problems
    english_problems = english_image_problems(files, project, board)
    if english_problems:
        raise ValueError('; '.join(english_problems))
    # native_problems already enforces the shared startup-dependency audit.
    # Do not run that identical check twice before runtime. Packed assets,
    # however, were previously only checked after the expensive runner.
    assets = package_checks.packed_assets(native)
    if not assets['passed']:
        raise ValueError('packed resource check: ' + '; '.join(assets['errors']))
    observed = None
    if interaction_audio_trace:
        from audit_interaction_audio import audit
        observed = audit(interaction_audio_trace, native)
        if not observed['passed']:
            raise ValueError('interaction/audio: ' + '; '.join(observed['errors']))
    static_seconds = time.monotonic() - started
    runtime_started = time.monotonic()
    startup_runtime = audit_final_startup(native, project, startup_contract, loading_recovery_runtime)
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError('runtime resource manifest changed during startup validation')
    runtime_seconds = time.monotonic() - runtime_started
    fd, filename = tempfile.mkstemp(prefix='.tiktok-package-', suffix='.zip', dir=out.parent)
    os.close(fd)
    temporary = Path(filename)
    report_temp = None
    receipt_temp = None
    report_published = False
    try:
        archive_started = time.monotonic()
        write_archive(temporary, files)
        result = check(temporary, app_id, native, ad_regression, board, policy=gate_policy, context=gate_context)
        result['archive'] = str(out)
        result['finalize'] = finalize_report(finalized)
        result['adapter_fix'] = adapter_step(finalized)
        result['native_pre_home_bytes'] = sizes.get('pre_home_bytes')
        receipt = verifier.make_receipt('build_checked_zip', temporary, result['sha256'], result['file_sha256'],
                                        result['package_gates'], board,
                                        {'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                                        finalize=finalized)
        problem = verifier.finalize_problem(receipt['finalize'], result['file_sha256'])
        if problem:
            raise ValueError('finalize record does not match the ZIP: ' + problem)
        result.update(entry='official', entry_label=verifier.ENTRY_LABEL['official'],
                      entry_reason='matching receipt from build_checked_zip', receipt=str(receipt_file))
        result['final_startup_runtime'] = startup_runtime
        result['package_obligations'] = obligations
        if observed is not None:
            result['interaction_audio_check'] = observed
        result['check_timings'] = {
            'static_preflight_seconds': round(static_seconds, 6),
            'startup_runtime_seconds': round(runtime_seconds, 6),
            'archive_validation_seconds': round(time.monotonic() - archive_started, 6),
            'total_seconds': round(time.monotonic() - started, 6)}
        with package_obligations.publication_guard(files, native, project, manifest_path, obligations):
            if report:
                fd, name = tempfile.mkstemp(prefix='.tiktok-evidence-', dir=report.parent)
                os.close(fd)
                report_temp = Path(name)
                report_temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
                os.link(report_temp, report)
                report_published = True
            fd, name = tempfile.mkstemp(prefix='.tiktok-receipt-', dir=out.parent)
            os.close(fd)
            receipt_temp = Path(name)
            receipt_temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            os.link(receipt_temp, receipt_file)      # never overwrites; removed again if the ZIP cannot be published
            try:
                os.link(temporary, out)
            except OSError:
                receipt_file.unlink(missing_ok=True)
                if report_published and report_temp.samefile(report):
                    report.unlink()
                raise
        # v7.8 (总表 B32 b): older packages of this game go into 旧包/, the folder keeps this one and 最新.txt.
        import delivery_folder
        result['delivery_folder'] = delivery_folder.tidy(out, app_id, 'build_checked_zip', result['sha256'],
                                                         keep=keep_old_packages)
        # v7.8 (总表 B32 d): check() listed changed tools (tool_identity); they get a feedback draft for the Skill.
        draft = package_checks.feedback_draft(result.get('tool_identity'), Path(project).name if project else out.stem)
        if draft:
            result['tool_feedback_draft'] = draft
        return result
    finally:
        temporary.unlink(missing_ok=True)
        if report_temp:
            report_temp.unlink(missing_ok=True)
        if receipt_temp:
            receipt_temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--expected-app-id', required=True)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--resource-manifest', type=Path, help='expanded business load requests for final bundle path/type validation')
    parser.add_argument('--interaction-audio-trace', type=Path, help='required by workflow for reported drag/audio defects; checked before ZIP creation')
    parser.add_argument('--project', type=Path, required=True, help='the Cocos project (v7.7: its tiktok_finalize source record is checked)')
    parser.add_argument('--startup-contract', type=Path)
    parser.add_argument('--loading-recovery-runtime', type=Path)
    parser.add_argument('--ad-regression', type=Path, help='adapter JSON for the rewarded-ad and runtime regressions (default $TIKTOK_AD_REGRESSION_ADAPTER); every package with game.js is refused without it')
    parser.add_argument('--board', choices=['remake', 'localize'], help='remake | localize; package gates use it only to choose block vs warning (default: unknown)')
    parser.add_argument('--keep-webp-exception', metavar='REASON', help='design D77 3.6 WebP exception (same reason as tiktok_finalize.py source)')
    parser.add_argument('--keep-old-packages', action='store_true', help='v7.8: leave older packages of this game in the '
                        'output folder and do not write 最新.txt (e.g. a writer-refusal test ZIP); default: they go into 旧包/')
    args = parser.parse_args()
    try:
        if args.report and args.report.exists():
            raise ValueError('report already exists')
        result = build(args.native, args.expected_app_id, args.out, args.report, args.interaction_audio_trace, args.resource_manifest, args.project, args.startup_contract, args.loading_recovery_runtime, args.ad_regression, args.board, args.keep_webp_exception, args.keep_old_packages)
        print(json.dumps({k:result.get(k) for k in ('archive','sha256','archive_bytes','main_bytes','uncompressed_total_bytes','expected_tree_exact','check_timings','pre_home_bytes','entry','receipt')}, ensure_ascii=False))
        print('finalize (policy %s):\n%s' % (result['finalize']['policy'], result['finalize']['table_markdown']))
        import delivery_folder
        print('\n'.join(delivery_folder.describe(result['delivery_folder'])))
        if result.get('modified_tools'):
            print('改过的工具：%s%s' % ('; '.join(result['modified_tools']),
                                     '（反馈草稿：%s）' % result['tool_feedback_draft'] if result.get('tool_feedback_draft') else ''))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({'status':'refuse', 'error':str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
