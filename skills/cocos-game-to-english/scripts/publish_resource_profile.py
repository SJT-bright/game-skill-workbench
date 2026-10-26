"""Publish one reviewed finite resource profile without machine-local references.

This is an update writer, not semantic approval or a game acceptance gate.
It uses the unchanged resource auditor before replacing one registry entry.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def native_files(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Native directory missing')
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Native profile input may not contain symlinks')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def embedded_previous(row, registry):
    previous = copy.deepcopy(row)
    if 'profile_ref' in previous:
        ref = previous.pop('profile_ref')
        path = Path(ref['path'])
        path = path if path.is_absolute() else registry.parent / path
        raw = path.read_bytes()
        if sha(raw) != ref['sha256']:
            raise ValueError('previous resource profile reference changed')
        content = json.loads(raw)
        if content.get('source_sha256') != previous.get('source_sha256'):
            raise ValueError('previous resource profile reference source differs')
        previous = dict(content, **previous)
    return previous


def prepare(profile, files, entries, name, registry):
    if not isinstance(profile, dict) or 'profile_ref' in profile:
        raise ValueError('publish the complete reviewed profile, not profile_ref')
    for key in ('source_sha256', 'resolutions', 'escapes'):
        if not isinstance(profile.get(key), dict):
            raise ValueError('resource profile requires an object: ' + key)
    spec = importlib.util.spec_from_file_location('_resource_publish_auditor', HERE / 'audit_runtime_resources.py')
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)
    previous = embedded_previous(entries.get(name, {}), registry)
    # A normal regeneration must not erase existing constraints/metadata.
    candidate = dict(previous, **copy.deepcopy(profile))
    for key in set(previous) - {'source_sha256', 'resolutions', 'escapes'}:
        if key in profile and profile[key] != previous[key]:
            raise ValueError('existing resource profile constraint changed: ' + key)
    digest = sha(json.dumps(auditor._serialized_asset_data_hashes(files), sort_keys=True, separators=(',', ':')).encode())
    if previous.get('data_digest_kind') not in (None, 'serialized-json-assets-v1'):
        raise ValueError('unsupported existing resource profile data fingerprint')
    if previous.get('data_digest') not in (None, digest):
        raise ValueError('resource semantic data changed; review finite domains before publishing')
    if profile.get('data_digest_kind') not in (None, 'serialized-json-assets-v1') or profile.get('data_digest') not in (None, digest):
        raise ValueError('incoming resource profile data fingerprint differs')
    # An existing live data-domain parser already binds the actual current
    # data on every audit. Do not turn it into a fixed-data profile here.
    if not candidate.get('data_domains') or 'data_digest' in candidate:
        candidate.update(data_digest_kind='serialized-json-assets-v1', data_digest=digest)
    updated = copy.deepcopy(entries)
    updated[name] = candidate
    # Only this isolated module instance sees the prospective registry.
    # All existing discovery/type/coverage/current-file predicates still run.
    auditor._reviewed_profiles = lambda: updated
    manifest = auditor.generate(files)
    if manifest['source_sha256'] != profile['source_sha256']:
        raise ValueError('resource profile source inventory differs from current Native')
    return updated, manifest


def publish(profile_path, native, name, registry=None):
    registry = Path(registry or HERE / 'reviewed_resource_profiles.json').absolute()
    if not name or registry.is_symlink():
        raise ValueError('profile name required; registry must be a regular file')
    profile_path = Path(profile_path).resolve()
    profile_bytes = profile_path.read_bytes()
    files = native_files(native)
    lock = registry.with_suffix(registry.suffix + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        os.close(fd)
        original = registry.read_bytes() if registry.exists() else None
        entries = json.loads(original) if original is not None else {}
        if not isinstance(entries, dict):
            raise ValueError('resource profile registry must be an object')
        updated, manifest = prepare(json.loads(profile_bytes), files, entries, name, registry)
        output = (json.dumps(updated, ensure_ascii=False, indent=2) + '\n').encode()
        if profile_path.read_bytes() != profile_bytes or native_files(native) != files:
            raise ValueError('profile or Native changed during publication; no registry written')
        current = registry.read_bytes() if registry.exists() else None
        if current != original:
            raise ValueError('resource registry changed during publication; retry from current bytes')
        changed = original != output
        if changed:
            handle, filename = tempfile.mkstemp(prefix='.' + registry.name + '-', dir=registry.parent)
            temporary = Path(filename)
            with os.fdopen(handle, 'wb') as stream:
                stream.write(output)
                stream.flush()
                os.fsync(stream.fileno())
            if (registry.read_bytes() if registry.exists() else None) != original:
                raise ValueError('resource registry changed before replace')
            os.replace(temporary, registry)
        return {'profile': name, 'registry': str(registry), 'changed': changed,
                'registry_sha256': sha(output), 'resources': len(manifest['resources']),
                'portable': True, 'data_digest': updated[name].get('data_digest'),
                'scope': 'reviewed-profile update and static inventory; not game acceptance'}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--name', required=True)
    parser.add_argument('--registry', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(publish(args.profile, args.native, args.name, args.registry), ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
