#!/usr/bin/env python3
"""Source hygiene (简化.11.6, Saul 2026-11-04「提醒做 91 的对话交源码前删掉 .git」「同类问题要让它直接出不了包」).

91_SLS11海洋逃脱: the seller's SLS11.zip carried a full .git (one "init" commit). The working tree had no secret, but
the commit still held app_desc.txt, the store listing with a developer account and password. Anyone who gets the
folder or a ZIP made from it gets the password. So:

  version control / IDE folders   .git .svn .hg .bzr CVS  and  .idea .vscode .vs .history .fleet  (and __MACOSX)
                                  never enter a working copy, a source ZIP or an upload package.
  credential files                app_desc.txt, .env, *.keystore *.jks *.p12 *.pfx *.pem *.mobileprovision
  credential lines                in text files (.txt .md .ini .cfg .conf .env .properties .yaml .yml .plist .csv .json
                                  .xml): a label 密码 / 口令 / 账号 / 帐号 / 账户 / password / passwd / pwd / secret /
                                  api_key / access_token ending the key (appSecret, keystorePassword) followed by : or = and a value
                                  that is not empty, true, false or null
                                  ("keystorePassword": "" in Cocos local/builder.json is empty, so it is not a hit).
Build caches (library temp build local node_modules profiles) are not looked into: they are never shipped.

  python3 source_hygiene.py --source <folder | .zip> [--out report.json]   exit 0 clean, 1 findings, 2 bad input
Used by: cocos-game-to-english/scripts/unpack_source.py (intake), make_source_zip.py (source ZIP writer),
prepare_delivery.py --source, package_gates/secrets.py (both upload writers and check_package).
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

VCS_DIRS = {'.git', '.svn', '.hg', '.bzr', 'cvs'}
IDE_DIRS = {'.idea', '.vscode', '.vs', '.history', '.fleet'}
JUNK_DIRS = {'__macosx'}
CACHE_DIRS = {'library', 'temp', 'build', 'local', 'node_modules', 'profiles'}
SECRET_NAMES = {'app_desc.txt', '.env'}
SECRET_SUFFIXES = ('.keystore', '.jks', '.p12', '.pfx', '.pem', '.mobileprovision')
TEXT_SUFFIXES = ('.txt', '.md', '.ini', '.cfg', '.conf', '.env', '.properties', '.yaml', '.yml', '.plist', '.csv',
                 '.json', '.xml')
# the label must end the key (keystorePassword, appSecret, 登录密码 match; secretIncluded does not)
SECRET_LINE = re.compile(r'(密码|口令|账号|帐号|账户|password|passwd|pwd|secret|api[_-]?key|access[_-]?token)'
                         r'["\']?\s*[:=：]\s*["\']?([^\s"\'，,;；}<）)]{3,})', re.I)
NOT_A_VALUE = {'false', 'true', 'null', 'none', 'undefined', 'nil', 'not', 'n/a', 'todo', 'xxx', '***', 'placeholder', 'empty'}
NOT_SCANNED = {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'}   # dependency metadata
MAX_TEXT = 2_000_000


def blocked_dir(parts):
    """-> ('vcs' | 'ide', name) for the first version-control / IDE folder in a path, else None."""
    for p in parts[:-1]:
        low = p.lower()
        if low in VCS_DIRS:
            return 'vcs', p
        if low in IDE_DIRS:
            return 'ide', p
        if low in JUNK_DIRS:
            return 'junk', p
    if parts and parts[-1].lower() == '.git':
        return 'vcs', parts[-1]          # a .git FILE (worktree / submodule pointer)
    return None


def in_cache(parts):
    """Cocos caches sit at the project root, or one level down in a ZIP with a top folder (SLS11/local/...)."""
    return any(p.lower() in CACHE_DIRS for p in parts[:-1][:2])


def secret_reason(rel, data=None):
    """-> reason string when this file looks like it holds credentials, else None. data = bytes or None."""
    name = PurePosixPath(rel).name.lower()
    if name in SECRET_NAMES:
        return 'credential file %s (store listing / environment secrets)' % name
    if name.endswith(SECRET_SUFFIXES):
        return 'signing key / certificate file'
    if data is None or not name.endswith(TEXT_SUFFIXES) or name in NOT_SCANNED:
        return None
    text = data[:MAX_TEXT].decode('utf-8', 'ignore')
    m = next((x for x in SECRET_LINE.finditer(text) if x.group(2).lower() not in NOT_A_VALUE), None)
    if m:
        line = text.count('\n', 0, m.start()) + 1
        return 'line %d looks like a credential: %s = %s***' % (line, m.group(1), m.group(2)[:1])
    return None


def scan_items(items):
    """items: iterable of (posix relpath, bytes-or-None). -> {'vcs_ide': [...], 'secrets': [...]}"""
    vcs, secrets, seen = [], [], set()
    for rel, data in items:
        parts = PurePosixPath(rel).parts
        hit = blocked_dir(parts)
        if hit:
            i = [p.lower() for p in parts].index(hit[1].lower())
            top = '/'.join(parts[:i + 1])
            if top not in seen:
                seen.add(top)
                vcs.append({'path': top, 'kind': hit[0]})
            continue
        if in_cache(parts):
            continue
        why = secret_reason(rel, data)
        if why:
            secrets.append({'path': rel, 'why': why})
    return {'vcs_ide': vcs, 'secrets': secrets}


def iter_folder(root):
    root = Path(root)
    for p in sorted(root.rglob('*')):
        if p.is_file() or (p.name == '.git' and not p.is_dir()):
            rel = p.relative_to(root).as_posix()
            parts = PurePosixPath(rel).parts
            want = not blocked_dir(parts) and not in_cache(parts) and p.name.lower().endswith(TEXT_SUFFIXES)
            try:
                yield rel, (p.read_bytes() if want and p.stat().st_size <= MAX_TEXT * 4 else None)
            except OSError:
                yield rel, None


def iter_zip(path):
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                name = info.filename.rstrip('/')
                if blocked_dir(PurePosixPath(name + '/x').parts):
                    yield name + '/', None
                continue
            rel = info.filename
            parts = PurePosixPath(rel).parts
            want = not blocked_dir(parts) and not in_cache(parts) and rel.lower().endswith(TEXT_SUFFIXES)
            yield rel, (z.read(info) if want and info.file_size <= MAX_TEXT * 4 else None)


def audit(source):
    source = Path(source)
    if source.is_dir():
        found = scan_items(iter_folder(source))
    elif zipfile.is_zipfile(source):
        found = scan_items(iter_zip(source))
    else:
        raise ValueError('not a folder or a ZIP: %s' % source)
    problems = ['%s folder %s: version control / IDE data must not leave this machine (it can hold deleted files, '
                'e.g. 91 SLS11 .git kept app_desc.txt with an account and password)' % (v['kind'], v['path'])
                for v in found['vcs_ide']]
    problems += ['%s: %s' % (s['path'], s['why']) for s in found['secrets']]
    return {'tool': 'source_hygiene', 'schema': 1, 'source': str(source.resolve()), 'vcs_ide': found['vcs_ide'],
            'secrets': found['secrets'], 'problems': problems, 'passed': not problems,
            'status': 'pass' if not problems else 'fail',
            'boundary': 'names and text patterns only; a secret in code or an image is not found'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        r = audit(a.source)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False)); return 2
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
