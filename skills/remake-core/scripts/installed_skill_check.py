#!/usr/bin/env python3
"""开工核对已装 Skill 有没有被直接改过（简化.11.14 R4D，普查 T21:installed_skill_direct_edit：游戏会话直接改已装
Skill 39 次，没交补丁、也没过发版自检）。只提示，不还原、不拦。

拿什么比：发版时写的同一套哈希。
  - 给了 --manifest（发版 ZIP 根目录的 distribution-manifest.json，或解压出来的那份）就用它；
  - 否则用每个已装 Skill 自带的 PROVENANCE.json（发版自检 regen_provenance.py 写的，文件哈希和
    distribution-manifest.json 是同一套；装包时随 Skill 一起装上）。
比什么：每个登记过的文件，已装副本的 SHA-256 和登记的是否一样。
  - 改过的（modified）、缺了的（missing）：提示「已装 Skill 被改过，请走补丁」并列出文件；
  - 多出来的（added，例如项目 QA 写进去的 reviewed_resource_profiles.json）：只列出来，不算被改；
  - __pycache__、.DS_Store、*.pyc 不看。
在 Skill 维护树（路径里有 /_内部/maintenance/）或发版工作目录里跑时，status 是 dev_tree，不提示（那里本来就在改）。

  python3 installed_skill_check.py [--root <skills 文件夹>] [--manifest <distribution-manifest.json>] [--json]
默认 --root 是本脚本所在的那个 skills 文件夹（<root>/remake-core/scripts/installed_skill_check.py）。
退出码一律 0（只提示）；参数错误 2。只用标准库，Windows / macOS / Linux 都能跑。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[1]
PROVENANCE = 'PROVENANCE.json'
PROV_SCHEMA = 'gameskills.release-provenance.v1'
MANIFEST_SCHEMA = 'cocos-skills-distribution.v1'
IGNORE_NAMES = {'.DS_Store', 'Thumbs.db', 'desktop.ini', PROVENANCE}
IGNORE_DIRS = {'__pycache__', '.pytest_cache'}
DEV_MARKS = ('/_内部/maintenance/', '/_work/')
LINE = '已装 Skill 被改过，请走补丁（改动写成补丁交 Skill 会话发版，不要直接改已装文件）'
LIMIT = 40


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _ignored(rel):
    parts = rel.split('/')
    return parts[-1] in IGNORE_NAMES or parts[-1].endswith('.pyc') or any(p in IGNORE_DIRS for p in parts)


def records_from_manifest(manifest):
    data = json.loads(Path(manifest).read_text(encoding='utf-8'))
    if data.get('schema') != MANIFEST_SCHEMA:
        raise ValueError('not a %s manifest: %s' % (MANIFEST_SCHEMA, manifest))
    out = {name: {} for name in data.get('skills', [])}
    for rel, row in data['files'].items():
        skill, _, inner = rel.partition('/')
        if skill in out and inner and not _ignored(inner):
            out[skill][inner] = row['sha256']
    return out, data.get('revision')


def records_from_provenance(root):
    out, revisions = {}, set()
    for prov in sorted(Path(root).glob('*/' + PROVENANCE)):
        try:
            data = json.loads(prov.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or data.get('schema') != PROV_SCHEMA or not isinstance(data.get('files'), list):
            continue
        out[prov.parent.name] = {r['path']: r['sha256'] for r in data['files']
                                 if isinstance(r, dict) and r.get('path') and not _ignored(r['path'])}
        revisions.add(data.get('revision'))
    return out, ', '.join(sorted(r for r in revisions if r)) or None


def check(root=None, manifest=None):
    """-> {'status': 'clean' | 'modified' | 'no_record' | 'dev_tree', 'root', 'revision', 'modified': [...],
    'missing': [...], 'added': [...], 'line'}"""
    root = Path(root or DEFAULT_ROOT).resolve()
    shown = root.as_posix() + '/'
    if manifest is None and any(m in shown for m in DEV_MARKS):
        return {'status': 'dev_tree', 'root': str(root), 'line': '在 Skill 维护树里，不核对'}
    records, revision = records_from_manifest(manifest) if manifest else records_from_provenance(root)
    if not records:
        return {'status': 'no_record', 'root': str(root),
                'line': '没找到发版哈希记录（PROVENANCE.json / distribution-manifest.json），没核对已装 Skill'}
    modified, missing, added = [], [], []
    for skill, files in sorted(records.items()):
        folder = root / skill
        if not folder.is_dir():
            continue                               # a skill of the release that is not installed here
        for rel, sha in sorted(files.items()):
            p = folder / rel
            if not p.is_file():
                missing.append('%s/%s' % (skill, rel))
            elif _sha(p) != sha:
                modified.append('%s/%s' % (skill, rel))
        for p in sorted(folder.rglob('*')):
            if p.is_file() and not p.is_symlink():
                rel = p.relative_to(folder).as_posix()
                if rel not in files and not _ignored(rel):
                    added.append('%s/%s' % (skill, rel))
    status = 'modified' if modified or missing else 'clean'
    line = ('%s：%s' % (LINE, '、'.join((modified + missing)[:LIMIT]) + (' 等 %d 个' % len(modified + missing)
                                                                      if len(modified + missing) > LIMIT else ''))
            if status == 'modified' else '已装 Skill 和发版记录一致')
    return {'status': status, 'root': str(root), 'revision': revision, 'reference': str(manifest) if manifest else PROVENANCE,
            'modified': modified, 'missing': missing, 'added': added[:200], 'added_count': len(added), 'line': line,
            'note': '只提示，不还原；多出来的文件（added）不算被改'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path)
    ap.add_argument('--manifest', type=Path)
    ap.add_argument('--json', action='store_true', help='print the whole result (default: one line + lists)')
    a = ap.parse_args(argv)
    try:
        r = check(a.root, a.manifest)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 2
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(r['line'])
        for key in ('modified', 'missing'):
            for item in r.get(key) or []:
                print('  %s: %s' % (key, item))
    return 0


if __name__ == '__main__':
    sys.exit(main())
