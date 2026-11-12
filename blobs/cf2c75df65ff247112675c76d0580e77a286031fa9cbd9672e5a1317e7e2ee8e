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
                 for name in ('parse_package_requires.cjs','vendor/acorn.cjs','scan_platform_input_bindings.cjs'))

def parse_package_source(source, node, signature):
    key = (node, signature, hashlib.sha256(source).hexdigest())
    if not source.strip():
        # 简化.11.14: an empty JavaScript file (a custom subpackage's placeholder game.js) has no requires; the parser
        # (生成时预防 J1 批) answers empty stdin with not_run, which is for a person running it with no input.
        return 0, '', {'dependencies': [], 'dynamic': [], 'bundle_internal_requires': 0, 'parser': 'acorn@8.15.0',
                        'native_entry_protocols': []}, False
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


def audit_cocos2_resources(files, settings, engine_subpackages, subpackage_roots, forced_by, uses_kit, edges):
    """Check the resources entry selected by the Cocos 2.4 ByteDance adapter."""
    flag = re.search(r"""\bhasResourcesBundle["']?\s*:\s*(true|false|!\s*[01])\s*[,}]""", settings)
    declared = flag and re.sub(r'\s+', '', flag.group(1)) in ('true', '!0')
    if flag and not declared:
        if 'resources' in engine_subpackages:
            return ['Cocos2 resources: hasResourcesBundle=false conflicts with settings.js subpackages containing resources']
        if forced_by:
            return [f'Cocos2 resources: {forced_by} loads assets/resources/index.js despite '
                    'hasResourcesBundle=false; skip the resources load when the bundle is absent']
        return []
    if not declared and not (uses_kit or forced_by):
        return []
    remote = re.search(r"""\bremoteBundles["']?\s*:\s*(\[[^\]]*\])""", settings)
    if remote and 'resources' not in engine_subpackages:
        try:
            if 'resources' in json.loads(remote.group(1)):
                # The package does not contain the remote config.
                return []
        except (TypeError, ValueError):
            pass
    if 'resources' in engine_subpackages:
        base = 'subpackages/resources'
        if subpackage_roots.get('resources') != base:
            return ['Cocos2 resources: settings.js expects game.json to declare resources at subpackages/resources']
        entry = base + '/game.js'
    else:
        base = 'assets/resources'
        entry = base + '/index.js'
    version_map = re.search(r"""\bbundleVers["']?\s*:\s*\{([^}]*)\}""", settings)
    version = version_map and re.search(r"""\bresources["']?\s*:\s*["']([\w-]+)["']""", version_map.group(1))
    config = base + ('/config.' + version.group(1) + '.json' if version else '/config.json')
    errors = ['Cocos2 resources: missing startup dependency: ' + path
              for path in (entry, config) if path not in files]
    if base == 'assets/resources' and entry in files and not any(
            edge['source'] == 'ccRequire.js' and edge['resolved'] == entry for edge in edges):
        errors.append('Cocos2 resources: ccRequire.js does not register ' + entry)
    return errors


def audit_adapter_preconditions(files):
    """Reject known unsafe Cocos2 startup assumptions before accepting an artifact.

    Writers normalize these forms before this read-only audit. Legacy or renamed
    candidates do not turn the three known defects into verified compatibility.
    This is a static prerequisite, not an iOS/device or first-frame verdict.
    """
    from package_gates.adapter_fix import detect
    state = detect(files)
    old = sorted(name for name, status in state.get('rules', {}).items() if status == 'old')
    return {**state, 'passed': not old, 'known_unsafe': old,
            'errors': ['Cocos2 startup adapter normalization missing: ' + ', '.join(old)] if old else [],
            'boundary': 'Known adapter prerequisites only; actual first-frame and device failure remain separate.'}


def audit_files(files):
    """files is a ZIP-root-relative {path: bytes}; no filesystem mutation."""
    errors, warnings, edges, dynamic = [], [], [], []
    adapter_preconditions = audit_adapter_preconditions(files)
    errors.extend(adapter_preconditions['errors'])
    parse_stats = {"cache_hits":0,"executed":0}
    signature = None
    entry_protocols = set()
    platform_input_bindings, platform_input_unresolved = [], []
    startup_modules, startup_imports = {}, {}
    settings = files.get('src/settings.js', b'').decode('utf-8-sig', errors='replace')
    engine_subpackages, subpackage_roots = set(), {}
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
        roots = set()
        for sub in subs:
            root, name = sub.get('root'), sub.get('name')
            if not isinstance(root, str) or not root or not isinstance(name, str) or not name:
                raise ValueError('subpackage root/name required')
            if name in subpackage_roots or root.rstrip('/') in roots:
                raise ValueError('duplicate subpackage name/root')
            root = root.rstrip('/')
            subpackage_roots[name] = root
            roots.add(root)
            entry = need(root + '/game.js', 'game.json subpackages')
            if entry:
                pending.append(entry)
        match = re.search(r"""\bsubpackages["']?\s*:\s*(\[[^\]]*\])""", settings)
        if match:
            try:
                listed = json.loads(match.group(1))
                engine_subpackages = set(listed)
                if not engine_subpackages.issubset(subpackage_roots):
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
        input_scan = parsed.get('platform_input_bindings') or {}
        for finding in input_scan.get('findings', []):
            platform_input_bindings.append(dict(source=name, **finding))
            errors.append('Cocos platform input binding skipped: %s:%s [%s] %s; missing when %s' %
                          (name, finding['line'], finding['id'], finding['event'],
                           json.dumps(finding['missing_when'], sort_keys=True)))
        for finding in input_scan.get('unresolved', []):
            platform_input_unresolved.append(dict(source=name, **finding))
            warnings.append('Cocos platform input binding needs runtime review: %s:%s (%s)' %
                            (name, finding['line'], finding['reason']))
        startup_modules[name] = {key: parsed.get(key) for key in
                                 ('startup24_resources', 'global_boot_assignments', 'calls_global_boot',
                                  'direct_startup_resources', 'direct_boot_resources')}
        immediate_requires = set(parsed.get('startup_requires', ()))
        dynamic.extend(dict(source=name, **site) for site in parsed['dynamic'])
        for dependency in parsed['dependencies']:
            request = dependency['request']
            path = posixpath.join(posixpath.dirname(name), request) if request.startswith('.') else request
            target = need(path, name)
            edges.append({'source': name, 'request': request, 'resolved': target,
                          'line': dependency['line'], 'kind': dependency['kind']})
            if target:
                pending.append(target)
                if dependency['kind'] == 'require' and request in immediate_requires:
                    startup_imports.setdefault(name, set()).add(target)
    # Follow only immediate imports from the platform entry here. The full closure above also
    # contains delayed subpackage entries and helpers that may never run on cold startup.
    eager = set()
    pending = ['game.js']
    while pending:
        name = pending.pop()
        if name not in eager:
            eager.add(name)
            pending.extend(startup_imports.get(name, ()))
    def is_cocos2_adapter(name):
        content = files.get(name, b'')
        return all(marker in content for marker in (b'__cocos_require__', b'subpackages/', b'assets/'))

    adapter_loaded = any(is_cocos2_adapter(name) for name in eager - {'game.js', 'src/settings.js'})
    standard_layout = {'src/settings.js', 'main.js', 'adapter-min.js'}.issubset(visited) and \
        is_cocos2_adapter('adapter-min.js')
    if ('src/settings.js' in eager and adapter_loaded) or standard_layout:
        startup_entries = {name: startup_modules.get(name, {}) for name in sorted(eager)}
        boot_count = sum(entry.get('global_boot_assignments') or 0 for entry in startup_entries.values())
        invokes_boot = boot_count == 1 and any(entry.get('calls_global_boot') for entry in startup_entries.values())
        forced_by = None
        uses_kit = False
        for name, entry in startup_entries.items():
            kit = entry.get('startup24_resources') if invokes_boot else None
            if kit == 'unconditional':
                forced_by = f'startup24 in {name}'
                break
            uses_kit = uses_kit or kit == 'skip_explicitly_absent'
            if entry.get('direct_startup_resources') or (invokes_boot and entry.get('direct_boot_resources')):
                forced_by = f'startup code in {name}'
                break
        if standard_layout and boot_count <= 1 and not forced_by:
            # Retain the standard template check when game.js invokes its known boot via a wrapper.
            standard_kit = startup_modules.get('main.js', {}).get('startup24_resources')
            if standard_kit == 'unconditional':
                forced_by = 'startup24 in main.js'
            uses_kit = uses_kit or standard_kit == 'skip_explicitly_absent'
        errors.extend(audit_cocos2_resources(files, settings, engine_subpackages, subpackage_roots,
                                            forced_by, uses_kit, edges))
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
    # Release builds ship cocos/cocos2d-js-min.js; debug builds (MergeShot2048 v82) ship cocos/cocos2d-js.js.
    engine_candidates = [n for n in files if re.search(r'(?:^|/)cocos/cocos2d-js(?:-min)?\.js$', n)
                         and re.search(rb'getTouchesByEvent\s*:\s*function\b', files[n])]
    engine_name = next((n for n in ('cocos/cocos2d-js-min.js', 'cocos/cocos2d-js.js') if n in engine_candidates),
                       engine_candidates[0] if len(engine_candidates) == 1 else 'cocos/cocos2d-js-min.js')
    engine = files.get(engine_name, b'').decode('utf-8', errors='replace')
    touch_converter = re.search(r'getTouchesByEvent\s*:\s*function\b', engine) is not None
    # TikTok gives touches only screenX/screenY; Cocos 2.4 reads clientX/clientY, so every legacy-converter build
    # is probed, whatever its adapter looks like. Browser emulation supplies clientX and cannot reveal the defect.
    if touch_converter:
        try:
            node = shutil.which('node')
            if not node:
                raise ValueError('Node.js required for Cocos touch-coordinate probe')
            # Root scripts carry the install line, the adapter and any SDK touch wrapper (tiktok-input.js or a
            # module game.js declares with '// tiktok-touch-adapter: ./name.js').
            names = sorted({n for n in files if '/' not in n and n.endswith('.js')} | {engine_name})
            payload = {'files': {name: files[name].decode('utf-8') for name in names if name in files}}
            run = subprocess.run([node, str(Path(__file__).with_name('probe_cocos2_touch_coordinates.cjs'))], input=json.dumps(payload), capture_output=True, text=True, timeout=20)
            touch_coordinates = json.loads(run.stdout)
            if run.returncode or touch_coordinates.get('schema') != 'cocos2_touch_coordinates.v1' or touch_coordinates.get('passed') is not True:
                failed = [str(row.get('id')) + ' expected ' + str(row.get('expected')) +
                          ', observed ' + str(row.get('observed'))
                          for row in touch_coordinates.get('rows', []) if row.get('passed') is not True]
                reason = touch_coordinates.get('error') or '; '.join(failed) or 'probe did not pass'
                errors.append('Cocos2 native touch coordinates rejected: SDK screenX/screenY must reach finite engine coordinates'
                              + ' (' + str(reason) + ')')
        except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
            errors.append('Cocos2 native touch-coordinate probe unavailable: ' + str(exc))
    # Cocos 3.x reads clientX/clientY in its minigame TouchInputSource through its own copy of `tt`. Run the
    # package's real game.js -> web-adapter.js prefix with SDK touches that carry only the documented
    # identifier/screenX/screenY/force fields, then the engine's own callbacks (probe_cocos3_touch_coordinates.cjs).
    # Its Vec2 turns NaN into 0, so the probe requires the tapped point, not just a finite on-screen value.
    touch_probed = touch_converter
    root_scripts = [n for n in files if '/' not in n and n.endswith('.js')]
    tiktok = any(re.search(rb'\btt\s*\.\s*[A-Za-z_$]|\bTTMinis\b', files[n]) for n in root_scripts)
    cocos3_engine = next((n for n in sorted(files) if n.startswith('cocos-js/') and n.endswith('.js')
                          and re.search(rb'\.onTouchStart\(this\.(?:_ccprivate\$)?_createCallback\(', files[n])), None)
    # Creator 3.8.8 command-line builds mangle engine private names to _ccprivate$_createCallback (ccbuild
    # mangleProperties); delivered R4/R6 packages keep _createCallback. Both are the same engine touch source.
    if touch_coordinates is None and cocos3_engine and (tiktok or 'web-adapter.js' in files):
        touch_probed = True
        try:
            node = shutil.which('node')
            if not node:
                raise ValueError('Node.js required for Cocos 3 touch-coordinate probe')
            prefix_files = {n: files[n].decode('utf-8', errors='replace') for n in files
                            if n.endswith(('.js', '.json')) and not n.startswith(('assets/', 'subpackages/', 'cocos-js/', 'src/'))}
            payload = {'files': prefix_files, 'engine': files[cocos3_engine].decode('utf-8', errors='replace')}
            run = subprocess.run([node, str(Path(__file__).with_name('probe_cocos3_touch_coordinates.cjs'))],
                                 input=json.dumps(payload), capture_output=True, text=True, timeout=60)
            touch_coordinates = json.loads(run.stdout)
            if not isinstance(touch_coordinates, dict):
                raise ValueError('unexpected Cocos 3 touch probe report')
            if run.returncode or touch_coordinates.get('schema') != 'cocos3_touch_coordinates.v1' or touch_coordinates.get('passed') is not True:
                rows = touch_coordinates.get('rows') if isinstance(touch_coordinates.get('rows'), list) else []
                failed = ['%s expected (%s, %s), engine received %s (raw location %s)' % (
                              r.get('id'), (r.get('expected') or {}).get('x'), (r.get('expected') or {}).get('y'),
                              [(t.get('x'), t.get('y')) for t in r.get('observed', [])],
                              [(t.get('x'), t.get('y')) for t in r.get('raw_location', [])])
                          for r in rows if isinstance(r, dict) and r.get('passed') is not True]
                reason = touch_coordinates.get('error') or '; '.join(failed) or 'probe did not pass'
                errors.append('Cocos3 native touch coordinates rejected: SDK identifier/screenX/screenY/force touches must reach '
                              'finite in-screen engine coordinates at the tapped point through game.js -> web-adapter.js (' + str(reason) + ')')
        except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
            errors.append('Cocos3 native touch-coordinate probe unavailable: ' + str(exc))
    # A TikTok Cocos package must prove its touch coordinates; a missing probe result is never a pass.
    cocos_package = any(n.startswith(('cocos/', 'cocos-js/')) or n in ('adapter-min.js', 'web-adapter.js', 'engine-adapter.js',
                                                                     'src/settings.js', 'src/settings.json') for n in files)
    if not touch_probed and touch_coordinates is None and tiktok and cocos_package:
        errors.append('TikTok Cocos package touch coordinates unverified: engine touch converter not recognised (neither the '
                      'Cocos 2.x getTouchesByEvent in cocos/cocos2d-js-min.js nor the Cocos 3.x minigame TouchInputSource in '
                      'cocos-js/*.js was found), so SDK screenX/screenY cannot be proven to reach the engine')
    if dynamic:
        warnings.append('dynamic require sites are not proven by static closure; execute actual Native startup')
    return {'tool': 'audit_upload_startup', 'policy_version': 2, 'passed': not errors,
            'errors': sorted(set(errors)), 'warnings': sorted(set(warnings)),
            'reachable_files': sorted(visited), 'require_edges': edges, 'dynamic_requires': dynamic,
            'adapter_preconditions': adapter_preconditions, 'native_host_boundary': host_boundary, 'bootstrap_boundary': bootstrap_boundary, 'touch_coordinates': touch_coordinates, 'js_parse_reuse': parse_stats,
            'platform_input_bindings': {'findings': platform_input_bindings, 'unresolved': platform_input_unresolved},
            'coverage': 'literal CommonJS startup graph, Cocos2 jsList/launch/resources registration and provable startup loads, declared subpackage entries; registered entry host-boundary fixtures; Cocos 2.x/3.x TikTok SDK touch-coordinate probes; legacy-flag skipped common node input bindings in Cocos2 lifecycle methods',
            'not_verified': ['dynamic resource paths', 'actual renderer/parser/SDK', 'platform flags outside checked Cocos2 lifecycle paths', 'account/region/network', 'platform acceptance']}
