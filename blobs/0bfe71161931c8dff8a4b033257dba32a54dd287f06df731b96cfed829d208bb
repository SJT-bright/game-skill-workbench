#!/usr/bin/env python3
"""Which package is this? (音乐消消乐复盘 2026-11-05). READ ONLY.

Two AIs worked on MusicSlice at the same time from the same source and both called their builds v30 / v31; Saul renamed
both upload ZIPs to 音乐消消乐.zip. On 11-04 a phone report came with a renamed ZIP and the session that got it said
"this is an old package, use v31" -- it was the newest build of the OTHER line (v32, with revive, x2 and the ad fixes
that v31 lacks). File names and version numbers do not identify a build. Bytes and Cocos asset uuids do.

    python3 which_package.py --zip <the ZIP from the phone / the one you are about to work on> \
        --roots <every folder that holds this game's projects or packages> [--roots ...] [--out result.json]
    python3 which_package.py --project <Cocos project or package folder> --roots ...   (start of work: lines)

1. Same bytes: every ZIP under the roots with the same SHA-256, and every *.receipt.json whose sha256 is it
   (writer / prepare_delivery receipts), whatever the file is called now.
2. Same game: every TikTok ZIP, built package folder and Cocos project under the roots that shares Cocos asset uuids
   with it (the frozen legacy list rule: LINK_MIN uuids and LINK_SHARE of the smaller one; a source against a build
   SOURCE_SHARE, because the editor gives packed atlases new uuids), newest first, with how many files differ (ZIP
   CRC, built packages only) and whether main.js / game.js / the adapter differ.
3. Lines: when the same game sits in two or more top folders under the roots, it says so: there may be two lines of
   work with the same version numbers; find out which one is current before changing anything.
Exit codes: 0 done (also when nothing matched), 2 bad input. The `lines` field is Chinese for the user's reply.
"""
import argparse
import json
import sys
import time
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_legacy_list as M  # noqa: E402

STARTUP_FILES = ('main.js', 'game.js', 'adapter-min.js', 'game.json', 'src/settings.js')
SOURCE_SHARE, SOURCE_MIN = 0.6, 50   # MusicSlice v32 source vs its own build: 267 of 349 uuids shared (77 %)


def zip_crcs(path):
    """name -> CRC32 of a TikTok ZIP; a first-level wrapper folder holding game.json is stripped."""
    with zipfile.ZipFile(path) as z:
        infos = [i for i in z.infolist() if not i.is_dir() and '__MACOSX' not in i.filename]
    names = [i.filename for i in infos]
    top = ''
    if 'game.json' not in names:
        hit = [n for n in names if n.count('/') == 1 and n.endswith('/game.json')]
        if hit:
            top = hit[0][:-len('game.json')]
    return {i.filename[len(top):]: i.CRC for i in infos if i.filename.startswith(top)}


def dir_crcs(path):
    out = {}
    for p in Path(path).rglob('*'):
        if p.is_file() and not (M.SKIP_DIRS & set(p.relative_to(path).parts)):
            out[p.relative_to(path).as_posix()] = zlib.crc32(p.read_bytes()) & 0xffffffff
    return out


def scan(roots, max_depth=6):
    """-> (zips, receipts, packages): every ZIP, receipt and readable package (path, hint) under the roots."""
    zips, receipts, packages, seen = [], [], [], set()
    for root in roots:
        for dirpath, _dirnames, filenames in M.walk(root, max_depth):
            for f in filenames:
                p = Path(dirpath) / f
                if f.endswith('.receipt.json'):
                    receipts.append(p)
                elif f.lower().endswith('.zip') and not f.startswith('._'):
                    zips.append(p)
        for path, hint in M.candidates(root, max_depth):
            key = str(Path(path).resolve())
            if key not in seen:
                seen.add(key)
                packages.append((Path(path), hint))
    return zips, receipts, packages


def top_folder(path, roots):
    for r in roots:
        try:
            rel = Path(path).resolve().relative_to(Path(r).resolve())
        except ValueError:
            continue
        return str(Path(r) / rel.parts[0]) if len(rel.parts) > 1 else str(r)
    return str(Path(path).parent)


def same_game(a, b):
    shared = len(a['assets'] & b['assets']) + len(a['scenes'] & b['scenes'])
    small = min(len(a['assets']) + len(a['scenes']), len(b['assets']) + len(b['scenes']))
    if small <= 0 or shared < M.LINK_MIN:
        return False, shared
    if shared >= M.LINK_SHARE * small:
        return True, shared
    mixed = {a.get('kind'), b.get('kind')} == {'source', 'native'}
    return mixed and shared >= SOURCE_MIN and shared >= SOURCE_SHARE * small, shared


def when(ts):
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(ts)) if ts else '?'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--zip', help='the ZIP to identify (the phone one, or the one you are about to work on)')
    src.add_argument('--project', help='a Cocos project or built package folder (start of work)')
    ap.add_argument('--roots', action='append', default=[], help='folder holding this game; repeat for every one')
    ap.add_argument('--max-depth', type=int, default=6)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    target = Path(a.zip or a.project).expanduser()
    roots = [Path(r).expanduser() for r in a.roots if Path(r).expanduser().exists()]
    if not target.exists() or not roots:
        print('need an existing --zip/--project and at least one existing --roots', file=sys.stderr)
        return 2
    hint = 'zip' if target.is_file() else ('native_dir' if (target / 'game.json').is_file() else 'project_dir')
    me = M.read_package(target, hint)
    if me.get('error'):
        print('cannot read %s: %s' % (target, me['error']), file=sys.stderr)
        return 2
    my_sha = M.file_sha(target) if target.is_file() else None
    my_pkg = hint == 'native_dir' or (hint == 'zip' and M.tiktok_zip(target))
    my_crc = (zip_crcs(target) if hint == 'zip' else dir_crcs(target)) if my_pkg else None
    zips, receipts, packages = scan(roots, a.max_depth)
    self_key = str(target.resolve())
    exact = [str(z) for z in zips if my_sha and str(z.resolve()) != self_key and z.stat().st_size == target.stat().st_size
             and M.file_sha(z) == my_sha]
    receipts_hit = []
    for r in receipts:
        try:
            data = json.loads(r.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if my_sha and isinstance(data, dict) and data.get('sha256') == my_sha:
            receipts_hit.append({'receipt': str(r), 'status': data.get('status'), 'archive': data.get('archive')})
    rows = []
    for path, h in packages:
        if str(path.resolve()) == self_key:
            continue
        other = M.read_package(path, h)
        if other.get('error'):
            continue
        ok, shared = same_game(me, other)
        if not ok:
            continue
        row = {'path': str(path), 'kind': h, 'mtime': other['mtime'], 'when': when(other['mtime']), 'shared_uuids': shared,
               'folder': top_folder(path, roots)}
        if h == 'zip':
            row['sha256'] = M.file_sha(path)
            row['same_bytes'] = row['sha256'] == my_sha
        row['tiktok_package'] = h == 'native_dir' or (h == 'zip' and M.tiktok_zip(path))
        crc = None
        try:   # file differences only between built packages (a source ZIP has other file names)
            crc = (zip_crcs(path) if h == 'zip' else dir_crcs(path)) if row['tiktok_package'] else None
        except (zipfile.BadZipFile, OSError):
            pass
        if crc is not None and my_crc is not None:
            diff = sorted(n for n in set(crc) | set(my_crc) if crc.get(n) != my_crc.get(n))
            row['files_differ'] = len(diff)
            row['startup_files_differ'] = [n for n in STARTUP_FILES if n in diff]
        rows.append(row)
    rows.sort(key=lambda r: -r['mtime'])
    # file time only: a copy (WeChat, a download) is newer than its original, so a copy with 0 differing files is not
    # "newer"; the user decides which line is current, this only lists what exists
    newer = [r for r in rows if r['mtime'] > me['mtime'] + 60 and not r.get('same_bytes') and r.get('files_differ') != 0]
    folders = {top_folder(target, roots)}
    folders |= {r['folder'] for r in rows}
    lines = []
    if a.zip:
        if exact or receipts_hit:
            lines.append('这个包和下面的文件逐字节相同（不管现在叫什么名字）：' + '；'.join(exact + [x['receipt'] for x in receipts_hit]))
        else:
            lines.append('在给的文件夹里没有找到和它逐字节相同的包：它不是这些文件夹里任何一次交付的原件，或者原件放在别处。')
    lines.append('同一款游戏的包和工程一共 %d 个（按 Cocos 资源 uuid 认的）。' % len(rows))
    if newer:
        lines.append('比它新的有 %d 个，最新的是 %s（%s）。' % (len(newer), newer[0]['path'], newer[0]['when']))
    if len(folders) > 1:
        lines.append('这款游戏放在 %d 个地方：%s。可能有两条以上的版本线在同时做，版本号和文件名都可能重复。'
                     '动手前先弄清楚哪一条是现在要用的，不要把另一条当成旧包。' % (len(folders), '；'.join(sorted(folders))))
    for r in rows[:12]:
        extra = ''
        if 'files_differ' in r:
            extra = '，和它差 %d 个文件' % r['files_differ'] + (
                '（启动文件 %s 不同）' % '、'.join(r['startup_files_differ']) if r['startup_files_differ'] else '')
        lines.append('- %s  %s%s%s' % (r['when'], r['path'], '（逐字节相同）' if r.get('same_bytes') else '', extra))
    result = {'target': str(target), 'sha256': my_sha, 'mtime': me['mtime'], 'exact': exact, 'receipts': receipts_hit,
              'same_game': rows, 'newer': [r['path'] for r in newer], 'folders': sorted(folders), 'lines': lines}
    if a.out:
        Path(a.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
