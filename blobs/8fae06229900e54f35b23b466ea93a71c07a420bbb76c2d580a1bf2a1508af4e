"""Narrow production hooks: admitted resource preparation and nonblocking learning.

No hook starts game QA, a browser, upload, shared-Skill maintenance or installation.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

RESOURCE_HOME = Path('.tiktok-kit/resource-package')
RESOURCE_PLAN = Path('docs/startup/resource-package-plan.json')


def admit_resources(project):
    """Called only for a fresh localization intake, never for existing markers."""
    project = Path(project).resolve()
    path = project / RESOURCE_HOME / 'scope.json'
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    try:
        temporary.write_text(json.dumps({'schema': 'production-resource-scope.v1',
            'scope': 'first_full_localization', 'resource_preparation': True}, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def resource_enabled(project):
    project = Path(project)
    return any((project / p).is_file() for p in (RESOURCE_HOME / 'scope.json',
                RESOURCE_HOME / 'prepared.json', RESOURCE_PLAN))


def resource_step(project, board, *, native=None, policy_override=None):
    """Production-only route. Existing unadmitted maintenance is unchanged."""
    if not project or board != 'localize' or policy_override is not None or not resource_enabled(project):
        return None
    from resource_package_prepare import prepare, calibrate
    return calibrate(project, native) if native is not None else prepare(project, board=board)


def resource_refresh(project, board, *, policy_override=None):
    """After standard source steps, update proof only; never change build inputs."""
    if not project or board != 'localize' or policy_override is not None or not resource_enabled(project):
        return None
    from resource_package_prepare import refresh_current
    return refresh_current(project)


def collect_after_delivery(project, *, record_paths=(), final_zip_sha256=None):
    """Best-effort existing-record collection; never changes delivery readiness."""
    if project is None:
        return {'status': 'not_applicable', 'delivery_blocking': False}
    try:
        root = Path(project).resolve()
        from production_learning import collect_nonblocking, DEFAULT_RECORDS
        selected = []
        for value in (*DEFAULT_RECORDS, *record_paths):
            if not value:
                continue
            path = Path(value)
            path = path.resolve() if path.is_absolute() else (root / path).resolve()
            if path.is_relative_to(root) and path.is_file():
                name = path.relative_to(root).as_posix()
                if name not in selected:
                    selected.append(name)
        context = {'delivery_ready': True}
        if isinstance(final_zip_sha256, str) and len(final_zip_sha256) == 64:
            context['final_zip_sha256'] = final_zip_sha256
        return collect_nonblocking(root, record_paths=selected, trigger='delivery', context=context)
    except Exception as error:
        # An outbox/import problem is never a new game delivery gate.
        return {'status': 'deferred', 'delivery_blocking': False,
                'diagnostics': [type(error).__name__ + ': ' + str(error)]}
