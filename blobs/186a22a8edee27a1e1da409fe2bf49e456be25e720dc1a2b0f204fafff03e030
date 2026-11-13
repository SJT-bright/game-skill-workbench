#!/usr/bin/env python3
"""Compatibility name for the sole make_tiktok_zip.write_package backend.

The callable build() signature is retained. Neither this file nor its CLI owns
preparation, validation, archive writing or fallback execution.
"""
from pathlib import Path
import sys

SHARED = Path(__file__).resolve().parents[3] / 'remake-core/scripts'
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))


def build(native, app_id, out, report=None, interaction_audio_trace=None, resource_manifest=None,
          project=None, startup_contract=None, loading_recovery_runtime=None, ad_regression=None,
          board=None, keep_webp_exception=None, keep_old_packages=False, rework_of=None, *,
          web=None, build_tag=None, review=None, coverage=None, writer_evidence=None,
          native_resource_paths_runtime=None, webp_codec_reports=None):
    import make_tiktok_zip
    return make_tiktok_zip.write_package(native=native, app_id=app_id, out=out, report=report,
        interaction_audio_trace=interaction_audio_trace, resource_manifest=resource_manifest, project=project,
        startup_contract=startup_contract, loading_recovery_runtime=loading_recovery_runtime,
        ad_regression=ad_regression, board=board, keep_webp_exception=keep_webp_exception,
        keep_old_packages=keep_old_packages, rework_of=rework_of, web=web, build_tag=build_tag,
        review=review, coverage=coverage, writer_evidence=writer_evidence,
        native_resource_paths_runtime=native_resource_paths_runtime, webp_codec_reports=webp_codec_reports)


def main(argv=None):
    import make_tiktok_zip
    return make_tiktok_zip.main(argv)


if __name__ == '__main__':
    raise SystemExit(main())
