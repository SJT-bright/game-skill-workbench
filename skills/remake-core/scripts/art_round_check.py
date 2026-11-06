"""Read-only glue for the actual English Web art check and trial-link gate."""
import hashlib
import json
from pathlib import Path
import subprocess


def run(command, project, build, dumps=None):
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
        if not (file.is_relative_to(dumps) or file.is_relative_to(evidence)):
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
