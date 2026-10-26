"""One shared mandatory resource/registered-defect gate for both writers and delivery."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import audit_runtime_resources as resources
import package_issue_gate as issues


def verify(files, native, project, resource_manifest):
    if not project:
        raise ValueError('package obligations require --project and its fixed issue history')
    if not resource_manifest:
        raise ValueError('runtime resource manifest required for both writers and final delivery')
    # Missing/open issues are a cheap refusal, before JS discovery or browser runs.
    try:
        issue_result = issues.audit(project, native)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('malformed reported-issue evidence: '+str(error)) from error
    path = Path(resource_manifest).resolve()
    raw = path.read_bytes()
    resource_result = resources.audit(files, json.loads(raw))
    return {'passed': True, 'resource_manifest': str(path),
            'resource_manifest_sha256': hashlib.sha256(raw).hexdigest(),
            'reported_issues': issue_result, 'resources': resource_result}


def signature(result):
    return issues.digest(result)


@contextmanager
def publication_guard(files, native, project, resource_manifest, expected):
    # Only the short publication step is locked. No long gameplay/browser run
    # holds the issue lock, and no other game/project is affected.
    with issues.editing(project):
        import verify_native_zip as verifier
        actual = {}
        for path in Path(native).rglob('*'):
            if path.is_symlink():
                raise ValueError('Native changed to contain a symlink before publication')
            if path.is_file():
                name = path.relative_to(native).as_posix()
                if verifier.forbidden(name) == 'Finder/Windows junk file':
                    continue
                actual[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}:
            raise ValueError('Native changed before package publication')
        current = verify(files, native, project, resource_manifest)
        if signature(current) != signature(expected):
            raise ValueError('resource manifest or reported-issue evidence changed during packaging')
        yield current
