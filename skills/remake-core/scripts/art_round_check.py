"""Read-only glue for the actual English Web art check and trial-link gate."""
import hashlib
import json
from pathlib import Path
import subprocess


def _run_single(command, project, build, dumps=None):
    arguments = ['node', str(Path(__file__).with_name('art_capture_round.mjs')), command, str(project), str(build)]
    if dumps is not None:
        arguments.append(str(dumps))
    try:
        proc = subprocess.run(arguments, capture_output=True, text=True, timeout=180)
        result = json.loads(proc.stdout) if proc.stdout else {}
        if proc.returncode:
            ids = [row['id'] for row in result.get('cases', []) if row['action'] == 'recapture']
            result['error'] = proc.stderr.strip() or ('需要重拍：' + '、'.join(ids))
        return result
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'error': str(exc)}

def run(command, project, build, dumps=None):
    """Verify two sealed capture rounds against the same live Web export."""
    root = Path(dumps).resolve() if dumps is not None else None
    if command in ('verify', 'plan') and root is not None:
        from art_capture_history import verify as verify_originals, MANIFEST
        try:
            history = verify_originals(project, build, root)
            if history is not None:
                return history
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            # A declared mixed transition is authoritative or invalid. Never
            # fall back to a looser scan after it failed validation.
            if (root / MANIFEST).is_file():
                return {'ready': False, 'error': str(exc)}
    manifest = root / 'same-build-rounds.json' if root else None
    if command != 'verify' or manifest is None or not manifest.is_file():
        return _run_single(command, project, build, dumps)
    try:
        primary, extra = root / 'primary', root / 'supplement'
        extra_project = Path(json.loads(manifest.read_text())['supplement_project']).resolve(strict=True)
        if extra_project == Path(project).resolve():
            raise ValueError('supplement must have an independent registered capture round')
        for file in root.rglob('*'):
            if file.is_symlink():
                raise ValueError('symbolic link in combined capture evidence')
            if 'ui-dump-' in file.name and file.suffix == '.json' and file.parent not in (primary, extra):
                raise ValueError('unregistered dump outside both capture rounds: ' + file.name)
        original = _run_single('verify', project, build, primary)
        supplement = _run_single('verify', extra_project, build, extra)
        for report in (original, supplement):
            if report.get('ready') is not True or report.get('error'):
                raise ValueError(report.get('error') or 'capture round incomplete')
        identities = (_run_single('status', p, build) for p in (project, extra_project))
        left, right = identities
        for key in ('source_hash', 'export_hash', 'collector_hash'):
            if not left.get(key) or left[key] != right.get(key):
                raise ValueError('capture rounds do not share the same ' + key)
        cases = original['cases'] + supplement['cases']
        if len({row['id'] for row in cases}) != len(cases):
            raise ValueError('duplicate case in combined capture rounds')
        return dict(original, cases=cases, supplement={
            'round': supplement['round'], 'version': supplement['version'],
            'origin_hash': origin_hash(supplement),
        })
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {'ready': False, 'error': str(exc)}


def origin_hash(plan):
    pairs = [(row['id'], row['origin']) for row in plan['cases']]
    return hashlib.sha256(json.dumps(sorted(pairs)).encode()).hexdigest()


def artifact_hash(project, dumps):
    """Bind supplementary frames and reports to a pass, including project-relative evidence references."""
    project = Path(project).resolve()
    evidence = project/'docs/test'
    dumps = Path(dumps).resolve(strict=True)
    pending = list(dumps.rglob('*'))
    seen = {}
    explicit = set()
    from art_capture_history import MANIFEST, current_context, verify as verify_originals
    if (dumps / MANIFEST).is_file():
        current = json.loads((project/'.tiktok-kit/art-rounds/current.json').read_text())
        snap = json.loads((project/'.tiktok-kit/art-rounds/snapshots'/(current['version']+'.json')).read_text())
        verified = verify_originals(project, snap['build'], dumps)
        if not verified or not verified.get('ready'):raise ValueError('inheritance artifact is not verified')
        manifest = json.loads((dumps/MANIFEST).read_text())
        explicit.add(Path(manifest['baseline']).resolve())
        for ref in verified['quality_refs']:explicit.add(Path(ref['path']).resolve())
        for name in verified['resolved_dumps']:
            raw=Path(name);doc=json.loads(raw.read_text())
            explicit.update((raw.resolve(),(raw.parent/doc['screenshot']).resolve()))
            proof=project/'.tiktok-kit/art-rounds/proofs'/(doc['art_capture_id']+'.json')
            explicit.add(proof.resolve())
            version=json.loads(proof.read_text())['version']
            explicit.add((project/'.tiktok-kit/art-rounds/snapshots'/(version+'.json')).resolve())
        pending.extend(explicit)
    def references(obj):
        if isinstance(obj, dict):
            for item in obj.values():
                yield from references(item)
        elif isinstance(obj, list):
            for item in obj:
                yield from references(item)
        elif isinstance(obj, str) and obj.startswith('docs/test/') and Path(obj).suffix.lower() in {
                '.png', '.jpg', '.jpeg', '.json', '.webp', '.webm', '.mp4'}:
            yield project / obj
    while pending:
        item = pending.pop()
        if item.is_symlink():
            raise ValueError('symbolic link in art evidence: '+str(item))
        if item.is_dir():
            continue
        file = item.resolve(strict=True)
        if not (file.is_relative_to(dumps) or file.is_relative_to(evidence) or file in explicit):
            raise ValueError('art evidence outside capture directories: '+str(file))
        if file in seen:
            continue
        data = file.read_bytes()
        seen[file] = hashlib.sha256(data).hexdigest()
        if file.suffix == '.json':
            pending.extend(references(json.loads(data)))
    return hashlib.sha256(json.dumps(sorted((str(f), h) for f, h in seen.items())).encode()).hexdigest()


def matches_receipt(project, build, proof):
    try:
        plan = run('verify', project, build, proof['dumps'])
        return (plan.get('ready') is True and 'error' not in plan
                and plan['round'] == proof['round'] and plan['version'] == proof['version']
                and origin_hash(plan) == proof['origin_hash']
                and artifact_hash(project, proof['dumps']) == proof['artifact_hash'])
    except (OSError, KeyError, TypeError, ValueError):
        return False
