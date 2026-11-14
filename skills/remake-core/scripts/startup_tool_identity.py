"""Exact startup observation identity projection, scoped away from delivery checks.

The baseline source is only read and parsed, never imported or executed. Any
unreviewed source, import, configuration, or helper seal uses the ordinary actual
fingerprint. This does not alter the global ledger or a runtime verdict.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import check_ledger as cl

_MANIFEST_SHA256 = 'a88547a9beb2f42f4edab6a2a38bb834f0018ed1e035f6c79453c0ed1301c6e1'
_SEAL = re.compile(rb"^_STARTUP_TOOL_IDENTITY_SHA256 = '([0-9a-f]{64})'$", re.M)
_BODY_SEAL = re.compile(rb"^_STARTUP_TOOL_IDENTITY_BODY_SHA256 = '([0-9a-f]{64})'$", re.M)
_MANIFEST_SEAL = re.compile(rb"^_MANIFEST_SHA256 = '([0-9a-f]{64})'$", re.M)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _path(root, rel):
    if (not isinstance(rel, str) or not rel or Path(rel).is_absolute()
            or '..' in rel.split('/') or '\\' in rel):
        raise ValueError('invalid startup identity dependency')
    path = root / rel
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError('startup identity dependency missing/linked')
    return path


def _legacy_engine_context(proof, native, project):
    if (not isinstance(proof, dict) or proof.get('schema') != 'native_startup_renderer.v1'
            or proof.get('producer') != 'real_browser_native_entry'
            or not isinstance(proof.get('binding'), dict)
            or not all(proof['binding'].get(k) for k in ('source_sha256', 'native_tree_sha256', 'web_tree_sha256', 'build_tag'))
            or native is None or project is None):
        raise ValueError('old startup identity needs its approved engine2/3 context')
    native, project = Path(native).resolve(), Path(project).resolve()
    if not native.is_dir() or not project.is_dir():
        raise ValueError('startup identity artifact context missing')
    if (project / 'docs/checks/creator1-compatibility.json').exists():
        raise ValueError('Creator1 compatibility scope never inherits the old startup identity')
    if any((native / name).exists() for name in ('cocos2d-js-min.js', 'cocos2d-js.js')):
        raise ValueError('root Creator1 engine cannot inherit engine2/3 startup identity')
    engines = []
    for row in proof.get('inputs', []):
        if not isinstance(row, dict):
            raise ValueError('startup proof inputs malformed')
        name = row.get('relative_path')
        if not isinstance(name, str) or Path(name).is_absolute() or '..' in name.split('/') or '\\' in name:
            raise ValueError('startup proof engine path is unsafe')
        base = Path(name).name
        # The existing adapter_fix engine-name rule also permits Creator md5Cache suffixes.
        engine2 = re.fullmatch(r'cocos/cocos2d-js(-min)?(\.[0-9a-f]{5,})?\.js', name) is not None
        engine3 = name.startswith('cocos-js/') and (base == 'cc.js' or base.startswith('_virtual_cc-') and base.endswith('.js'))
        if engine2 or engine3:
            path = native / name
            if not path.resolve().is_relative_to(native) or any(p.is_symlink() for p in [path, *path.parents] if p != native and p.is_relative_to(native)) or path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != row.get('sha256'):
                raise ValueError('original engine input differs from actual Native')
            engines.append((path, row['sha256']))
    if not engines:
        raise ValueError('no exact approved engine2/3 Native input')
    return engines


def _project(paths, *, proof=None, native=None, project=None):
    runtime_inputs = _legacy_engine_context(proof, native, project)
    root = Path(__file__).resolve().parent
    read_set = dict(runtime_inputs)
    def remember(path):
        data = path.read_bytes()
        value = _sha(data)
        if path in read_set and read_set[path] != value:
            raise ValueError('startup identity dependency changed while reading')
        read_set[path] = value
        return data
    manifest_path = _path(root, 'startup_tool_projection.json')
    raw = remember(manifest_path)
    if _sha(raw) != _MANIFEST_SHA256:
        raise ValueError('startup identity projection metadata changed')
    doc = json.loads(raw)
    if (doc.get('schema') != 'startup-original-tool-projection.v1'
            or doc.get('domain') != 'startup-original-observation-identity-only'):
        raise ValueError('unknown startup identity projection')
    supplied = [Path(p).resolve() for p in paths]
    if len(supplied) != len(set(supplied)) or any(not p.is_relative_to(root) for p in supplied):
        raise ValueError('startup identity seeds escape their shared root')
    names = sorted(p.relative_to(root).as_posix() for p in supplied)
    groups = [g for g in doc['groups'].values() if sorted(g['seeds']) == names]
    if len(groups) != 1:
        raise ValueError('projection is limited to two startup observation callers')
    group = groups[0]
    # Guard JSON/import compatibility material is not implicitly covered by a
    # familiar Python filename. Exact bytes are checked every time.
    for name, expected in doc['guards'].items():
        if _sha(remember(_path(root, name))) != expected:
            raise ValueError('startup identity guard/policy changed')
    helper_bytes = remember(Path(__file__))
    if len(_MANIFEST_SEAL.findall(helper_bytes)) != 1:
        raise ValueError('startup helper manifest seal format changed')
    helper_sha = _sha(helper_bytes)
    helper_body_sha = _sha(_MANIFEST_SEAL.sub(b"_MANIFEST_SHA256 = '<projection-manifest-sha256>'", helper_bytes))
    todo, seen, rows, observed = list(supplied), set(), [], {}
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        rel = path.relative_to(root).as_posix()
        expected = group['entries'].get(rel)
        if expected is None:
            raise ValueError('new startup tool/import is not reviewed')
        current = remember(_path(root, rel))
        projection = doc['projections'].get(rel)
        if projection:
            if projection['mode'] == 'sealed-caller':
                seals = _SEAL.findall(current)
                body_seals = _BODY_SEAL.findall(current)
                if (len(seals) != 1 or seals[0].decode() != helper_sha
                        or len(body_seals) != 1 or body_seals[0].decode() != helper_body_sha):
                    raise ValueError('startup caller helper seal changed')
                normalized = _SEAL.sub(b"_STARTUP_TOOL_IDENTITY_SHA256 = '<helper-sha256>'", current)
                if _sha(normalized) != projection['current_sha256']:
                    raise ValueError('startup caller body changed')
            elif projection['mode'] != 'exact-current' or _sha(current) != projection['current_sha256']:
                raise ValueError('reviewed startup dependency source changed')
            original = remember(_path(root, projection['source']))
            if (_sha(original) != projection['source_sha256']
                    or projection['source_sha256'] != expected['raw_sha256']):
                raise ValueError('startup baseline source changed')
            identity, import_source = expected['identity_sha256'], original
            if _sha(import_source) != expected['import_source_sha256']:
                raise ValueError('startup projected import source differs')
        else:
            if _sha(current) != expected['raw_sha256']:
                raise ValueError('actual startup validator/tool changed')
            identity, import_source = cl._tool_compat_source(path, current)
            if (identity != expected['identity_sha256']
                    or _sha(import_source) != expected['import_source_sha256']):
                raise ValueError('ledger original identity/import proof changed')
        observed[rel] = _sha(current)
        rows.append((path.name, identity))
        if path.suffix == '.py':
            for node in ast.walk(ast.parse(import_source)):
                modules = ([a.name for a in node.names] if isinstance(node, ast.Import)
                           else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                for name in modules:
                    target = path.parent / (name.replace('.', '/') + '.py')
                    if target.is_file():
                        todo.append(target.resolve())
    if set(observed) != set(group['entries']):
        raise ValueError('startup original dependency closure changed')
    # No pass survives an input changing during identity construction.
    for path, expected_sha in read_set.items():
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != expected_sha:
            raise ValueError('startup identity inputs/guards changed during consumption')
    # The absence of a new engine1 branch is an input too. Recheck its small
    # structural conditions after reading the sources; engine bytes are already
    # covered by the complete read-set above.
    if ((Path(project).resolve() / 'docs/checks/creator1-compatibility.json').exists()
            or any((Path(native).resolve() / name).exists() for name in ('cocos2d-js-min.js', 'cocos2d-js.js'))):
        raise ValueError('startup engine context changed during consumption')
    value = cl.sha(sorted(rows))
    if value != group['fingerprint']:
        raise ValueError('startup baseline fingerprint does not match original closure')
    return value


def fingerprint(paths, *, proof=None, native=None, project=None):
    """Use exact reviewed original identity only; unknown state retains real identity."""
    values = list(paths)
    try:
        return _project(values, proof=proof, native=native, project=project)
    except (ValueError, OSError, KeyError, TypeError, SyntaxError, UnicodeError):
        return cl.tool_fingerprint(values)
