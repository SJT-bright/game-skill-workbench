#!/usr/bin/env python3
"""Snapshot clean Cocos files and compare hashes and serialized UI structure."""
import argparse
import hashlib
import json
from pathlib import Path

EXCLUDED = {'library', 'temp', 'build', 'profiles', 'node_modules', '.git', '.DS_Store'}
TEXT_FIELDS = {'_string'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strip_text(value):
    if isinstance(value, dict):
        return {k: strip_text(v) for k, v in value.items() if k not in TEXT_FIELDS}
    if isinstance(value, list):
        return [strip_text(v) for v in value]
    return value


def snapshot(project):
    result = {'project': str(project), 'files': {}, 'serialized_nontext': {}, 'labels': {}}
    for p in sorted(project.rglob('*')):
        rel = p.relative_to(project)
        if rel.parts[0] in EXCLUDED or any(x in {'.git', 'node_modules', '.DS_Store', '__pycache__'} for x in rel.parts):
            continue
        if p.is_symlink():
            raise ValueError(f'Symlink requires explicit review: {rel}')
        if not p.is_file():
            continue
        data = p.read_bytes()
        name = rel.as_posix()
        result['files'][name] = digest(data)
        if p.suffix in {'.scene', '.fire', '.prefab'}:
            obj = json.loads(data)
            result['serialized_nontext'][name] = digest(json.dumps(strip_text(obj), sort_keys=True, ensure_ascii=False).encode())
            result['labels'][name] = [x.get('_string') for x in obj if isinstance(x, dict) and '_string' in x]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--before', type=Path)
    args = parser.parse_args()
    current = snapshot(args.project.resolve())
    if args.before:
        before = json.loads(args.before.read_text())
        old, new = before['files'], current['files']
        current['diff'] = {
            'added': sorted(new.keys() - old.keys()),
            'removed': sorted(old.keys() - new.keys()),
            'changed': sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
            'serialized_nontext_changed': sorted(k for k in before['serialized_nontext'] if current['serialized_nontext'].get(k) != before['serialized_nontext'][k]),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(current.get('diff', {'files': len(current['files'])}), ensure_ascii=False))


if __name__ == '__main__':
    main()
