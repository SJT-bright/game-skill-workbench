#!/usr/bin/env python3
"""英化开工：把中文源码（ZIP 或文件夹）放进工作目录，不带 .git 这类东西（简化.11.6，Saul 2026-11-04）。

91_SLS11海洋逃脱 卖家给的 SLS11.zip 里带着完整的 .git，提交记录里有上架文案 app_desc.txt（开发者账号和密码）。
所以英化开工不要直接 unzip / cp 中文源码，用这个脚本：
  - 不拷：.git .svn .hg .bzr CVS、.idea .vscode .vs .history .fleet、__MACOSX、.DS_Store、._*；
  - 不拷：凭据文件 app_desc.txt、.env、签名证书和私钥（*.keystore *.jks *.p12 *.pfx *.pem *.mobileprovision）；
  - 拷了但要处理：文本里像账号密码的行（例如 settings/project.json 的 appSecret），列在结果里，交源码前把值清空，
    不然 make_source_zip.py 和 prepare_delivery.py 会拒绝；
  - 原 ZIP / 原文件夹一个字节不动；结果写进 <工作目录>/docs/source-intake.json。

  python3 unpack_source.py --source <中文源码.zip 或文件夹> --out <新的工作目录>
  （ZIP 里只有一个顶层文件夹时，工作目录就是它里面那一层）
退出码：0 干净；1 拷好了，但有要处理的凭据行；2 参数错误（--out 已存在、不是 ZIP 也不是文件夹）。
"""
import argparse
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'remake-core' / 'scripts'))
import source_hygiene as H  # noqa: E402

JUNK = {'.ds_store', 'thumbs.db', 'desktop.ini'}


def decide(rel, data):
    """-> ('copy' | 'skip_vcs' | 'skip_secret' | 'skip_junk', reason)"""
    parts = PurePosixPath(rel).parts
    hit = H.blocked_dir(parts)
    if hit:
        return 'skip_vcs', '%s folder %s' % (hit[0], hit[1])
    name = parts[-1].lower()
    if name in JUNK or name.startswith('._'):
        return 'skip_junk', 'Finder / Windows junk'
    why = H.secret_reason(rel, None)          # by name only: credential files are never copied
    if why:
        return 'skip_secret', why
    return 'copy', None


def strip_top(names):
    tops = {PurePosixPath(n).parts[0] for n in names if PurePosixPath(n).parts}
    real = [t for t in tops if t.lower() != '__macosx']
    if len(real) == 1 and all(len(PurePosixPath(n).parts) > 1 or PurePosixPath(n).parts[0].lower() == '__macosx'
                              for n in names if PurePosixPath(n).parts[0] == real[0]):
        return real[0] + '/'
    return ''


def unpack(source, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError('--out already exists: %s (choose a new folder; nothing is overwritten)' % out)
    if source.is_dir() and out.is_relative_to(source):
        raise ValueError('--out must be outside the source folder')
    rows = {'copied': 0, 'skipped_vcs_ide': set(), 'skipped_secrets': [], 'skipped_junk': 0}
    tmp = out.with_name(out.name + '.partial')
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        if source.is_dir():
            items = [(p.relative_to(source).as_posix(), p) for p in sorted(source.rglob('*'))
                     if p.is_file() and not p.is_symlink() or p.name == '.git']
            prefix = ''
            reader = lambda p: p.read_bytes()   # noqa: E731
        elif zipfile.is_zipfile(source):
            z = zipfile.ZipFile(source)
            infos = [i for i in z.infolist() if not i.is_dir()]
            prefix = strip_top([i.filename for i in infos])
            items = [(i.filename, i) for i in infos]
            reader = z.read
        else:
            raise ValueError('--source is not a ZIP or a folder: %s' % source)
        for rel, handle in items:
            what, why = decide(rel, None)
            if what == 'skip_vcs':
                parts = PurePosixPath(rel).parts
                i = [p.lower() for p in parts].index(H.blocked_dir(parts)[1].lower())
                rows['skipped_vcs_ide'].add('/'.join(parts[:i + 1]))
                continue
            if what == 'skip_junk':
                rows['skipped_junk'] += 1
                continue
            if what == 'skip_secret':
                rows['skipped_secrets'].append({'path': rel, 'why': why})
                continue
            if prefix and not rel.startswith(prefix):
                continue
            target_rel = rel[len(prefix):]
            parts = PurePosixPath(target_rel).parts
            if not target_rel or target_rel.startswith('/') or '..' in parts:
                raise ValueError('unsafe path in the source: %r' % rel)
            dest = tmp.joinpath(*parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if hasattr(handle, 'is_file') and handle.name == '.git' and not handle.is_file():
                continue
            dest.write_bytes(reader(handle))
            rows['copied'] += 1
        if not (tmp / 'assets').is_dir():
            raise ValueError('no assets/ folder after unpacking: is this a Cocos project? (%s)' % source)
        left = H.scan_items(H.iter_folder(tmp))
        tmp.rename(out)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
    record = {'tool': 'unpack_source', 'schema': 1, 'time': time.strftime('%Y-%m-%d %H:%M:%S %z'),
              'source': str(source), 'out': str(out), 'copied_files': rows['copied'],
              'left_out_vcs_ide': sorted(rows['skipped_vcs_ide']), 'left_out_credential_files': rows['skipped_secrets'],
              'left_out_junk_files': rows['skipped_junk'],
              'credential_lines_to_clean': left['secrets'],
              'status': 'clean' if not left['secrets'] and not left['vcs_ide'] else 'clean_before_delivery',
              'next': ('nothing to do' if not left['secrets'] else
                       'blank these values (or remove the files) before any source ZIP; make_source_zip.py and '
                       'prepare_delivery.py refuse them')}
    (out / 'docs').mkdir(exist_ok=True)
    (out / 'docs' / 'source-intake.json').write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n',
                                                    encoding='utf-8')
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    try:
        r = unpack(a.source, a.out)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r['status'] == 'clean' else 1


if __name__ == '__main__':
    sys.exit(main())
