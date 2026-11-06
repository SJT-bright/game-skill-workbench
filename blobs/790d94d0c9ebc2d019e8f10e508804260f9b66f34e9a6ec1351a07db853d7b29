#!/usr/bin/env python3
"""原始输入只读保留（简化.11.14 R4D，普查 T21:original_source_deleted）。

火柴人密室逃脱清理旧版本时，把最初的中文原包和中文解压目录一起删了，之后没法对照原版。所以：
  - 开工（unpack_source.py）先把原始输入（中文原包 ZIP 或原文件夹）原样复制进游戏文件夹的 `_原始输入/`，
    登记每个文件的 SHA-256（`_原始输入/原始输入登记.json`），再把这份副本设成只读；
  - 清理旧版本只用 clean_old_versions.py：`_原始输入/`、装着它的文件夹、登记过的原包一律跳过；
    手写 rm -rf / shutil.rmtree 删到它时，只读权限让删除失败（macOS / Linux 目录只读；Windows 文件只读）。
  - 要真删原始输入只能由用户自己做，AI 不做。

  python3 raw_inputs.py keep   --source <中文原包.zip 或文件夹> --game-folder <游戏文件夹>
  python3 raw_inputs.py verify --game-folder <游戏文件夹>       # 原始输入还在、没被改过
退出码：0 正常；1 verify 发现缺了或被改；2 参数错误。只用标准库，Windows / macOS / Linux 都能跑。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time
import zipfile

RAW_DIR = '_原始输入'
RECORD = '原始输入登记.json'
SCHEMA = 'raw-inputs.v1'


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _files(root):
    root = Path(root)
    if root.is_file():
        return {root.name: _sha(root)}
    return {p.relative_to(root).as_posix(): _sha(p) for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}


def is_protected(path):
    """True when removing / moving `path` would remove an original input: it is inside `_原始输入/`, it is that
    folder, or it is a folder that contains one (any depth)."""
    path = Path(path)
    if RAW_DIR in path.parts:
        return True
    if path.is_dir() and not path.is_symlink():
        try:
            return any(p.name == RAW_DIR for p in path.rglob(RAW_DIR))
        except OSError:
            return True
    return False


def _set_read_only(target):
    target = Path(target)
    if target.is_file():
        os.chmod(target, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
        return
    for p in sorted(target.rglob('*'), key=lambda x: len(x.parts), reverse=True):
        if p.is_symlink():
            continue
        os.chmod(p, (stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH) | (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH if p.is_dir() else 0))
    os.chmod(target, stat.S_IREAD | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


def _writable(folder):
    os.chmod(folder, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


def read_record(raw):
    try:
        data = json.loads((Path(raw) / RECORD).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) and data.get('schema') == SCHEMA else None
    except (OSError, ValueError):
        return None


def zip_problem(path):
    """R4N3 (补查2 第 15 组, 弹球传奇 原包 ZIP 尾部截断): None when `path` is not a ZIP or reads back whole;
    otherwise one line saying what is wrong. A ZIP is read in full once (zipfile.testzip: every member's CRC)."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with open(path, 'rb') as f:
            head = f.read(4)
    except OSError as exc:
        return '原包读不出来：%s' % exc
    if path.suffix.lower() != '.zip' and head[:2] != b'PK':
        return None
    if not zipfile.is_zipfile(path):
        return ('原包 ZIP 结尾的目录信息缺失（%d 字节），多半是下载或复制时被截断，解压不出完整工程' % path.stat().st_size)
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
    except (zipfile.BadZipFile, EOFError, OSError, ValueError, NotImplementedError, RuntimeError) as exc:
        return '原包 ZIP 读到一半出错（%s），多半是被截断或损坏' % exc
    return None if bad is None else '原包 ZIP 里的 %s 校验不对（CRC），这份原包已损坏' % bad


def keep(source, game_folder):
    """Copy `source` (ZIP or folder) into <game_folder>/_原始输入/ once, record hashes, make the copy read-only.
    A source already inside a `_原始输入/` folder, or the same bytes already kept, is not copied again.
    -> {'status': 'kept' | 'already_kept', 'raw_dir', 'copy', 'files', 'sha256'}"""
    source = Path(source).resolve()
    game_folder = Path(game_folder).resolve()
    if not source.exists():
        raise ValueError('source not found: %s' % source)
    if RAW_DIR in source.parts:
        return {'status': 'already_kept', 'raw_dir': _raw_of(source), 'copy': str(source), 'files': len(_files(source))}
    bad = zip_problem(source)  # R4N3: a broken original is reported now and never becomes the read-only baseline
    if bad:
        raise ValueError('%s：%s。这份不登记、不解压；请用户重新发一份原包（或从原来的地方再下载一次），'
                         '拿到后再跑一次。' % (bad, source))
    raw = game_folder / RAW_DIR
    record = read_record(raw) or {'schema': SCHEMA, 'note': '原始输入，只读；清理旧版本一律跳过。AI 不删、不改。',
                                  'entries': []}
    hashes = _files(source)
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    for entry in record['entries']:
        if entry.get('content_sha256') == digest and (raw / entry.get('name', '\0')).exists():
            return {'status': 'already_kept', 'raw_dir': str(raw), 'copy': str(raw / entry['name']), 'files': len(hashes),
                    'sha256': digest}
    raw.mkdir(parents=True, exist_ok=True)
    _writable(raw)
    name, n = source.name, 2
    while (raw / name).exists():
        name = '%s (%d)%s' % (Path(source.name).stem, n, Path(source.name).suffix) if source.is_file() else '%s (%d)' % (source.name, n)
        n += 1
    target = raw / name
    if source.is_file():
        shutil.copy2(source, target)
    else:
        shutil.copytree(source, target, symlinks=True)
    copied = _files(target)
    if copied != hashes:
        raise OSError('raw input copy differs from the source: %s' % target)
    record['entries'].append({'name': name, 'source': str(source), 'kind': 'file' if source.is_file() else 'folder',
                              'time': time.strftime('%Y-%m-%d %H:%M:%S %z'), 'content_sha256': digest,
                              'files': hashes})
    rec = raw / RECORD
    if rec.exists():
        os.chmod(rec, stat.S_IREAD | stat.S_IWRITE)
    rec.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    _set_read_only(target)
    os.chmod(rec, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    _set_read_only_dir(raw)
    return {'status': 'kept', 'raw_dir': str(raw), 'copy': str(target), 'files': len(hashes), 'sha256': digest}


def _raw_of(path):
    parts = Path(path).parts
    i = len(parts) - 1 - parts[::-1].index(RAW_DIR)
    return str(Path(*parts[:i + 1]))


def _set_read_only_dir(folder):
    os.chmod(folder, stat.S_IREAD | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


def verify(game_folder):
    """-> {'status': 'ok' | 'missing' | 'changed' | 'none', 'problems': [...]}"""
    raw = Path(game_folder).resolve() / RAW_DIR
    record = read_record(raw)
    if record is None:
        return {'status': 'none', 'problems': ['no %s/%s in %s' % (RAW_DIR, RECORD, game_folder)]}
    problems = []
    for entry in record.get('entries', []):
        target = raw / entry['name']
        if not target.exists():
            problems.append('原始输入不见了：%s' % target)
            continue
        now = _files(target)
        for rel, sha in entry['files'].items():
            if now.get(rel) != sha:
                problems.append('原始输入被改或缺文件：%s/%s' % (entry['name'], rel))
    status = 'ok' if not problems else ('missing' if any('不见了' in p for p in problems) else 'changed')
    return {'status': status, 'problems': problems[:50], 'raw_dir': str(raw)}


def unlock_for_test_cleanup(folder):
    """Tests only: make a temp fixture tree removable again. Never call this on a real game folder."""
    for p in [Path(folder)] + list(Path(folder).rglob('*')):
        if not p.is_symlink():
            try:
                os.chmod(p, stat.S_IRWXU)
            except OSError:
                pass


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    k = sub.add_parser('keep')
    k.add_argument('--source', type=Path, required=True)
    k.add_argument('--game-folder', type=Path, required=True)
    v = sub.add_parser('verify')
    v.add_argument('--game-folder', type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        r = keep(a.source, a.game_folder) if a.cmd == 'keep' else verify(a.game_folder)
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 1 if a.cmd == 'verify' and r['status'] in ('missing', 'changed') else 0


if __name__ == '__main__':
    sys.exit(main())
