#!/usr/bin/env python3
"""Read-only Cocos reference inventory; exit 0 means report written, never art approval.

UUID edges are serialized references. Literal strings in code/JSON are observations,
not executed loads. Transitive edges are possible parent consumers, not reachability.
"""
import argparse
from collections import defaultdict, deque
import hashlib
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from audit_ad_entry_reachability import compress
from tiktok_finalize_steps.policy import decode_uuid

SERIAL = {'.prefab', '.scene', '.fire', '.json'}
CODE = {'.js', '.ts'}
TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')
LOAD = re.compile(r'\b(load|loadRes|loadDir|loadAny|loadRemote|loadBundle)\s*\(')


def uuid_key(value):
    if not isinstance(value, str):
        return None
    base = decode_uuid(value)
    return base + ('@' + value.split('@', 1)[1] if '@' in value else '') if base else None


def uuid_aliases(value):
    key = uuid_key(value)
    if not key:
        return set()
    base, sep, suffix = key.partition('@')
    return {key, compress(base) + (sep + suffix), value}


def walk_strings(data, pointer=''):
    if isinstance(data, dict):
        for k, v in data.items():
            yield from walk_strings(v, pointer + '/' + str(k).replace('~', '~0').replace('/', '~1'))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            yield from walk_strings(v, pointer + '/' + str(i))
    elif isinstance(data, str):
        yield pointer, data


def meta_uuids(meta):
    if not isinstance(meta, dict):
        raise ValueError('meta/subMeta must be object')
    if meta.get('uuid'):
        if not uuid_key(meta['uuid']):
            raise ValueError('unsupported meta UUID')
        yield meta['uuid']
    children = meta.get('subMetas', {})
    if not isinstance(children, dict):
        raise ValueError('subMetas must be object')
    for child in children.values():
        yield from meta_uuids(child)


def node_path(data, pointer):
    """Common Cocos 2/3 flat serialization only; pointer remains authoritative."""
    if not isinstance(data, list):
        return None
    try:
        index = int(pointer.split('/')[1])
        obj = data[index]
        if obj.get('__type__') != 'cc.Node':
            index = obj['node']['__id__']
        names, seen = [], set()
        while isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(data):
            if index in seen:
                return None
            seen.add(index)
            obj = data[index]
            names.append(str(obj.get('_name', '(unnamed)')))
            index = (obj.get('_parent') or {}).get('__id__')
        return '/'.join(reversed(names)) or None
    except (ValueError, KeyError, IndexError, AttributeError, TypeError):
        return None


def inspect(project, assets):
    project = Path(project).resolve()
    root = project / 'assets'
    if not root.is_dir() or root.is_symlink() or not assets:
        raise ValueError('real project/assets and at least one asset are required')
    targets = []
    for asset in assets:
        p = (project / asset).resolve()
        if not p.is_relative_to(root) or p.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.fnt'} or not p.is_file():
            raise ValueError('asset must be an existing PNG/JPEG/FNT inside project/assets: ' + str(asset))
        targets.append(p.relative_to(project).as_posix())
    unresolved, hashes, texts, identities = [], {}, {}, {}
    uuids, paths, reverse = defaultdict(set), defaultdict(set), defaultdict(list)

    def issue(reason, file, **extra):
        unresolved.append(dict(reason=reason, file=file, **extra))

    def read(p):
        rel = p.relative_to(project).as_posix()
        try:
            if p.is_symlink() or not p.resolve().is_relative_to(root):
                raise ValueError('symlink/outside assets')
            before = p.stat()
            raw = p.read_bytes()
            after = p.stat()
            if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                raise ValueError('source changed during read')
            hashes[rel] = hashlib.sha256(raw).hexdigest()
            return raw
        except (OSError, ValueError) as exc:
            issue('unreadable_or_changed_file', rel, detail=str(exc))

    files = []
    for directory, dirs, names in os.walk(root, followlinks=False,
                                          onerror=lambda e: issue('directory_unreadable', str(e.filename), detail=str(e))):
        for name in list(dirs):
            p = Path(directory) / name
            if p.is_symlink():
                issue('symlink_directory_not_followed', p.relative_to(project).as_posix())
                dirs.remove(name)
        files.extend(Path(directory) / name for name in names)
    for p in sorted(files):
        rel = p.relative_to(project).as_posix()
        if p.suffix == '.meta':
            raw = read(p)
            if raw is None:
                continue
            owner = rel[:-5]
            if not (project / owner).exists():
                issue('orphan_meta', rel)
            try:
                ids = list(meta_uuids(json.loads(raw)))
                identities[owner] = ids
                for uid in ids:
                    for alias in uuid_aliases(uid):
                        uuids[alias].add(owner)
                if not ids:
                    issue('meta_without_uuid', rel)
            except (ValueError, UnicodeError) as exc:
                issue('bad_meta', rel, detail=str(exc))
        elif p.suffix.lower() in SERIAL | CODE:
            raw = read(p)
            if raw is not None:
                try:
                    texts[rel] = raw.decode('utf-8-sig')
                except UnicodeError as exc:
                    issue('bad_text_encoding', rel, detail=str(exc))
        # Exact paths only. Never match basename or a similar filename.
        if p.suffix != '.meta' and p.is_file() and not p.is_symlink():
            paths[rel].add(rel)
            parts = Path(rel).parts
            if 'resources' in parts:
                resource = Path(*parts[parts.index('resources') + 1:]).with_suffix('').as_posix()
                paths[resource].add(rel)
                paths['resources/' + resource].add(rel)
                if p.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
                    paths[resource + '/spriteFrame'].add(rel)

    def observe(file, value, location, ref_kind=False):
        key = uuid_key(value) or value
        owners = uuids.get(key, set())
        kind = 'uuid_reference' if ref_kind else 'uuid_literal_review'
        if not owners:
            owners, kind = paths.get(value, set()), 'path_literal_review'
        if len(owners) > 1:
            issue('ambiguous_reference', file, value=value, candidates=sorted(owners), **location)
        if not owners and (ref_kind and (uuid_key(value) or re.fullmatch(r'[0-9a-fA-F]{5}[A-Za-z0-9+/]{18}', value))):
            issue('unmapped_uuid', file, value=value, **location)
        if value.startswith(('http://', 'https://', 'db://', 'file://')):
            issue('external_reference', file, value=value, **location)
        for owner in sorted(owners - {file}):
            reverse[owner].append(dict(file=file, kind=kind, value=value, source_sha256=hashes[file], **location))

    for file, text in texts.items():
        if Path(file).suffix.lower() in SERIAL:
            try:
                data = json.loads(text)
                if Path(file).suffix.lower() != '.json' and not (isinstance(data, list) and all(isinstance(x, dict) for x in data)):
                    issue('nonstandard_scene_serialization', file, detail='Pointers/string observations only; node paths may be unavailable.')
                for pointer, value in walk_strings(data):
                    loc = dict(json_pointer=pointer, node_path=node_path(data, pointer))
                    if isinstance(data, list) and pointer.split('/')[1:2] and pointer.split('/')[1].isdigit():
                        obj = data[int(pointer.split('/')[1])]
                        if isinstance(obj, dict) and '_enabled' in obj:
                            loc['serialized_enabled'] = obj['_enabled']
                    observe(file, value, loc,
                            pointer.endswith(('/__uuid__', '/__type__')))
            except (ValueError, RecursionError) as exc:
                issue('bad_serialized_file', file, detail=str(exc))
        else:
            masked, literals = list(text), {}
            for match in TOKEN.finditer(text):
                token, start = match.group(), match.start()
                masked[start:match.end()] = ' ' * len(token)
                if token.startswith(('/',)):
                    continue
                value = token[1:-1]
                loc = dict(line=text.count('\n', 0, start) + 1)
                if '\\' in value or '${' in value:
                    issue('escaped_or_interpolated_literal', file, **loc)
                    continue
                literals[start] = (match.end(), value)
                observe(file, value, loc)
            code = ''.join(masked)
            for match in LOAD.finditer(code):
                start = match.end()
                while start < len(text) and text[start].isspace():
                    start += 1
                literal = literals.get(start)
                tail = text[literal[0]:].lstrip() if literal else ''
                reason = 'literal_load_requires_runtime_review' if literal and tail[:1] in {',', ')'} else 'dynamic_load_unresolved'
                issue(reason, file, line=text.count('\n', 0, match.start()) + 1)
    reports = []
    for target in sorted(set(targets)):
        read(project / target)
        distances, queue, indirect = {target: 0}, deque([(target, [target])]), []
        while queue:
            child, chain = queue.popleft()
            if child not in identities:
                issue('missing_meta_or_identity', child)
            for hit in reverse[child]:
                parent = hit['file']
                if parent in distances:
                    continue
                distances[parent] = distances[child] + 1
                route = chain + [parent]
                queue.append((parent, route))
                if distances[parent] > 1:
                    indirect.append(dict(hit, via=route, depth=distances[parent]))
        reports.append(dict(asset=target, source_sha256=hashes.get(target), uuids=identities.get(target, []),
                            direct=reverse[target], indirect=indirect))
    issue('runtime_coverage_not_proven', 'assets', detail='Static observations only; dynamic wrappers/imports, bundles, conditions, active states and runtime-created consumers are not closed.')
    return dict(schema='art_consumer_index.v1', project=str(project), assets=reports, sources=hashes,
                unresolved=unresolved, coverage_complete=False, may_reduce_capture=False, visual_passed=None,
                snapshot_atomic=False, scope='Read-only reference observations; not reachability, usage completeness, screenshot reuse or art acceptance.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--asset', action='append', required=True)
    parser.add_argument('--out', required=True, help='JSON report outside the project')
    args = parser.parse_args(argv)
    try:
        out, project = Path(args.out).resolve(), Path(args.project).resolve()
        if out.is_relative_to(project):
            raise ValueError('--out must be outside the project')
        report = inspect(project, args.asset)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(report=str(out), coverage_complete=False, may_reduce_capture=False)))
        return 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
