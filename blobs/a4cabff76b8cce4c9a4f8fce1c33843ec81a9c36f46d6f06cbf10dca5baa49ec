"""Register a reviewed platform-only repair of an existing received Creator 1.9 game.

This is an immutable comparison/authorization boundary, never a prior delivery
approval. New UI/assets/features or engine replacement cannot use this scope.
The current startup, storage, input, ads and ZIP gates remain required.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def tree(root):
    root = Path(root)
    out = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError('Compatibility scope refuses symlinks')
        if p.is_file():
            out[p.relative_to(root).as_posix()] = sha(p.read_bytes())
    return out


def archive(path):
    path = Path(path).resolve()
    with zipfile.ZipFile(path) as z:
        rows = {}
        for i in z.infolist():
            if i.is_dir():
                continue
            if i.filename in rows or '..' in Path(i.filename).parts or i.filename.startswith('/'):
                raise ValueError('Unsafe or duplicate intake ZIP entry')
            rows[i.filename] = z.read(i)
    return rows


def register(project, native, source_zip, native_zip, instruction, out, *, reviewed=False):
    if not reviewed:
        raise ValueError('Read the actual source/native integration delta and current user instruction first')
    project, native, out = (Path(p).resolve() for p in (project, native, out))
    if not native.is_relative_to(project) or not out.is_relative_to(project) or out.exists():
        raise ValueError('New project-local scope and actual Native required')
    raw = archive(source_zip)
    roots = [n[:-len('project.json')] for n in raw if n.endswith('project.json') and '/' not in n[:-len('project.json')].strip('/')]
    if len(roots) != 1 or json.loads(raw[roots[0]+'project.json']).get('version') != '1.9.3':
        raise ValueError('Actual original Creator 1.9.3 source archive required')
    baseline = {n[len(roots[0]):]: sha(b) for n, b in raw.items()
                if n.startswith(roots[0]) and n[len(roots[0]):].split('/')[0] in ('assets', 'settings', 'build-templates')}
    current = {}
    for name in ('assets', 'settings', 'build-templates'):
        current.update({name+'/'+n: h for n, h in tree(project/name).items()})
    if set(current) != set(baseline):
        raise ValueError('A platform-only repair cannot add/remove source assets or UI')
    changed = sorted(n for n in current if current[n] != baseline[n])
    if not changed or any(not n.endswith('.js') for n in changed):
        raise ValueError('Only reviewed existing JavaScript integration changes may retain this contract')
    old = archive(native_zip)
    files = {n: (native/n).read_bytes() for n in tree(native)}
    if set(old) != set(files):
        raise ValueError('Native membership changed; review as a broader production change')
    from cocos1_compat import engine_file
    engine = engine_file(files)
    if not engine or files[engine] != old.get(engine):
        raise ValueError('The original actual 1.9.3 engine must stay unchanged')
    cache = json.loads((project/'.tiktok-kit/png-cache.json').read_text()).get('entries', {})
    native_changed = sorted(n for n in files if files[n] != old[n])
    for name in native_changed:
        if name.endswith('.js') or name in ('game.json', 'project.config.json'):
            continue
        if (name.startswith('assets/raw-internal/image/default_btn_') and name.endswith('.png')
                and cache.get(sha(old[name])) == sha(files[name])):
            continue  # Actual canonical PNG preparation, not a new art/feature scope.
        raise ValueError('Non-integration Native resource changed: '+name)
    instruction = Path(instruction).resolve()
    if not instruction.is_file() or not instruction.read_text().strip():
        raise ValueError('Saved current user authorization required')
    doc = {'schema': 'cocos-platform-compatibility-scope.v1',
           'operation': 'repair_existing_platform_integration',
           'authority': 'reviewed_current_user_instruction',
           'project': str(project), 'native': str(native),
           'instruction': {'path': str(instruction), 'sha256': sha(instruction.read_bytes())},
           'source_zip': {'path': str(Path(source_zip).resolve()), 'sha256': sha(Path(source_zip).read_bytes())},
           'native_zip': {'path': str(Path(native_zip).resolve()), 'sha256': sha(Path(native_zip).read_bytes())},
           'source_inputs': current, 'native_inputs': {n: sha(b) for n, b in files.items()},
           'source_delta': changed, 'native_delta': native_changed,
           'new_features_requested': False,
           'prior_writer_evidence': 'unavailable; no prior approval inferred',
           'created': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n')
    import project_qa
    store = project_qa.read_store()
    store.setdefault('compatibility_scopes', {})[str(project)] = {'path': str(out), 'sha256': sha(out.read_bytes())}
    project_qa.write_store(store)
    return doc


def verified(project):
    import project_qa
    project = Path(project).resolve()
    ref = project_qa.read_store().get('compatibility_scopes', {}).get(str(project))
    if not ref:
        return None
    path = Path(ref['path'])
    if not path.is_relative_to(project) or sha(path.read_bytes()) != ref['sha256']:
        raise ValueError('Reviewed compatibility scope changed')
    doc = json.loads(path.read_bytes())
    if (doc.get('schema') != 'cocos-platform-compatibility-scope.v1'
            or doc.get('operation') != 'repair_existing_platform_integration'
            or doc.get('authority') != 'reviewed_current_user_instruction'
            or doc.get('new_features_requested') is not False or doc.get('project') != str(project)):
        raise ValueError('Invalid registered compatibility boundary')
    for key in ('instruction', 'source_zip', 'native_zip'):
        if sha(Path(doc[key]['path']).read_bytes()) != doc[key]['sha256']:
            raise ValueError('Compatibility authorization/intake changed: '+key)
    current = {}
    for name in ('assets', 'settings', 'build-templates'):
        current.update({name+'/'+n: h for n, h in tree(project/name).items()})
    if current != doc['source_inputs'] or tree(doc['native']) != doc['native_inputs']:
        raise ValueError('Current integration differs from its reviewed scope')
    return doc


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('project', 'native', 'source-zip', 'native-zip', 'instruction', 'out'):
        p.add_argument('--'+key, required=True, type=Path)
    p.add_argument('--reviewed', action='store_true')
    args = vars(p.parse_args())
    doc = register(**args)
    print(json.dumps({'registered': True, 'source_delta': doc['source_delta'], 'native_delta': doc['native_delta']}, ensure_ascii=False))
