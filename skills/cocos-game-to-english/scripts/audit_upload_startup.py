#!/usr/bin/env python3
"""Package startup closure plus registered entry host-boundary replay. No renderer/device claim."""
import json
import collections
import copy
import hashlib
import posixpath
import re
from pathlib import Path
import shutil
import subprocess


# Pure parse cache is process-local; it never caches a package/game verdict.
_PARSE_CACHE = collections.OrderedDict()
_PARSE_CACHE_LIMIT = 64

def parser_fingerprint():
    root = Path(__file__).parent
    return tuple(hashlib.sha256((root/name).read_bytes()).hexdigest()
                 for name in ('parse_package_requires.cjs','vendor/acorn.cjs'))

def parse_package_source(source, node, signature):
    key = (node, signature, hashlib.sha256(source).hexdigest())
    if key in _PARSE_CACHE:
        result = _PARSE_CACHE.pop(key)
        _PARSE_CACHE[key] = result
        return 0, '', copy.deepcopy(result), True
    proc = subprocess.run([node, str(Path(__file__).with_name('parse_package_requires.cjs'))],
                          input=source.decode('utf-8-sig', errors='strict'), text=True,
                          capture_output=True, timeout=60)
    parsed = json.loads(proc.stdout)
    valid = (isinstance(parsed,dict) and parsed.get('parser')=='acorn@8.15.0' and
             isinstance(parsed.get('dependencies'),list) and isinstance(parsed.get('dynamic'),list) and
             all(isinstance(x,dict) and isinstance(x.get('request'),str) and isinstance(x.get('kind'),str) and type(x.get('line')) is int for x in parsed['dependencies']) and
             all(isinstance(x,dict) and isinstance(x.get('kind'),str) and type(x.get('line')) is int for x in parsed['dynamic']))
    if proc.returncode == 0 and not valid:
        raise ValueError('invalid dependency parser report; no result cached')
    if proc.returncode == 0 and valid and not parsed.get('error'):
        _PARSE_CACHE[key] = copy.deepcopy(parsed)
        while len(_PARSE_CACHE)>_PARSE_CACHE_LIMIT:
            _PARSE_CACHE.popitem(last=False)
    return proc.returncode, proc.stderr, parsed, False


def audit_scene_components(document, path):
    errors = []
    def slots(value, node):
        if isinstance(value, list) and any(item is None for item in value):
            errors.append(f'null/corrupted Cocos component in {node}: {path}')
    if not isinstance(document, list):
        return errors
    # Editor/uncompressed serialized object arrays.
    for obj in document:
        if isinstance(obj, dict) and obj.get('__type__') == 'cc.Node':
            slots(obj.get('_components'), obj.get('_name', 'cc.Node'))
    # Cocos 3.8 compiled JSON: classes[3], masks[4], instances[5].
    if len(document) < 6 or document[0] != 1:
        return errors
    classes, masks, instances = document[3:6]
    if not all(isinstance(x, list) for x in (classes, masks, instances)):
        return errors
    for instance in instances:
        if not isinstance(instance, list) or not instance or type(instance[0]) is not int:
            continue
        try:
            mask = masks[instance[0]]
            cls = classes[mask[0]]
            if not isinstance(cls, list) or cls[0] != 'cc.Node':
                continue
            properties = cls[1]
            for offset, prop_index in enumerate(mask[1:-1], 1):
                if properties[prop_index] != '_components':
                    continue
                value = instance[offset]
                # Typed-array property stores its actual component slots at [0].
                if isinstance(value, list) and value:
                    first = value[0]
                    wrapped = (isinstance(first, list) and first and
                               (isinstance(first[0], list) or first[0] is None))
                    slots(first if wrapped else value, 'cc.Node')
        except (IndexError, TypeError):
            continue
    return errors


def audit_files(files):
    """files is a ZIP-root-relative {path: bytes}; no filesystem mutation."""
    errors, warnings, edges, dynamic = [], [], [], []
    parse_stats = {"cache_hits":0,"executed":0}
    signature = None
    entry_protocols = set()
    names = set(files)
    folded = {n.casefold(): n for n in names}

    def need(path, source):
        path = posixpath.normpath(path)
        if path.startswith('../') or path.startswith('/'):
            errors.append(f'path escapes package: {path} from {source}')
            return None
        choices = [path, path + '.js', path + '.json', path + '/index.js']
        for candidate in choices:
            if candidate in names:
                if not files[candidate] and (candidate == 'game.js' or
                        re.search(r'(?:cocos2d[^/]*|physics[^/]*)\.js$', candidate)):
                    errors.append(f'empty startup dependency: {candidate} from {source}')
                return candidate
        case = [folded[x.casefold()] for x in choices if x.casefold() in folded]
        errors.append(f'missing startup dependency: {path} from {source}' +
                      (f' (case mismatch: {case[0]})' if case else ''))
        return None

    pending = ['game.js']
    visited = set()
    for root in ('game.js', 'game.json', 'project.config.json'):
        need(root, 'package root')
    try:
        game = json.loads(files.get('game.json', b'{}'))
        subs = game.get('subpackages', game.get('subPackages', []))
        if not isinstance(subs, list):
            raise ValueError('subpackage list must be an array')
        subnames, roots = set(), set()
        for sub in subs:
            root, name = sub.get('root'), sub.get('name')
            if not isinstance(root, str) or not root or not isinstance(name, str) or not name:
                raise ValueError('subpackage root/name required')
            if name in subnames or root.rstrip('/') in roots:
                raise ValueError('duplicate subpackage name/root')
            subnames.add(name)
            roots.add(root.rstrip('/'))
            entry = need(root.rstrip('/') + '/game.js', 'game.json subpackages')
            if entry:
                pending.append(entry)
        settings = files.get('src/settings.js', b'').decode('utf-8-sig', errors='replace')
        match = re.search(r'\bsubpackages\s*:\s*(\[[^\]]*\])', settings)
        if match:
            try:
                listed = json.loads(match.group(1))
                if not set(listed).issubset(subnames):
                    errors.append('settings.js references undeclared game.json subpackages')
            except (ValueError, TypeError):
                warnings.append('settings subpackage expression needs runtime validation')
        match = re.search(r'\bjsList\s*:\s*(\[[^\]]*\])', settings)
        if match:
            try:
                for item in json.loads(match.group(1)):
                    target = need(posixpath.join('src', item), 'settings.js jsList')
                    if target:
                        pending.append(target)
            except (ValueError, TypeError):
                warnings.append('settings jsList expression needs runtime validation')
        launch = re.search(r'\blaunchScene\s*:\s*["\']([^"\']+)', settings)
        if launch and launch.group(1).startswith('db://'):
            scene_maps = []
            for n in names:
                if re.search(r'/(?:config(?:\.[\w-]+)?)\.json$', n):
                    try:
                        config = json.loads(files[n])
                        if isinstance(config, dict):
                            scene_maps.extend((config.get('scenes') or {}).keys())
                    except (ValueError, AttributeError, TypeError):
                        pass
            if launch.group(1) not in scene_maps:
                errors.append('launchScene not registered in packaged bundle configs: ' + launch.group(1))
        # Cocos2 compiled import packs are referenced by bundle config, not JS literals.
        # A registered scene can still be unusable if its actual JSON pack was removed.
        for n in names:
            if not re.search(r'/config(?:\.[\w-]+)?\.json$', n):
                continue
            try:
                config = json.loads(files[n])
            except ValueError:
                errors.append('invalid bundle configuration: ' + n)
                continue
            if not isinstance(config, dict) or not isinstance(config.get('importBase'), str):
                continue
            base = posixpath.dirname(n)
            for pack in (config.get('packs') or {}):
                prefix = posixpath.join(base, config['importBase'], pack[:2], pack)
                if not any(path.startswith(prefix + '.') and path.endswith(('.json', '.ccon', '.cconb')) for path in names):
                    errors.append('missing Cocos import pack: ' + prefix + ' from ' + n)
    except (ValueError, TypeError, AttributeError) as exc:
        errors.append('startup configuration: ' + str(exc))

    while pending:
        name = pending.pop()
        if name in visited or name not in files:
            continue
        visited.add(name)
        if name.endswith('.json'):
            try:
                json.loads(files[name])
            except ValueError:
                errors.append('invalid required JSON: ' + name)
            continue
        if not name.endswith(('.js', '.mjs', '.cjs')):
            continue
        node = shutil.which('node')
        if not node:
            errors.append('Node.js required for non-executing JS syntax/dependency parser')
            break
        try:
            if signature is None:
                signature = parser_fingerprint()
            code, stderr, parsed, reused = parse_package_source(files[name], node, signature)
            parse_stats['cache_hits' if reused else 'executed'] += 1
            if code or not isinstance(parsed,dict) or parsed.get('error'):
                errors.append('JS parse failed in ' + name + ': ' + str(parsed.get('error', stderr) if isinstance(parsed,dict) else 'invalid parser report'))
                continue
        except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
            errors.append('JS parser unavailable/invalid in ' + name + ': ' + str(exc))
            continue
        if name == 'game.js':
            entry_protocols = set(parsed.get('native_entry_protocols', []))
        dynamic.extend(dict(source=name, **site) for site in parsed['dynamic'])
        for dependency in parsed['dependencies']:
            request = dependency['request']
            path = posixpath.join(posixpath.dirname(name), request) if request.startswith('.') else request
            target = need(path, name)
            edges.append({'source': name, 'request': request, 'resolved': target,
                          'line': dependency['line'], 'kind': dependency['kind']})
            if target:
                pending.append(target)
    # Cocos 3 compiled scenes may serialize a missing script as a null component,
    # while the scene and every referenced file still exist. Inspect component slots,
    # never arbitrary null values (which are valid for optional asset properties).
    for path, content in files.items():
        if not path.endswith('.json') or '/import/' not in path:
            continue
        try:
            document = json.loads(content)
        except (ValueError, UnicodeError):
            continue
        errors.extend(audit_scene_components(document, path))
    # Registered exported entry family: execute actual namespace/receiver/data/WASM contracts.
    # Browser hosts that merge GameGlobal with globalThis cannot calibrate these cases.
    host_boundary = None
    entry = files.get('game.js', b'').decode('utf-8', errors='replace')
    # Registered capability-bridge fixtures belong to this protocol, not to
    # every game using common filenames. The known module identities retain
    # coverage of older entries whose first-error acknowledgement is missing.
    known_platforms = {
        '973d03c11f04848d5134d28ec591a6a5709bd821ad30550ee1e84fed476e5650',
        '285594096341a17f27090f081c0d1ac1bdba2c0cb6a1acba4d590e9e50128a8a',
    }
    platform_identity = hashlib.sha256(files.get('native-platform.js', b'')).hexdigest()
    entry_family = 'bamboo_native_host_v1' if ('bamboo_native_host_v1' in entry_protocols or platform_identity in known_platforms) else None
    if entry_family == 'bamboo_native_host_v1':
        try:
            node = shutil.which('node')
            if not node:raise ValueError('Node.js required for Native host-boundary probe')
            payload = {'files': {name: data.decode('utf-8') for name, data in files.items() if '/' not in name and name.endswith(('.js', '.json'))}}
            probe = subprocess.run([node, str(Path(__file__).with_name('probe_native_host_boundary.cjs')), '--stdin'], input=json.dumps(payload), capture_output=True, text=True, timeout=20)
            host_boundary = json.loads(probe.stdout)
            if not isinstance(host_boundary,dict) or host_boundary.get('schema')!='native_host_boundary.v1':
                raise ValueError('unexpected Native host-boundary report schema')
            rows=host_boundary.get('rows')
            rows_valid=isinstance(rows,list) and bool(rows) and all(isinstance(row,dict) and type(row.get('passed')) is bool for row in rows)
            if probe.returncode or host_boundary.get('passed') is not True or not rows_valid or any(not row['passed'] for row in rows):
                errors.append('Native host-boundary probe failed or returned inconsistent cases')
                if rows_valid:
                    errors.extend('Native host boundary: '+str(row.get('id','unknown'))+': '+str((row.get('error') or {}).get('message','failed')) for row in rows if not row['passed'])
        except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
            errors.append('Native host-boundary probe unavailable/invalid: '+str(exc))
    bootstrap_boundary = None
    if entry_family == 'bamboo_native_host_v1' and any(edge['source']=='game.js' and edge['resolved']=='native-diagnostics.js' for edge in edges):
        try:
            node = shutil.which('node')
            if not node:
                raise ValueError('Node.js required for Native bootstrap boundary probe')
            payload = {'files': {name: content.decode('utf-8') for name, content in files.items() if name.endswith(('.js', '.json'))}}
            run = subprocess.run([node, str(Path(__file__).with_name('probe_native_bootstrap.cjs')), '--stdin'], input=json.dumps(payload), capture_output=True, text=True, timeout=20)
            bootstrap_boundary = json.loads(run.stdout)
            rows = bootstrap_boundary.get('rows')
            if run.returncode or bootstrap_boundary.get('passed') is not True or not isinstance(rows,list) or len(rows)!=3 or any(row.get('passed') is not True for row in rows):
                errors.append('Native bootstrap first-error capture failed: diagnostic dependency missing/parse error must retain entry acknowledgement and original error; normal dispatch must work')
        except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
            errors.append('Native bootstrap probe unavailable/invalid: '+str(exc))
    touch_coordinates = None
    adapter = files.get('adapter-min.js', b'').decode('utf-8', errors='replace')
    engine = files.get('cocos/cocos2d-js-min.js', b'').decode('utf-8', errors='replace')
    if 'tt.onTouchStart' in adapter and 'getTouchesByEvent:function(' in engine:
        try:
            node = shutil.which('node')
            if not node:
                raise ValueError('Node.js required for Cocos touch-coordinate probe')
            names = ('game.js', 'adapter-min.js', 'touch-coordinates.js', 'tiktok-touch-bridge.js', 'cocos/cocos2d-js-min.js')
            payload = {'files': {name: files[name].decode('utf-8') for name in names if name in files}}
            run = subprocess.run([node, str(Path(__file__).with_name('probe_cocos2_touch_coordinates.cjs'))], input=json.dumps(payload), capture_output=True, text=True, timeout=20)
            touch_coordinates = json.loads(run.stdout)
            if run.returncode or touch_coordinates.get('schema') != 'cocos2_touch_coordinates.v1' or touch_coordinates.get('passed') is not True:
                errors.append('Cocos2 native touch coordinates rejected: SDK screenX/screenY must reach finite engine coordinates')
        except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
            errors.append('Cocos2 native touch-coordinate probe unavailable: ' + str(exc))
    if dynamic:
        warnings.append('dynamic require sites are not proven by static closure; execute actual Native startup')
    return {'tool': 'audit_upload_startup', 'policy_version': 1, 'passed': not errors,
            'errors': sorted(set(errors)), 'warnings': sorted(set(warnings)),
            'reachable_files': sorted(visited), 'require_edges': edges, 'dynamic_requires': dynamic,
            'native_host_boundary': host_boundary, 'bootstrap_boundary': bootstrap_boundary, 'touch_coordinates': touch_coordinates, 'js_parse_reuse': parse_stats,
            'coverage': 'literal CommonJS startup graph, Cocos2 jsList/launch registration, declared subpackage entries; registered entry host-boundary fixtures',
            'not_verified': ['dynamic resource paths', 'actual renderer/parser/SDK', 'account/region/network', 'platform acceptance']}
