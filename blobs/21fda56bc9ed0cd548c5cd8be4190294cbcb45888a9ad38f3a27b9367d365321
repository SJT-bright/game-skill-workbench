#!/usr/bin/env python3
"""Is every picture in a Cocos Web export the one the project has now? (English pack 10.2.7, Saul 2026-10-31) Read-only.

Cube Digits (10-31 01:09 and 02:53) twice showed an export that still had the old PNGs after the art was replaced, and
each time cost a round of looking, rebuilding and looking again. Cocos names an exported picture after the uuid in its
.meta (2.4: assets/<bundle>/native/<2 chars>/<uuid>.<md5>.png; 3.x the same with the 3.x image uuid) and copies the
bytes unchanged, so an exported file can be matched to its project file and compared.

A project picture is reported as OLD (exit 1) when no exported file of its uuid has its bytes, and an exported one
  * is older than the project file (it was exported before the picture was replaced), or
  * has the bytes of a pre-English original (docs/english/pre-english-images.json) while the project file has not
    (the export still shows the Chinese original).
A differing exported file that is newer and is not an original is only a note (the engine may have compressed it), and
so is an old leftover file lying next to a current one. Exported pictures under no project uuid (engine pictures,
auto-atlas pages) are counted, not judged.

Calibrated 2026-10-31 on exports on Saul's Mac: OceanBubbleMerge 2.4.15 (15 matched, all current), Cube Digits 3.7.1
three exports (30 / 76 / 154 matched, all current), ReefGuard 2.4.15 build/web-mobile (3 pictures older than the
project, reported).

  python3 check_export_images.py --project <Cocos project> --export <web-mobile export folder> [--pre-english <json>]
Exit 0 every matched picture is current, 1 old pictures found, 2 bad input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp')
UUID = re.compile(r'^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', re.I)
HEX64 = re.compile(r'^[0-9a-f]{64}$')
SKIP_DIRS = {'library', 'temp', 'build', 'node_modules', '.git'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project_images(project):
    """{uuid: picture path} for every picture under <project>/assets that has a readable .meta with a uuid."""
    out = {}
    for meta in sorted((project / 'assets').rglob('*.meta')):
        picture = meta.with_name(meta.name[:-len('.meta')])
        if picture.suffix.lower() not in IMAGE_SUFFIXES or not picture.is_file():
            continue
        if SKIP_DIRS & set(meta.relative_to(project).parts):
            continue
        try:
            uuid = json.loads(meta.read_text(encoding='utf-8')).get('uuid')
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(uuid, str) and UUID.match(uuid):
            out[uuid.lower()] = picture
    return out


def originals(path):
    """SHA-256 strings of the pre-English pictures: {"images": {sha: path}} (make-list) or {"images": {path: sha}}."""
    if path is None or not Path(path).is_file():
        return set()
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    found = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(k)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str) and HEX64.match(x.lower()):
            found.add(x.lower())

    walk(doc.get('images', doc) if isinstance(doc, dict) else doc)
    return found


def check(project, export, pre_english=None):
    project, export = Path(project), Path(export)
    if not (project / 'assets').is_dir():
        raise ValueError('不是 Cocos 工程（没有 assets/）：%s' % project)
    if not export.is_dir():
        raise ValueError('找不到导出目录：%s' % export)
    if pre_english is None:
        default = project / 'docs' / 'english' / 'pre-english-images.json'
        pre_english = default if default.is_file() else None
    orig = originals(pre_english)
    sources = project_images(project)
    groups = {}
    result = {'exported': 0, 'matched': 0, 'current': 0, 'unmatched': 0, 'old': [], 'notes': [],
              'pre_english': str(pre_english) if pre_english else None}
    for f in sorted(export.rglob('*')):
        if not f.is_file() or f.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        result['exported'] += 1
        m = UUID.match(f.name)
        uuid = m.group(1).lower() if m else None
        if uuid not in sources:
            result['unmatched'] += 1
            continue
        result['matched'] += 1
        groups.setdefault(uuid, []).append(f)
    for uuid, files in sorted(groups.items()):
        src = sources[uuid]
        src_sha, src_time = sha(src), src.stat().st_mtime
        rel_src = src.relative_to(project).as_posix()
        rows = [(f, sha(f)) for f in files]
        current = [f for f, s in rows if s == src_sha]
        result['current'] += len(current)
        for f, s in rows:
            if s == src_sha:
                continue
            row = {'export': f.relative_to(export).as_posix(), 'project': rel_src}
            stale = (s in orig and src_sha not in orig) or f.stat().st_mtime < src_time
            if current:
                row['why'] = '导出目录里还留着这张图的旧文件，游戏用的是新的；清掉导出目录再构建更干净'
                result['notes'].append(row)
            elif stale:
                row['why'] = '导出里还是英化前的原图' if s in orig and src_sha not in orig else \
                    '导出的图比工程里的旧（换图后没有重新导出）'
                result['old'].append(row)
            else:
                row['why'] = '导出的图和工程里的不一样，但比工程里的新，可能是引擎压缩过，不算旧图'
                result['notes'].append(row)
    result['passed'] = not result['old']
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description='核对 Cocos Web 导出里的图是不是工程里现在的图（只读）')
    ap.add_argument('--project', required=True, type=Path, help='Cocos 工程（有 assets/ 的那一层）')
    ap.add_argument('--export', required=True, type=Path, help='这次的 web-mobile 导出目录')
    ap.add_argument('--pre-english', type=Path, help='英化前的图片清单（默认 <工程>/docs/english/pre-english-images.json）')
    ap.add_argument('--json', action='store_true', help='输出完整结果 JSON')
    a = ap.parse_args(argv)
    try:
        r = check(a.project, a.export, a.pre_english)
    except (OSError, ValueError) as error:
        print('输入有问题：%s' % error)
        return 2
    if r['exported'] == 0:
        print('导出目录里一张图都没有：%s。先确认导出成功了。' % a.export)
        return 2
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print('导出里 %d 张图，%d 张对得上工程里的图：%d 张是新的，%d 张是旧图；%d 张对不上（引擎自带的图或自动图集，不查）。'
              % (r['exported'], r['matched'], r['current'], len(r['old']), r['unmatched']))
        if r['matched'] == 0:
            print('一张都没对上：看看 --project 和 --export 是不是同一款游戏；这款的图全打进自动图集时本脚本查不了，换图后看截图确认。')
        for row in r['old']:
            print('  旧图：%s（工程里是 %s）：%s' % (row['export'], row['project'], row['why']))
        for row in r['notes'][:10]:
            print('  提示：%s（工程里是 %s）：%s' % (row['export'], row['project'], row['why']))
        if r['old']:
            print('删掉这次的导出目录，重新构建，再跑一次本脚本，到 0 张旧图再给试玩链接。')
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
