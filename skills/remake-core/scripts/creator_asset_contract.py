"""Production-time Creator asset contracts; no game execution or PASS records."""
from __future__ import annotations

import json
from pathlib import Path
import re
import uuid


def module_meta(existing: bytes | None, relative_path: str) -> bytes:
    """Only for a producer-owned 2.x CommonJS module, never arbitrary user scripts."""
    if existing is None:
        data = {'ver': '1.0.5', 'uuid': str(uuid.uuid5(uuid.NAMESPACE_URL,
                'cocos-generated-module:' + relative_path)), 'subMetas': {}}
    else:
        try:
            data = json.loads(existing.decode('utf-8-sig'))
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError('invalid module metadata: ' + relative_path + '.meta') from error
        if not isinstance(data, dict) or not isinstance(data.get('uuid'), str) or not data['uuid']:
            raise ValueError('module metadata needs existing UUID: ' + relative_path + '.meta')
        if 'importer' in data or 'userData' in data:
            raise ValueError('2.x module producer cannot rewrite 3.x metadata: ' + relative_path)
    changed = data.get('isPlugin') is not False or data.get('loadPluginInEditor') is not False
    data.update(isPlugin=False, loadPluginInEditor=False)
    if existing is not None and not changed:
        return existing
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def validate_bundle_names(project, planned=()):
    """Reject names that would alias an engine bundle or overwrite another root.

    Read both legacy 2.x subpackages and current 2.x/3.x directory metadata.
    The caller resolves offending source configuration; no blind asset rename.
    """
    project = Path(project)
    roots = {}
    for path in sorted((project / 'assets').rglob('*.meta')):
        folder = path.with_name(path.name[:-5])
        if not folder.is_dir():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            continue  # Existing importer reports malformed files separately.
        if not isinstance(data, dict):
            continue
        user = data.get('userData') if isinstance(data.get('userData'), dict) else {}
        if not (data.get('isBundle') is True or user.get('isBundle') is True or data.get('isSubpackage') is True):
            continue
        directory = folder.relative_to(project).as_posix()
        name = data.get('bundleName') or user.get('bundleName') or data.get('subpackageName') or folder.name
        roots[directory] = name
    for item in planned:
        roots[item['directory']] = item['name']
    used = {}
    for directory, name in sorted(roots.items()):
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
            raise ValueError('nonportable bundle name at ' + directory + ': ' + repr(name))
        key = name.casefold()
        if key in {'main', 'internal'} or (key == 'resources' and directory != 'assets/resources'):
            raise ValueError('reserved engine bundle name %r at %s; map the directory and its actual loading calls before building' % (name, directory))
        if key in used and used[key] != directory:
            raise ValueError('duplicate bundle name %r at %s and %s' % (name, used[key], directory))
        used[key] = directory
    return roots
