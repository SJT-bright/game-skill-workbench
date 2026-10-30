"""Derive finite Cocos requests from production JS, then refuse incomplete manifests.
Unknown dynamic domains/method escapes fail closed; this never plays levels.
v7.7 W-G2: the platform-kit main.js (bytes listed in KIT_MANIFEST.json) loads settings.jsList with
cc.assetManager.loadScript; that one call becomes required script files (script_files), never a waived request.
"""
import argparse
import copy
import hashlib
import json
import posixpath
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from contextvars import ContextVar
from functools import wraps

HERE = Path(__file__).resolve().parent
_CACHE = {}
_RESOURCE_PROJECT = ContextVar('resource_project', default=None)
# v7.7 W-G2: the platform-kit main.js is recognised by the hashes KIT_MANIFEST.json lists at run time (current and
# previous_sha256); tests point this at a copy.
KIT_MANIFEST = HERE.parent / 'assets' / 'platform-kit' / 'KIT_MANIFEST.json'
# The one loader call of the kit main.js that is script loading: every settings.jsList entry, as 'src/' + entry.
KIT_JSLIST_CALL = re.compile(r"cc\.assetManager\.loadScript\(\(settings\.jsList \|\| \[\]\)\.map\(function \(x\) \{\s*"
                             r"return 'src/' \+ x;\s*\}\)")

def resource_profile_file(name):
    import project_qa
    return project_qa.resource_profile_path(_RESOURCE_PROJECT.get(), name)

def project_context(function):
    @wraps(function)
    def wrapped(*args, project=None, **kwargs):
        token = _RESOURCE_PROJECT.set(project)
        try:return function(*args, **kwargs)
        finally:_RESOURCE_PROJECT.reset(token)
    return wrapped



def _catalogs(files):
    catalogs = {}
    for name, content in files.items():
        if not re.search(r'(^|/)config(?:\.[0-9a-fA-F]+)?\.json$', name):
            continue
        try:
            config = json.loads(content)
        except (ValueError, UnicodeError):
            continue
        if not isinstance(config, dict) or not isinstance(config.get('paths'), dict):
            continue
        bundle = config.get('name') or PurePosixPath(name).parent.name
        types = config.get('types', [])
        if not isinstance(bundle, str) or not bundle or not isinstance(types, list) or any(not isinstance(t, str) or not t for t in types):
            raise ValueError('invalid bundle name/types: ' + name)
        for row in config['paths'].values():
            if not isinstance(row, list) or len(row) < 2 or not isinstance(row[0], str):
                raise ValueError('invalid bundle resource entry: ' + name)
            # Cocos 2.4 debug catalogs store the class name directly; compact catalogs use types indexes.
            if isinstance(row[1], str) and re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$.]*', row[1]):
                resource_type = row[1]
            elif type(row[1]) is int and 0 <= row[1] < len(types):
                resource_type = types[row[1]]
            else:
                raise ValueError('invalid bundle resource type: ' + name)
            catalogs.setdefault(bundle, set()).add((row[0], resource_type))
    return catalogs


def _domain(value):
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return [value]
    if isinstance(value, list):
        return {'table': [_domain(x) for x in value]}
    if isinstance(value, dict):
        return {'table': {k: _domain(v) for k, v in value.items()}}
    return None


def _reviewed_profiles():
    path = resource_profile_file('reviewed_resource_profiles.json')
    return json.loads(path.read_text()) if path.is_file() else {}


def _serialized_asset_data_hashes(files):
    hashes = {}
    for name, content in files.items():
        if not name.endswith('.json') or b'cc.JsonAsset' not in content:
            continue
        try:
            value = json.loads(content)
        except ValueError:
            continue
        if isinstance(value, list):
            hashes[name] = hashlib.sha256(content).hexdigest()
    return hashes


def _matching_reviewed_profiles(files, source_hashes):
    matching = []
    for profile in _reviewed_profiles().values():
        if profile.get('source_sha256') != source_hashes:
            continue
        if 'profile_ref' in profile:
            ref = profile['profile_ref']; local = Path(ref['path'])
            if not local.is_absolute():
                if '..' in local.parts:
                    raise ValueError('unsafe reviewed resource profile reference')
                local = resource_profile_file('reviewed_resource_profiles.json').parent / local
            if not local.is_file() or hashlib.sha256(local.read_bytes()).hexdigest() != ref.get('sha256'):
                raise ValueError('reviewed project resource profile changed or missing')
            reviewed = json.loads(local.read_text())
            if reviewed.get('source_sha256') != source_hashes:
                raise ValueError('reviewed project profile source identity differs')
            profile = reviewed
        if 'data_digest_kind' in profile:
            if profile['data_digest_kind'] != 'serialized-json-assets-v1':
                raise ValueError('unsupported reviewed resource data fingerprint')
            data_digest = hashlib.sha256(json.dumps(_serialized_asset_data_hashes(files), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            if data_digest != profile.get('data_digest'):
                continue
        matching.append(profile)
    return matching


def _profile_data_hashes(files, source_hashes):
    hashes = {}
    for profile in _matching_reviewed_profiles(files, source_hashes):
        if 'data_digest' in profile:
            hashes['serialized-json-assets-v1'] = profile['data_digest']
        for domain in profile.get('data_domains', {}).values():
            name = domain['path']
            hashes[name] = hashlib.sha256(files[name]).hexdigest() if name in files else None
    return hashes


def _resolve_reviewed_data(profile, resolution, files):
    domain_name = resolution.get('data_domain')
    if not domain_name:
        return resolution
    domain = profile.get('data_domains', {}).get(domain_name)
    if not isinstance(domain, dict) or domain.get('kind') != 'mira-cosmetics-unlock-v1':
        raise ValueError('unsupported reviewed resource data domain')
    name = domain.get('path', '')
    if not name or name not in files or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
        raise ValueError('reviewed resource data source missing/unsafe: '+name)
    data = json.loads(files[name])
    rows = data[5] if isinstance(data, list) and len(data) > 5 else []
    matches = [row[2] for row in rows if isinstance(row, list) and len(row) > 2 and row[1] == domain['asset_name']]
    if len(matches) != 1 or not isinstance(matches[0], dict) or not isinstance(matches[0].get('items'), list):
        raise ValueError('reviewed cosmetics data asset missing/ambiguous')
    paths = []
    for item in matches[0]['items']:
        ident = item.get('id') if isinstance(item, dict) else None
        if not isinstance(ident, str) or not re.fullmatch(r'(?:hero|bg)_[A-Za-z0-9_]+', ident):
            raise ValueError('invalid reviewed cosmetics ID: '+str(ident))
        if ident in paths:
            raise ValueError('duplicate reviewed cosmetics ID: '+ident)
        paths.append(ident)
    # Defaults are already loaded by the production resources.loadDir call;
    # loadEquipped filters these exact two IDs before requesting cosmetics.
    paths = sorted(p for p in paths if p not in ('hero_01', 'bg_01'))
    if not paths:
        raise ValueError('reviewed cosmetics request domain is empty')
    return dict(resolution, paths=paths)


def apply_reviewed_profile(report, files):
    """Exact-inventory finite domains; any changed/new JS falls back to strict discovery."""
    profiles = _reviewed_profiles()
    if not profiles:
        return report
    matching = _matching_reviewed_profiles(files, report['source_sha256'])
    if not matching:
        return report
    if len(matching) != 1:
        raise ValueError('ambiguous reviewed resource profile')
    profile = matching[0]
    sites = {r['id']: r for r in report['sites']}
    escapes = {r['id']: r for r in report['escapes']}
    if not set(profile['resolutions']).issubset(sites) or not set(profile['escapes']).issubset(escapes):
        raise ValueError('reviewed profile does not match independent call inventory')
    report['reviewed_resolutions'] = []
    for ident, resolution in profile['resolutions'].items():
        resolution = _resolve_reviewed_data(profile, resolution, files)
        if not resolution.get('reason'):
            raise ValueError('reviewed resource domain lacks rationale')
        if 'local_method' in resolution:
            local=resolution['local_method']
            if not isinstance(local,dict) or set(local)!={'source','start','end','sha256','delegate_sites'}:
                raise ValueError('reviewed local method requires exact body identity and delegated inventory')
            source=local['source'];start=local['start'];end=local['end']
            if source not in files or type(start)is not int or type(end)is not int or not 0<=start<end<=len(files[source]):
                raise ValueError('reviewed local method body range invalid')
            body=files[source][start:end]
            if hashlib.sha256(body).hexdigest()!=local['sha256'] or not body.startswith(b'function'):
                raise ValueError('reviewed local method body changed')
            delegated={r['id'] for r in report['sites'] if r.get('source')==source and start<=int(r['id'].rsplit(':',1)[1])<end}
            if not isinstance(local['delegate_sites'],list) or delegated!=set(local['delegate_sites']):
                raise ValueError('reviewed local method lost independent body-call inventory')
            sites.pop(ident)
        elif resolution.get('not_executed') or resolution.get('delegated_sdk'):
            sites.pop(ident)
        elif 'native_files' in resolution:
            sites.pop(ident)
        elif 'requests' in resolution:
            if set(resolution) != {'reason', 'requests'} or not isinstance(resolution['requests'], list) or not resolution['requests']:
                raise ValueError('reviewed requests requires only reason and nonempty explicit tuples')
            seen = set()
            for request in resolution['requests']:
                if not isinstance(request, dict) or set(request) != {'bundle', 'path', 'type', 'kind'} or any(not isinstance(request[k], str) or not request[k] for k in request) or request['kind'] not in ('load', 'loadRes', 'loadDir'):
                    raise ValueError('invalid reviewed request tuple')
                key = tuple(request[k] for k in ('bundle', 'path', 'type', 'kind'))
                if key in seen:
                    raise ValueError('duplicate reviewed request tuple')
                seen.add(key)
            sites[ident] = dict(sites[ident], reviewed_requests=resolution['requests'])
        else:
            sites[ident] = dict(sites[ident], **{k:v for k,v in resolution.items() if k != 'reason'})
        report['reviewed_resolutions'].append(dict(id=ident, **resolution))
    for ident in profile['escapes']:
        escapes.pop(ident)
    report['sites'] = list(sites.values())
    report['escapes'] = list(escapes.values())
    return report


def kit_main_identity():
    """The kit main.js as KIT_MANIFEST.json describes it, read on every call (W-G1 may change main.js): its sha256
    values (files["build-templates/bytedance/main.js"] and every 2.4 part whose file lands at main.js, each with its
    previous_sha256) and the files that part always ships next to it (extra_files, e.g. webp-decode-probe.js).
    An unreadable manifest recognises nothing, so the jsList call stays an unsupported loader call."""
    try:
        manifest = json.loads(Path(KIT_MANIFEST).read_bytes())
    except (OSError, ValueError, UnicodeError):
        return {'hashes': [], 'extra_files': []}
    hashes, extras = set(), set()

    def add(spec):
        if not isinstance(spec, dict):
            return
        for digest in [spec.get('sha256')] + list(spec.get('previous_sha256') or []):
            if isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest):
                hashes.add(digest)
    files = manifest.get('files') if isinstance(manifest.get('files'), dict) else {}
    add(files.get('build-templates/bytedance/main.js'))
    parts = manifest.get('parts') if isinstance(manifest.get('parts'), dict) else {}
    for part in parts.values():
        if not isinstance(part, dict) or part.get('engine') != 2 or not isinstance(part.get('file'), dict) \
                or part['file'].get('dest') != 'main.js':
            continue
        add(part['file'])
        for extra in part.get('extra_files') or []:
            if isinstance(extra, dict) and isinstance(extra.get('dest'), str) and extra['dest']:
                extras.add(extra['dest'])
    return {'hashes': sorted(hashes), 'extra_files': sorted(extras)}


def _expand_kit_main_scripts(report, files, kit):
    """v7.7 W-G2: in the kit main.js (bytes equal to a KIT_MANIFEST hash) and nowhere else, the call
    cc.assetManager.loadScript((settings.jsList || []).map(x => 'src/' + x)) is script loading, not a resource
    request: each jsList entry becomes a required package file, and so does every kit extra file the kit main.js
    requires (webp-decode-probe.js). Any other main.js, any other loader call, a non-literal jsList, a second settings
    script, or a write to jsList / _CCSettings outside the kit main.js leaves the call unsupported, as before."""
    settings = report.pop('settings_js', None) or {}
    writes = [w for w in report.pop('settings_writes', None) or [] if w.get('source') != 'main.js']
    main = files.get('main.js')
    if main is None or hashlib.sha256(main).hexdigest() not in kit['hashes']:
        return report
    calls = [s for s in report['sites'] if s.get('source') == 'main.js' and s.get('kind') == 'unsupported'
             and KIT_JSLIST_CALL.match(s.get('expression') or '')]
    if len(calls) != 1:
        return report
    site, problem, paths = calls[0], None, []
    if len(settings) != 1:
        problem = 'expected one src/settings.js, found %s' % (sorted(settings) or 'none')
    else:
        (settings_name, row), = settings.items()
        if not isinstance(row.get('jsList'), list):
            problem = '%s: %s' % (settings_name, row.get('why') or 'jsList unreadable')
        elif writes:
            problem = 'settings jsList/_CCSettings written outside the kit main.js: ' + \
                '; '.join('%s:%s %s' % (w['source'], w['line'], w['expression'][:80]) for w in writes)
        else:
            for entry in row['jsList']:
                path = posixpath.normpath('src/' + entry)
                if not entry or entry.startswith('/') or '\\' in entry or not path.startswith('src/') or '..' in PurePosixPath(path).parts:
                    problem = 'unsafe settings.jsList entry: %r' % entry
                    break
                if path not in paths:
                    paths.append(path)
    if problem:
        site['kit_main_js'] = 'kit main.js jsList not expanded: ' + problem
        return report
    text = main.decode('utf-8-sig', errors='replace')
    rows = [{'id': site['id'], 'path': p, 'required_by': 'kit main.js cc.assetManager.loadScript(settings.jsList)'}
            for p in paths]
    for dest in kit['extra_files']:
        stem = re.escape(PurePosixPath(dest).with_suffix('').as_posix())
        if re.search(r"\brequire\(\s*(['\"])\./%s(?:\.js)?\1\s*\)" % stem, text) and dest not in paths:
            rows.append({'id': 'main.js:require:' + dest, 'path': dest, 'required_by': 'kit main.js require (KIT_MANIFEST extra_files)'})
    report['sites'] = [s for s in report['sites'] if s is not site]
    report['kit_main_js'] = {'sha256': hashlib.sha256(main).hexdigest(), 'settings': settings_name,
                             'jsList': row['jsList'], 'expanded_site': dict(site)}
    report['kit_script_files'] = rows
    return report


def _validate_current_files(report, files, *, systemjs):
    """Validate per-call Native data; only the parsed call inventory is cached."""
    for row in report.get('kit_script_files', []):
        path = row['path']
        if PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or not files.get(path):
            raise ValueError('kit main.js script file missing or empty: %s (%s)' % (path, row['required_by']))
        row['sha256'] = hashlib.sha256(files[path]).hexdigest()
    for row in report.get('finite_adapter', {}).get('native_file_sites', []):
        path = row['path']
        if path not in files or not files[path] or PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts:
            raise ValueError('declared local script missing/unsafe: '+path)
    if systemjs:
        for row in report.get('native_file_sites', []):
            rel = PurePosixPath(row['path'])
            if rel.is_absolute() or '..' in rel.parts or row['path'] not in files or not files[row['path']]:
                raise ValueError('literal Native resource file missing or unsafe: ' + row['path'])
            row['sha256'] = hashlib.sha256(files[row['path']]).hexdigest()
        for row in report.get('module_file_sites', []):
            rel = PurePosixPath(row['path'])
            if rel.is_absolute() or '..' in rel.parts or not files.get(row['path']):
                raise ValueError('SystemJS local module file missing/unsafe: ' + row['path'])
            row['sha256'] = hashlib.sha256(files[row['path']]).hexdigest()
        settings = json.loads(files['src/settings.json'])
        if settings.get('assets', {}).get('server') or settings.get('assets', {}).get('remoteBundles'):
            raise ValueError('remote SystemJS resource domains need their own finite adapter')
        for script in settings.get('scripting', {}).get('scriptPackages', []):
            if not script.startswith('project://') or script[len('project://'):] not in files:
                raise ValueError('nonlocal/missing SystemJS script package: ' + script)
    for resolution in report.get('reviewed_resolutions', []):
        if resolution.get('not_executed') or resolution.get('delegated_sdk'):
            continue
        for name in resolution.get('native_files', []):
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or not files.get(name):
                raise ValueError('reviewed literal Native file missing: '+name)
    return report


def discover(files):
    node = shutil.which('node')
    if not node:
        raise ValueError('Node.js required for production resource-call inventory')
    try:
        version = json.loads(files.get('src/settings.json', b'{}')).get('CocosEngine')
        systemjs = isinstance(version, str) and version.split('.')[0] == '3' and b'System.register' in files.get('cocos-js/cc.js', b'')
    except (ValueError, AttributeError):
        systemjs = False
    # Cocos's own loader internals are checked by startup/engine contracts.
    # All root/business bundle JS is inventoried, including scripts in subpackages.
    sources = {n: b for n, b in files.items() if n.endswith(('.js', '.mjs', '.cjs'))
               and not n.startswith(('cocos/', 'jsb-adapter/'))
               and not (systemjs and (n.startswith('cocos-js/') or n in ('engine-adapter.js', 'web-adapter.js')))}
    source_hashes = {n: hashlib.sha256(b).hexdigest() for n, b in sources.items()}
    payload = {'files': {n: b.decode('utf-8-sig') for n, b in sources.items()}, 'json_domains': {},
               'reviewed_data_sha256': _profile_data_hashes(files, source_hashes)}
    system_profile_path = resource_profile_file('systemjs_finite_profiles.json')
    system_profile_bytes = system_profile_path.read_bytes() if system_profile_path.is_file() else b''
    if systemjs and system_profile_bytes:
        source_digest = hashlib.sha256(json.dumps(source_hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        semantic_data = _serialized_asset_data_hashes(files)
        data_digest = hashlib.sha256(json.dumps(semantic_data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        matches = [p for p in json.loads(system_profile_bytes) if p.get('source_digest') == source_digest and p.get('data_digest_kind') == 'serialized-json-assets-v1' and p.get('data_digest') == data_digest]
        if len(matches) > 1:
            raise ValueError('ambiguous reviewed SystemJS profile')
        if matches:
            payload['systemjs_profile'] = matches[0]
    for name in sources:
        domains = {}
        requests = {m[1] for m in re.findall(r'\brequire\(\s*([\'"])(.*?)\1\s*\)', payload['files'][name])}
        for request in requests:
            if not request.startswith('.'):
                continue
            path = posixpath.normpath(posixpath.join(posixpath.dirname(name), request))
            path = path if path.endswith('.json') else path + '.json'
            if path not in files:
                continue
            try:
                value = _domain(json.loads(files[path]))
            except (ValueError, UnicodeError):
                continue
            domains[request] = value
        payload['json_domains'][name] = domains
    # Exact-program finite adapters cannot be enabled by an upload manifest.
    # Keep the independent generic inventory, then resolve only reviewed sites.
    profile_path = resource_profile_file('cocos2_finite_profiles.json')
    profile = None
    if not systemjs and profile_path.is_file():
        source_digest = hashlib.sha256(json.dumps({n: hashlib.sha256(b).hexdigest() for n, b in sources.items()}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        matches = [p for p in json.loads(profile_path.read_text()) if p.get('source_digest') == source_digest]
        if len(matches) > 1:
            raise ValueError('ambiguous reviewed CommonJS resource profile')
        profile = matches[0] if matches else None
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    scanner = HERE / ('scan_systemjs_resources.cjs' if systemjs else 'scan_runtime_resources.cjs')
    tool_sha = hashlib.sha256(scanner.read_bytes() + ((HERE/'scan_runtime_resources.cjs').read_bytes() if systemjs else b'') + (HERE/'vendor/acorn.cjs').read_bytes()).hexdigest()
    finite_adapter = HERE/'scan_cocos2_finite_art.cjs'
    if profile:
        payload['asset_jsons'] = {n: b.decode('utf-8-sig') for n, b in files.items() if '/import/' in n and n.endswith('.json')}
        payload['catalogs'] = {k: sorted(v) for k, v in _catalogs(files).items()}
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        tool_sha = hashlib.sha256((tool_sha+hashlib.sha256(finite_adapter.read_bytes()+json.dumps(profile,sort_keys=True,separators=(',', ':')).encode()).hexdigest()).encode()).hexdigest()
    profile_path = resource_profile_file('reviewed_resource_profiles.json')
    profile_bytes = profile_path.read_bytes() if profile_path.is_file() else b''
    special = HERE / 'scan_systemjs_finite_art.cjs'
    special_bytes = special.read_bytes() if systemjs and payload.get('systemjs_profile') else b''
    if not systemjs:
        # Other games can publish profiles while this package runs its browser
        # probe. Fingerprint only profiles that can affect this program's result;
        # keep Native-file anchor refusals and matching-profile changes binding.
        relevant_profiles = _matching_reviewed_profiles(files, source_hashes)
        relevant_profiles += [p for p in _reviewed_profiles().values()
                              if p.get('native_manifest_kind') == 'native-files-v3'
                              and isinstance(p.get('anchor_source'), str)
                              and p['anchor_source'] in sources
                              and p not in relevant_profiles]
        profile_bytes = json.dumps(relevant_profiles, sort_keys=True, separators=(',', ':')).encode()
        system_profile_bytes = b''
        reviewed_digest = hashlib.sha256(profile_bytes).hexdigest()
    else:
        relevant_profiles = _matching_reviewed_profiles(files, source_hashes)
        relevant_profiles += [p for p in _reviewed_profiles().values() if p.get('native_manifest_kind') == 'native-files-v3' and p.get('anchor_source') in sources and p not in relevant_profiles]
        profile_bytes = json.dumps(relevant_profiles,sort_keys=True,separators=(',', ':')).encode()
        reviewed_digest = hashlib.sha256(profile_bytes).hexdigest()
        system_profile_bytes = json.dumps([payload['systemjs_profile']] if payload.get('systemjs_profile') else [],sort_keys=True,separators=(',', ':')).encode()
    kit = {'hashes': [], 'extra_files': []} if systemjs else kit_main_identity()
    tool_sha = hashlib.sha256(tool_sha.encode() + profile_bytes + system_profile_bytes + special_bytes + Path(__file__).read_bytes() + (HERE/'scan_native_file_requests.cjs').read_bytes()).hexdigest()
    if kit['hashes']:  # the kit main.js identity decides the jsList expansion, so it is part of the cache key
        tool_sha = hashlib.sha256((tool_sha + json.dumps(kit, sort_keys=True)).encode()).hexdigest()
    key = (node, tool_sha, hashlib.sha256(raw).hexdigest(), reviewed_digest)
    if key in _CACHE:
        return _validate_current_files(copy.deepcopy(_CACHE[key]), files, systemjs=systemjs)
    try:
        result = subprocess.run([node, str(scanner)], input=raw, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired as error:
        raise ValueError('resource inventory parser timed out; do not classify as a gameplay failure') from error
    try:
        report = json.loads(result.stdout)
    except ValueError as error:
        raise ValueError('resource-call parser did not return valid JSON') from error
    if result.returncode or report.get('error') or report.get('schema') != 'cocos_resource_sites.v1':
        raise ValueError('resource-call inventory refused: ' + str(report.get('error', result.stderr.decode(errors='replace'))))
    if profile:
        adapted_payload = dict(payload, profile=profile, generic=report)
        adapted = subprocess.run([node, str(finite_adapter)], input=json.dumps(adapted_payload).encode(), capture_output=True, timeout=30)
        if adapted.returncode:
            raise ValueError('reviewed CommonJS finite adapter refused: '+adapted.stderr.decode(errors='replace')[-2500:])
        resolution = json.loads(adapted.stdout)
        if resolution.get('schema') != 'cocos2_finite_resolution.v1':
            raise ValueError('invalid CommonJS finite resolution')
        original = {r['id']: r for r in report['sites']}
        used = set()
        for site in resolution['resolved_sites']:
            if site['id'] not in original or site['id'] in used:
                raise ValueError('finite adapter lost independent production call coverage')
            original[site['id']] = site
            used.add(site['id'])
        for site in resolution['delegated_sites']:
            if site['id'] not in original or site['id'] in used:
                raise ValueError('invalid or duplicated delegated production call')
            original.pop(site['id'])
            used.add(site['id'])
        report['sites'] = list(original.values())
        report['finite_adapter'] = resolution
    if systemjs:
        roots = report.pop('root_files', None)
        if not isinstance(roots, dict) or set(roots) != set(payload['files']):
            raise ValueError('SystemJS inventory lacks exact root-script coverage')
        # Independently inventory the ORIGINAL business sources. A specialized
        # finite-domain adapter may resolve sites, but may not mask a module and
        # silently omit its unsupported resource calls.
        root_result = subprocess.run([node, str(HERE/'scan_runtime_resources.cjs')], input=raw, capture_output=True, timeout=30)
        root_report = json.loads(root_result.stdout)
        if root_result.returncode or root_report.get('error'):
            raise ValueError('SystemJS root inventory refused: ' + str(root_report))
        generic = {row['id']: row for row in root_report['sites']}
        for site in report['sites']:
            if site['id'] not in generic:
                raise ValueError('SystemJS adapter site lacks independent production coverage: ' + site['id'])
            generic[site['id']] = site
        for row in report.get('delegated_sites', []):
            if row['id'] not in generic:
                raise ValueError('SystemJS delegated call lacks independent production coverage')
            generic.pop(row['id'])
        for row in report.get('native_file_sites', []):
            if row['id'] not in generic:
                raise ValueError('Native file call lacks independent production coverage')
            generic.pop(row['id'])
        resolved_escapes = {r['id'] for r in report.get('owned_method_definitions', [])}
        resolved_escapes.update(r['id'] for r in report.get('module_handler_escapes', []))
        report['sites'] = list(generic.values())
        report['escapes'] += [r for r in root_report['escapes'] if r.get('id') not in resolved_escapes]
    # New native-file protocol is opt-in by an exact whole-business-program profile.
    # Other reviewed games keep all existing discovery branches unchanged.
    current_source_hashes = {n: hashlib.sha256(b).hexdigest() for n, b in sources.items()}
    native_profiles = [p for p in _matching_reviewed_profiles(files, current_source_hashes)
                       if p.get('native_manifest_kind') == 'native-files-v3']
    native_anchors = [p for p in _reviewed_profiles().values()
                      if p.get('native_manifest_kind') == 'native-files-v3'
                      and isinstance(p.get('anchor_source'), str)
                      and p['anchor_source'] in sources]
    if native_anchors and not native_profiles:
        raise ValueError('reviewed Native-file program changed; finite profile must be re-derived and reviewed')
    if len(native_profiles) > 1:
        raise ValueError('ambiguous Native-file finite profile')
    if native_profiles:
        native_scan = subprocess.run([node, str(HERE/'scan_native_file_requests.cjs')], input=raw, capture_output=True, timeout=30)
        if native_scan.returncode:
            raise ValueError('native file call inventory failed: '+native_scan.stderr.decode(errors='replace'))
        native_report = json.loads(native_scan.stdout)
        if native_report.get('schema') != 'cocos_native_file_sites.v1':
            raise ValueError('unknown native file inventory schema')
        existing_ids = {row['id'] for row in report['sites']}
        for site in native_report['sites']:
            if site['id'] in existing_ids:
                raise ValueError('duplicate native resource call site')
            report['sites'].append(dict(site, bundles=None, paths=None))
        report['native_file_inventory'] = native_report['sites']
    report['source_sha256'] = current_source_hashes
    report['scanner_sha256'] = tool_sha
    report = apply_reviewed_profile(report, files)
    # After the reviewed profile: a profile that already resolved the jsList call keeps its own resolution.
    report = _expand_kit_main_scripts(report, files, kit)
    checked = _validate_current_files(copy.deepcopy(report), files, systemjs=systemjs)
    _CACHE[key] = copy.deepcopy(report)
    return checked


def required_requests(files):
    catalogs = _catalogs(files)
    inventory = discover(files)
    unresolved = [dict(row, reason='resource loader method escaped static call inventory') for row in inventory['escapes']]
    required = set()
    for original_site in inventory['sites']:
        explicit = original_site.get('reviewed_requests')
        expanded = [dict(original_site, bundles=[r['bundle']], paths=[r['path']], type=r['type'], kind=r['kind'], unknown_receiver=False) for r in explicit] if explicit is not None else [original_site]
        for site in expanded:
            bundles, paths = site.get('bundles'), site.get('paths')
            if not bundles or paths is None or site.get('unknown_receiver') or not paths:
                unresolved.append(dict(site, reason='unresolved bundle/path or unsupported loader protocol'))
                continue
            for bundle in bundles:
                for path in paths:
                    matches = {(p, t) for p, t in catalogs.get(bundle, set())
                               if (p == path if site['kind'] in ('load', 'loadRes') else (p == path or p.startswith(path.rstrip('/')+'/') or path == ''))
                               and (site.get('type') is None or t == site['type'] or (site['type'] == 'cc.Font' and t in ('cc.TTFFont', 'cc.BitmapFont')))}
                    if not matches:
                        raise ValueError('production resource request missing/type mismatch: %s:%s at %s' % (bundle, path, site['id']))
                    required.update((bundle, p, t) for p, t in matches)
    if unresolved:
        raise ValueError('unresolved dynamic resource calls; adapt the finite production domain, do not hand-waive: ' + json.dumps(unresolved, ensure_ascii=False))
    return required, inventory, catalogs


def required_native_files(inventory):
    required = {}
    for row in inventory.get('reviewed_resolutions', []):
        if row.get('not_executed') or row.get('delegated_sdk'):
            continue
        if row.get('native_manifest_required') is not True:
            continue  # Existing reviewed profiles keep their earlier declared file-only contract.
        names = row.get('native_files', [])
        types = row.get('native_file_types', {})
        for name in names:
            kind = types.get(name)
            if kind not in {'cc.ImageAsset', 'NativeAudio'}:
                raise ValueError('reviewed Native file lacks exact resource type: '+name)
            if name in required and required[name] != kind:
                raise ValueError('conflicting Native resource types: '+name)
            required[name] = kind
    return required


def _audit_observed(files, manifest):
    """Observed runtime manifest (cocos-game-check/package-check/scripts/make_runtime_resource_manifest.py, D7 14 /
    D3 5): only for packages the static expansion cannot read (runtime-built load paths, 3.x SystemJS). A package
    whose requests expand statically keeps the static manifest, so the observed one never replaces a working check."""
    try:
        required_requests(files)
    except ValueError:
        pass
    else:
        raise ValueError('observed runtime manifest refused: this package expands statically; '
                         'use the generated manifest (audit_runtime_resources.py --native)')
    import importlib.util
    path = Path(__file__).resolve().parents[2] / 'cocos-game-check/package-check/scripts/make_runtime_resource_manifest.py'
    spec = importlib.util.spec_from_file_location('_cocos_runtime_resource_manifest', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        return dict(module.verify(files, manifest), source='observed')
    except module.ManifestRefused as error:
        raise ValueError('observed runtime manifest refused: ' + str(error))


@project_context
def audit(files, manifest):
    if isinstance(manifest, dict) and manifest.get('schema') == 'runtime_resource_manifest.observed.v1':
        return _audit_observed(files, manifest)
    if not isinstance(manifest, dict):
        raise ValueError('runtime resource manifest must be an object')
    rows = manifest.get('resources', [])
    if not isinstance(rows, list):
        raise ValueError('runtime resource manifest resources must be an array')
    required, inventory, catalogs = required_requests(files)
    native_required = required_native_files(inventory)
    native_declared = {}
    native_rows = manifest.get('native_files', [])
    if not isinstance(native_rows, list):
        raise ValueError('native_files must be an array')
    for row in native_rows:
        if not isinstance(row, dict) or set(row) != {'path','type','sha256'}:
            raise ValueError('invalid Native file resource row')
        name = row['path']
        if name in native_declared or name not in native_required:
            raise ValueError('unknown or duplicate Native file request: '+str(name))
        if row['type'] != native_required[name] or row['sha256'] != hashlib.sha256(files[name]).hexdigest():
            raise ValueError('Native resource type/bytes mismatch: '+name)
        native_declared[name] = row['type']
    if native_declared != native_required:
        raise ValueError('runtime manifest omitted production Native file requests: '+repr(sorted(set(native_required)-set(native_declared))))
    declared = set()
    for row in rows:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k] for k in ('bundle', 'path', 'type')):
            raise ValueError('runtime resource row requires nonempty bundle/path/type strings')
        query = (row['bundle'], row['path'], row['type'])
        if query in declared:
            raise ValueError('duplicate runtime resource row: ' + repr(query))
        declared.add(query)
        if (query[1], query[2]) not in catalogs.get(query[0], set()):
            raise ValueError('business runtime resources missing/type mismatch: ' + repr(query))
    missing = required - declared
    if missing:
        raise ValueError('runtime resource manifest omitted production requests: ' + repr(sorted(missing)))
    script_required = {r['path']: r['sha256'] for r in inventory.get('kit_script_files', [])}
    script_rows = manifest.get('script_files', [])
    if not isinstance(script_rows, list):
        raise ValueError('script_files must be an array')
    script_declared = {}
    for row in script_rows:
        if not isinstance(row, dict) or not {'path', 'sha256'} <= set(row) <= {'path', 'sha256', 'required_by'}:
            raise ValueError('invalid kit main.js script file row')
        if row['path'] in script_declared or row['path'] not in script_required:
            raise ValueError('unknown or duplicate kit main.js script file: ' + str(row['path']))
        if row['sha256'] != script_required[row['path']]:
            raise ValueError('kit main.js script file bytes changed: ' + row['path'])
        script_declared[row['path']] = row['sha256']
    if script_declared != script_required:
        raise ValueError('runtime manifest omitted kit main.js script files: ' + repr(sorted(set(script_required) - set(script_declared))))
    return {'passed': True, 'kit_script_files': inventory.get('kit_script_files', []), 'checked_requests': len(declared), 'production_required_requests': len(required),
            'native_file_required_requests':len(native_required), 'native_file_call_inventory':inventory.get('native_file_inventory',[]), 'reviewed_resolutions':inventory.get('reviewed_resolutions',[]), 'resource_call_sites': inventory['sites'], 'source_sha256': inventory['source_sha256'],
            'scanner_sha256': inventory['scanner_sha256'], 'bundles': sorted(catalogs)}


@project_context
def generate(files):
    required, inventory, _ = required_requests(files)
    native_required=required_native_files(inventory)
    return {'schema': 'runtime_resource_manifest.v3' if native_required else 'runtime_resource_manifest.v2',
            'native_files':[{'path':p,'type':t,'sha256':hashlib.sha256(files[p]).hexdigest()} for p,t in sorted(native_required.items())],
            'resources': [{'bundle': b, 'path': p, 'type': t} for b, p, t in sorted(required)],
            **({'script_files': [{'path': r['path'], 'sha256': r['sha256'], 'required_by': r['required_by']}
                                 for r in inventory['kit_script_files']]} if inventory.get('kit_script_files') else {}),
            'source_sha256': inventory['source_sha256'], 'scanner_sha256': inventory['scanner_sha256']}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--project',type=Path,help='project-local reviewed finite data domain context')
    a = ap.parse_args()
    try:
        if a.out.exists():
            raise ValueError('manifest output already exists')
        files = {p.relative_to(a.native).as_posix(): p.read_bytes() for p in a.native.rglob('*') if p.is_file()}
        if a.out.resolve().is_relative_to(a.native.resolve()):
            raise ValueError('resource manifest must stay outside the upload tree')
        result = generate(files,project=a.project)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open('x') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'status': 'resource_manifest_generated', 'requests': len(result['resources']), 'native_file_requests':len(result.get('native_files',[])), 'kit_script_files':len(result.get('script_files',[])), 'out': str(a.out)}))
    except (ValueError, OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False))
        raise SystemExit(1)
