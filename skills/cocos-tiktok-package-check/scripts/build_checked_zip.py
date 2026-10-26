#!/usr/bin/env python3
"""Finished-product writer: final-file checks without rerunning gameplay CI."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time
import check_package as package_checks
from check_package import native_files, write_archive, check
from audit_final_package_startup import audit_final_startup
import package_obligations


def build(native, app_id, out, report=None, interaction_audio_trace=None, resource_manifest=None, project=None, startup_contract=None, loading_recovery_runtime=None):
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
    config = json.loads((native / 'project.config.json').read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict) or config.get('appid') != app_id:
        raise ValueError('Root App ID does not match the requested target')
    out.parent.mkdir(parents=True, exist_ok=True)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
    # Use the production byte limits before creating even a temporary archive.
    from make_tiktok_zip import native_problems
    problems, _, sizes = native_problems(native)
    if problems:
        raise ValueError('; '.join(problems))
    if not resource_manifest:
        raise ValueError('runtime resource manifest required: expand actual business load requests before writing ZIP')
    files = native_files(native)
    manifest_path = Path(resource_manifest).resolve()
    manifest_bytes = manifest_path.read_bytes()
    obligations = package_obligations.verify(files, native, project, manifest_path)
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
    report_published = False
    try:
        archive_started = time.monotonic()
        write_archive(temporary, files)
        result = check(temporary, app_id, native)
        result['archive'] = str(out)
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
            try:
                os.link(temporary, out)
            except OSError:
                if report_published and report_temp.samefile(report):
                    report.unlink()
                raise
        return result
    finally:
        temporary.unlink(missing_ok=True)
        if report_temp:
            report_temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--expected-app-id', required=True)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--resource-manifest', type=Path, help='expanded business load requests for final bundle path/type validation')
    parser.add_argument('--interaction-audio-trace', type=Path, help='required by workflow for reported drag/audio defects; checked before ZIP creation')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--startup-contract', type=Path)
    parser.add_argument('--loading-recovery-runtime', type=Path)
    args = parser.parse_args()
    try:
        if args.report and args.report.exists():
            raise ValueError('report already exists')
        result = build(args.native, args.expected_app_id, args.out, args.report, args.interaction_audio_trace, args.resource_manifest, args.project, args.startup_contract, args.loading_recovery_runtime)
        print(json.dumps({k:result[k] for k in ('archive','sha256','archive_bytes','main_bytes','uncompressed_total_bytes','expected_tree_exact','check_timings')}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({'status':'refuse', 'error':str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
