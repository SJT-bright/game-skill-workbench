#!/usr/bin/env python3
"""Inventory Han text candidates and image review scope; never certifies pixels/UI."""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

SOURCE_ROOT_CACHE = {'library', 'temp', 'build', 'profiles', '.git', 'node_modules'}
ANY_CACHE = {'.git', '__pycache__', '__MACOSX'}
TEXT = {'.js', '.ts', '.json', '.fire', '.scene', '.prefab', '.meta', '.atlas',
        '.fnt', '.xml', '.svg', '.html', '.htm', '.css', '.csv', '.tsv', '.txt',
        '.yaml', '.yml', '.plist', '.lua', '.effect', '.mtl', '.bytes', '.anim',
        '.animation', '.spriteatlas', '.pac', '.asset', '.text', '.ini', '.properties'}
IMAGES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tif', '.tiff', '.svg', '.avif', '.heic', '.heif'}
ENCODED_VISUALS = {'.skel', '.dbbin', '.csb', '.ccbi', '.pvr', '.pkm', '.ktx', '.ktx2', '.astc', '.basis'}
HAN = re.compile('[\u3007\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff'
                 '\U00020000-\U0002ffff\U00030000-\U000323af]+')
ESCAPE = re.compile(r'\\u\{([0-9a-fA-F]{1,6})\}|\\u([0-9a-fA-F]{4})')
SURROGATE = re.compile(r'\\u([dD][89aAbB][0-9a-fA-F]{2})\\u([dD][cCdDeEfF][0-9a-fA-F]{2})')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decoded(line):
    line = SURROGATE.sub(lambda m: chr(0x10000 + ((int(m[1], 16) - 0xD800) << 10)
                                     + int(m[2], 16) - 0xDC00), line)
    def replace(m):
        value = int(m[1] or m[2], 16)
        return chr(value) if value <= 0x10FFFF else m[0]
    return html.unescape(ESCAPE.sub(replace, line))


def records(root, role):
    if root.is_symlink():
        raise ValueError('Review root symlink explicitly: ' + str(root))
    if root.is_file() and role == 'native' and root.suffix.lower() == '.zip':
        seen = set()
        with zipfile.ZipFile(root) as archive:
            for item in sorted(archive.infolist(), key=lambda x: x.filename):
                name = item.filename
                parts = name.rstrip('/').split('/')
                if ('\\' in name or name.startswith('/') or ':' in parts[0]
                        or any(p in {'', '.', '..'} for p in parts)):
                    raise ValueError('Unsafe ZIP path: ' + name)
                if name in seen:
                    raise ValueError('Duplicate ZIP entry: ' + name)
                seen.add(name)
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError('ZIP symlink requires review: ' + name)
                if item.is_dir() or '__MACOSX' in parts or parts[-1] == '.DS_Store':
                    continue
                yield name, archive.read(item)
        return
    if not root.is_dir():
        raise ValueError('Expected a directory or Native ZIP: ' + str(root))
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if (p.name == '.DS_Store' or any(x in ANY_CACHE for x in rel.parts)
                or role == 'source' and (rel.parts[0] in SOURCE_ROOT_CACHE or 'node_modules' in rel.parts)):
            continue
        if p.is_symlink():
            raise ValueError('Symlink requires explicit review: ' + str(p))
        if p.is_file():
            yield rel.as_posix(), p.read_bytes()


def scan(targets):
    result = {'schema': 'english_coverage_inventory.v1', 'status': 'review_required',
              'targets': {}, 'text_candidates': [], 'images': [], 'encoded_visuals': [],
              'chinese_paths': [], 'unreadable_text': [], 'other_suffixes': {},
              'limits': ['Static candidates include internal comments/keys; reviewer determines visibility.',
                         'No OCR, image/animation viewing, runtime traversal or translation is performed.',
                         'Zero candidates does not certify all-English output.',
                         'Dynamic character assembly, remote content and unknown formats need project-specific review.']}
    image_groups, others = {}, Counter()
    for role, root in targets.items():
        files = {}
        for name, data in records(root, role):
            digest = sha(data)
            files[name] = digest
            suffix = PurePosixPath(name).suffix.lower()
            location = {'target': role, 'path': name}
            if HAN.search(name):
                result['chinese_paths'].append(location)
            if suffix in IMAGES:
                group = image_groups.setdefault(digest, {'sha256': digest, 'locations': [], 'review': 'pending'})
                group['locations'].append(location)
            if suffix in ENCODED_VISUALS:
                result['encoded_visuals'].append({**location, 'sha256': digest, 'review': 'pending_source_mapping'})
            if suffix not in TEXT:
                others[suffix or '(no suffix)'] += 1
                continue
            try:
                encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
                text = data.decode(encoding)
            except UnicodeError:
                result['unreadable_text'].append({**location, 'sha256': digest, 'reason': 'encoding_or_binary_requires_review'})
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                value = decoded(line)
                for match in HAN.finditer(value):
                    identity = [role, name, digest, line_number, match.start()]
                    result['text_candidates'].append({**location, 'id': sha(json.dumps(identity).encode())[:24],
                        'file_sha256': digest, 'line': line_number, 'decoded_column': match.start() + 1,
                        'text': match[0], 'context': value[max(0, match.start()-60):match.end()+60],
                        'decoded_escapes': value != line, 'disposition': 'pending'})
        if not files:
            raise ValueError('Empty scan target: ' + str(root))
        binding = {'root': str(root.resolve()), 'files': files,
                   'tree_sha256': sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())}
        if root.is_file():
            binding['zip_sha256'] = sha(root.read_bytes())
        result['targets'][role] = binding
    result['images'] = sorted(image_groups.values(), key=lambda x: x['sha256'])
    result['other_suffixes'] = dict(sorted(others.items()))
    result['summary'] = {'files': sum(len(t['files']) for t in result['targets'].values()),
                         'text_candidates': len(result['text_candidates']),
                         'unique_images_requiring_review': len(result['images']),
                         'encoded_visuals_requiring_mapping': len(result['encoded_visuals']),
                         'unreadable_text': len(result['unreadable_text'])}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for role in ('source', 'web', 'native'):
        parser.add_argument('--' + role, type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fail-on-candidates', action='store_true',
                        help='Diagnostic exit 2 for any candidate, including internal comments; not a visual gate')
    args = parser.parse_args()
    targets = {role: getattr(args, role) for role in ('source', 'web', 'native') if getattr(args, role)}
    if not targets:
        parser.error('At least one current source/Web/Native target is required')
    for root in targets.values():
        if args.output.resolve().is_relative_to(root.resolve()) or args.output.resolve() == root.resolve():
            parser.error('Write evidence outside every scanned target')
    try:
        result = scan(targets)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # errors='backslashreplace': real projects can contain undecodable bytes (lone surrogates); never crash the report
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', errors='backslashreplace')
    print(json.dumps({'status': result['status'], **result['summary'], 'output': str(args.output.resolve())}))
    return 2 if result['unreadable_text'] or args.fail_on_candidates and result['text_candidates'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
