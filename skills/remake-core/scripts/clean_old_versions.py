#!/usr/bin/env python3
"""清理游戏文件夹里的旧版本（简化.11.14 R4D）：唯一允许的清理入口，原始输入一律跳过。

火柴人密室逃脱清理旧版本时连最初的中文原包和解压目录一起删了（普查 T21:original_source_deleted）。清理旧版本只用这个
脚本，不手写 rm -rf / shutil.rmtree：
  - 跳过：`_原始输入/`、装着 `_原始输入/` 的文件夹、`_原始输入/原始输入登记.json` 里登记过的原包（同内容的副本也算）、
    `旧包/`、`最新.txt`，以及 --keep 列出的东西；
  - 其余 --old 列出的文件或文件夹：默认只列出；加 --apply 挪进 `<游戏文件夹>/旧版本/`（重名加 " (2)"），从不删除；
    加 --delete 才删除（仍然跳过上面那些）。

  python3 clean_old_versions.py --game-folder <游戏文件夹> --old <旧版本1> [--old <旧版本2> ...] [--apply | --delete]
退出码：0 正常（跳过的也算正常，列在 skipped 里）；2 参数错误（--old 不在游戏文件夹里）。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import raw_inputs  # noqa: E402

OLD_DIR = '旧版本'
ALWAYS_KEEP = ('旧包', '最新.txt', OLD_DIR)


def _sha(path):
    try:
        return raw_inputs._sha(path)
    except OSError:
        return None


def _registered(game_folder):
    """sha256 of every kept original file (single-file entries), from the raw-input record."""
    record = raw_inputs.read_record(Path(game_folder) / raw_inputs.RAW_DIR) or {}
    return {sha for e in record.get('entries', []) for sha in (e.get('files') or {}).values()}


def plan(game_folder, old, keep=()):
    game_folder = Path(game_folder).resolve()
    keep = {Path(k).resolve() for k in keep}
    registered = _registered(game_folder)
    out = {'game_folder': str(game_folder), 'remove': [], 'skipped': []}
    for item in old:
        p = Path(item).resolve()
        if p != game_folder and game_folder not in p.parents:
            raise ValueError('--old must be inside the game folder: %s' % p)
        if p == game_folder:
            out['skipped'].append({'path': str(p), 'why': '是游戏文件夹本身'})
            continue
        if not p.exists():
            out['skipped'].append({'path': str(p), 'why': '不存在'})
            continue
        if raw_inputs.is_protected(p):
            out['skipped'].append({'path': str(p), 'why': '原始输入（%s/），只读保留，不清理' % raw_inputs.RAW_DIR})
            continue
        if p in keep or p.name in ALWAYS_KEEP:
            out['skipped'].append({'path': str(p), 'why': '要保留（--keep / 旧包 / 最新.txt / 旧版本）'})
            continue
        if p.is_file() and registered and _sha(p) in registered:
            out['skipped'].append({'path': str(p), 'why': '和登记过的原始输入同内容（中文原包），不清理'})
            continue
        out['remove'].append(str(p))
    return out


def _free(folder, name):
    target = folder / name
    n = 2
    while target.exists():
        stem, suffix = (Path(name).stem, Path(name).suffix) if '.' in name else (name, '')
        target = folder / ('%s (%d)%s' % (stem, n, suffix))
        n += 1
    return target


def apply(p, delete=False):
    game_folder = Path(p['game_folder'])
    done, errors = [], []
    for item in p['remove']:
        path = Path(item)
        try:
            if delete:
                shutil.rmtree(path) if path.is_dir() and not path.is_symlink() else path.unlink()
                done.append({'deleted': item})
            else:
                dest_dir = game_folder / OLD_DIR
                dest_dir.mkdir(exist_ok=True)
                dest = _free(dest_dir, path.name)
                os.rename(path, dest)
                done.append({'moved': item, 'to': str(dest)})
        except OSError as error:
            errors.append('%s: %s' % (item, error))
    return done, errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game-folder', type=Path, required=True)
    ap.add_argument('--old', type=Path, action='append', default=[], required=True)
    ap.add_argument('--keep', type=Path, action='append', default=[])
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--apply', action='store_true', help='move into 旧版本/ (never deletes)')
    g.add_argument('--delete', action='store_true', help='delete (original inputs are still skipped)')
    a = ap.parse_args(argv)
    try:
        p = plan(a.game_folder, a.old, a.keep)
    except ValueError as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 2
    if a.apply or a.delete:
        p['done'], p['errors'] = apply(p, delete=a.delete)
    else:
        p['done'] = 'list only (add --apply to move into %s/)' % OLD_DIR
    print(json.dumps(p, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
