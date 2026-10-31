#!/usr/bin/env python3
"""After a package is written: older packages of the SAME game go into 旧包/, the folder keeps this one package and
最新.txt (v7.8, 总表 B32 b; 剪刀达人's delivery folder had dozens of ZIPs and Saul had to guess which one to upload).

Both writers (make_tiktok_zip.py, build_checked_zip.py) call tidy() right after the new ZIP and its receipt are
published. Only files the writer can recognise are moved:
  * another .zip in the same folder (not in subfolders) that is a TikTok upload package (game.js, game.json and
    project.config.json at its root), whose project.config.json appid equals the new package's App ID, and that shares
    at least 30 % of the game's own files with the new package (paths outside the root files, cocos/, src/ and the
    engine's assets/internal/: the asset uuids). Calibration 2026-10-30: versions of one game share 41 %-100 %
    (DriftRacer3D v1 vs v3.1 41 %), two different games at most 3 %; most games use the same test App ID, so the App ID
    alone never decides;
  * with it, its receipt <zip>.receipt.json and the make_tiktok_zip report <zip stem>.report.json, when present.
Everything else (source ZIPs, trial folders, delivery receipts, notes, other games' packages, unreadable ZIPs) is left
exactly where it is. A name already taken in 旧包/ gets " (2)", " (3)" ...; nothing is overwritten or deleted.
最新.txt says which file to upload (full path), its sha256, size and time, and which files were moved. An existing
最新.txt that this tool did not write is left alone (reported).

  python3 delivery_folder.py --zip <new package.zip> --app-id <App ID> [--apply]     # without --apply: list only
Opt out (e.g. a writer-refusal test ZIP written into the delivery folder): writer flag --keep-old-packages or
TIKTOK_KEEP_OLD_PACKAGES=1.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile

OLD_DIR = '旧包'
LATEST = '最新.txt'
MARK = '# 最新包（写包入口自动写，每次出包更新；不要手改）'
ROOT_FILES = ('game.js', 'game.json', 'project.config.json')
MIN_SHARED = 0.3
ENGINE_PREFIXES = ('assets/internal/', 'cocos/', 'src/', 'cocos-js/')
ENV_KEEP = 'TIKTOK_KEEP_OLD_PACKAGES'


def _names_and_appid(path):
    """(set of file names, appid) of a TikTok upload ZIP, or None when it is not one (or unreadable)."""
    try:
        with zipfile.ZipFile(path) as z:
            names = {i.filename for i in z.infolist() if not i.is_dir()}
            if not all(n in names for n in ROOT_FILES):
                return None
            config = json.loads(z.read('project.config.json').decode('utf-8-sig'))
    except (OSError, zipfile.BadZipFile, ValueError, KeyError, UnicodeDecodeError, RuntimeError):
        return None
    app = config.get('appid') if isinstance(config, dict) else None
    return names, app if isinstance(app, str) else None


def own_files(names):
    """The game's own files: not root files, not the engine and its internal bundle (shared by every Cocos game)."""
    return {n for n in names if '/' in n and not n.startswith(ENGINE_PREFIXES)}


def plan(new_zip, app_id=None):
    """What tidy() would do. -> {'folder', 'new', 'app_id', 'move': [{'zip', 'with': [...], 'shared'}],
    'left': [{'file', 'why'}]}. Read only."""
    new_zip = Path(new_zip).resolve()
    folder = new_zip.parent
    if not new_zip.is_file():
        raise ValueError('%s not found' % new_zip)
    mine = _names_and_appid(new_zip)
    if mine is None:
        raise ValueError('%s is not a TikTok upload package (game.js, game.json, project.config.json at its root)' % new_zip)
    names, own_app = mine
    app_id = app_id or own_app
    out = {'folder': str(folder), 'new': str(new_zip), 'app_id': app_id, 'move': [], 'left': []}
    if not app_id:
        out['left'].append({'file': new_zip.name, 'why': 'the new package has no appid: nothing can be matched'})
        return out
    for path in sorted(folder.iterdir()):
        if path == new_zip or not path.is_file() or path.is_symlink() or path.suffix.lower() != '.zip' \
                or path.name.startswith('.'):          # the writers' own .tiktok-package-*.zip temp links
            continue
        try:
            if path.samefile(new_zip):                 # a hard link of the new package is the new package
                continue
        except OSError:
            continue
        other = _names_and_appid(path)
        if other is None:
            out['left'].append({'file': path.name, 'why': 'not a TikTok upload package (source ZIP or unreadable)'})
            continue
        other_names, other_app = other
        if other_app != app_id:
            out['left'].append({'file': path.name, 'why': 'other App ID %s' % other_app})
            continue
        a, b = own_files(names), own_files(other_names)
        shared = len(a & b) / max(1, min(len(a), len(b)))
        if shared < MIN_SHARED:
            out['left'].append({'file': path.name, 'why': 'same App ID but only %d%% of its own files are in the new package '
                                '(another game)' % round(shared * 100)})
            continue
        extra = [p.name for p in (path.with_name(path.name + '.receipt.json'), path.with_name(path.stem + '.report.json'))
                 if p.is_file() and not p.is_symlink()]
        out['move'].append({'zip': path.name, 'with': extra, 'shared': round(shared, 3)})
    return out


def _free_name(folder, name):
    target = folder / name
    if not target.exists():
        return target
    stem, suffix = (name[:-len('.receipt.json')], '.receipt.json') if name.endswith('.receipt.json') else \
        (Path(name).stem, Path(name).suffix)
    for n in range(2, 1000):
        target = folder / ('%s (%d)%s' % (stem, n, suffix))
        if not target.exists():
            return target
    raise OSError('no free name for %s in %s' % (name, folder))


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def latest_text(new_zip, sha256, tool, moved):
    new_zip = Path(new_zip)
    lines = [MARK,
             '上传 TikTok 用这个：%s' % new_zip,
             'sha256：%s' % sha256,
             '大小：%d 字节' % new_zip.stat().st_size,
             '写包时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S %z'),
             '写包入口：%s（回执 %s）' % (tool, new_zip.name + '.receipt.json'),
             '源码包、试玩文件夹不能上传。']
    if moved:
        lines.append('这次挪进 %s/ 的旧包：' % OLD_DIR)
        lines += ['  - %s' % m for m in moved]
    return '\n'.join(lines) + '\n'


def tidy(new_zip, app_id=None, tool='writer', sha256=None, keep=False):
    """Move older same-game packages into 旧包/ and write 最新.txt. Never raises for a move problem: the new package is
    already written; problems are listed in 'errors'. -> {'planned', 'moved': [{'from', 'to'}], 'latest', 'errors',
    'left', 'skipped'}."""
    new_zip = Path(new_zip).resolve()
    result = {'moved': [], 'latest': None, 'errors': [], 'left': [], 'skipped': None}
    if keep or os.environ.get(ENV_KEEP) == '1':
        result['skipped'] = '--keep-old-packages / %s=1: old packages left in place, 最新.txt not written' % ENV_KEEP
        return result
    try:
        p = plan(new_zip, app_id)
    except ValueError as error:
        result['errors'].append(str(error))
        return result
    result['planned'] = p['move']
    result['left'] = p['left']
    old = new_zip.parent / OLD_DIR
    names = []
    for item in p['move']:
        for name in [item['zip']] + item['with']:
            src = new_zip.parent / name
            try:
                old.mkdir(exist_ok=True)
                dest = _free_name(old, name)
                os.rename(src, dest)          # same folder tree: a rename, never a copy over something
                result['moved'].append({'from': str(src), 'to': str(dest)})
                names.append(name if dest.name == name else '%s -> %s' % (name, dest.name))
            except OSError as error:
                result['errors'].append('could not move %s: %s' % (name, error))
    latest = new_zip.parent / LATEST
    try:
        if latest.exists() and not latest.read_text(encoding='utf-8', errors='replace').startswith(MARK):
            result['errors'].append('%s exists and was not written by the writer: left alone (write it yourself or remove it)' % latest)
        else:
            tmp = latest.with_name('.' + LATEST + '.tmp')
            tmp.write_text(latest_text(new_zip, sha256 or _sha(new_zip), tool, names), encoding='utf-8')
            os.replace(tmp, latest)
            result['latest'] = str(latest)
    except OSError as error:
        result['errors'].append('could not write %s: %s' % (latest, error))
    return result


def describe(result):
    """Chinese lines for the writer's console output."""
    if result.get('skipped'):
        return ['旧包没挪：' + result['skipped']]
    out = []
    planned = result.get('planned') or []
    if planned:
        out.append('挪进 %s/ 的同款旧包（%d 个）：' % (OLD_DIR, len(planned)))
        out += ['  - %s%s' % (m['zip'], ('（连同 ' + '、'.join(m['with']) + '）') if m['with'] else '') for m in planned]
    else:
        out.append('交付文件夹里没有同款旧包要挪')
    if result.get('latest'):
        out.append('最新.txt：%s' % result['latest'])
    out += ['没挪成：' + e for e in result.get('errors') or []]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--zip', type=Path, required=True, help='the new package (already written by a writer)')
    ap.add_argument('--app-id')
    ap.add_argument('--apply', action='store_true', help='move and write 最新.txt (default: list only)')
    a = ap.parse_args()
    if not a.apply:
        try:
            print(json.dumps(plan(a.zip, a.app_id), ensure_ascii=False, indent=1))
            return 0
        except ValueError as error:
            print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False))
            return 1
    result = tidy(a.zip, a.app_id, 'delivery_folder.py')
    print('\n'.join(describe(result)))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
