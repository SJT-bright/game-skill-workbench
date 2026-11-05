#!/usr/bin/env python3
"""Write the source ZIP that is handed over (简化.11.6, Saul 2026-11-04「提醒做 91 的对话交源码前删掉 .git」).

Every source ZIP a session gives out (可编辑源码、交付源码) is made with this script, not by hand:
  - left out: version control / IDE folders (.git .svn .hg .bzr CVS .idea .vscode .vs .history .fleet), __MACOSX,
    Finder / Windows junk, and the Cocos caches library temp build local node_modules profiles;
  - refused (no ZIP written): a credential file or line in the project (source_hygiene.py: app_desc.txt, .env, signing
    keys, 密码 / 账号 / password / appSecret ... = value). Remove the file from the project, or blank the value
    (settings/project.json appSecret ""), then run again; there is no flag that ships it anyway;
  - the written ZIP is checked again with source_hygiene.py before it is moved to --out, and <out>.sha256 is written.

  python3 make_source_zip.py --project <Cocos project> --out <Game_Source_v3.zip> [--top <folder name in the ZIP>]
Exit 0 written, 1 refused (nothing written), 2 bad input. prepare_delivery.py --source checks the same rules.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_hygiene as H  # noqa: E402

JUNK_FILES = {'.ds_store', 'thumbs.db', 'desktop.ini'}


def keep(rel):
    parts = PurePosixPath(rel).parts
    if H.blocked_dir(parts):
        return False
    if len(parts) > 1 and parts[0].lower() in H.CACHE_DIRS:     # project-root caches only
        return False
    name = parts[-1].lower()
    return name not in JUNK_FILES and not name.startswith('._')


def collect(project):
    out = []
    for dirpath, dirs, files in os.walk(project):
        rel_dir = Path(dirpath).relative_to(project)
        dirs[:] = sorted(d for d in dirs if keep((rel_dir / d / 'x').as_posix()))
        for f in sorted(files):
            rel = (rel_dir / f).as_posix()
            if keep(rel) and not (Path(dirpath) / f).is_symlink():
                out.append(rel)
    return out


def build(project, out, top=None):
    project, out = Path(project).resolve(), Path(out).resolve()
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    if out.suffix.lower() != '.zip' or out.exists() or out.is_relative_to(project):
        raise ValueError('--out must be a new .zip outside the project')
    names = collect(project)
    skipped_vcs = sorted({v['path'] for v in H.scan_items((r, None) for r in _all_names(project))['vcs_ide']})
    found = H.scan_items((rel, (project / rel).read_bytes() if rel.lower().endswith(H.TEXT_SUFFIXES) else None)
                         for rel in names)
    if found['secrets']:
        return {'status': 'refused', 'written': False, 'project': str(project),
                'problems': ['%s: %s' % (s['path'], s['why']) for s in found['secrets']],
                'fix': 'remove these files from the project or blank the values, then run again'}
    top = top or project.name
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.source-', suffix='.zip', dir=out.parent)
    os.close(fd)
    tmp = Path(tmp)
    try:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for rel in names:
                z.write(project / rel, '%s/%s' % (top, rel))
        check = H.audit(tmp)
        if not check['passed']:
            raise ValueError('the written ZIP is not clean: ' + '; '.join(check['problems'][:5]))
        with zipfile.ZipFile(tmp) as z:
            if z.testzip() is not None:
                raise ValueError('CRC check failed on the written ZIP')
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink()
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    Path(str(out) + '.sha256').write_text('%s  %s\n' % (digest, out.name), encoding='utf-8')
    return {'status': 'written', 'written': True, 'zip': str(out), 'sha256': digest, 'files': len(names),
            'left_out_vcs_ide': skipped_vcs, 'source_hygiene': 'pass'}


def _all_names(project):
    for p in project.rglob('*'):
        rel = p.relative_to(project).as_posix()
        if p.is_file() or p.name == '.git':
            yield rel


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--top', help='folder name inside the ZIP (default: the project folder name)')
    a = ap.parse_args()
    try:
        r = build(a.project, a.out, a.top)
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r['written'] else 1


if __name__ == '__main__':
    sys.exit(main())
