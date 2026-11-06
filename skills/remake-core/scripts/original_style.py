#!/usr/bin/env python3
"""保留原画风：英化游戏的深色、纯色美工检查只查新做的图（生成时预防 R4Q3，补查3 第 3 组）。

火箭三消、弹球传奇（11-05）：英化第一轮照原画风，原版本来就是深蓝纯色背景、黑色面板，art_check 的
「大块深色与纯色底」把原图当问题拦下，回执是 fail，写包入口不认会话里记的人工授权；Saul 两次都选了「保留原画风」。
现在：
  - 原图 = 图片 SHA-256 和中文原包里的图相同。原包哈希从两处只读：raw_inputs.py keep 登记的
    `_原始输入/原始输入登记.json`（工程文件夹和它往上两层里找；登记的是 ZIP 时读 ZIP 里每张图的哈希），
    以及 art_records.py base 写的 docs/art/base-assets.json（R4D 之前开工的游戏只有它）。
  - 英化（沿用原画风）：截图里的大块深色/纯色如果只来自原图，这一行记「原图保留，不适用」，不拦、不进回执缺口；
    新做的图（SHA 不在原包里）里有大块纯色或深色的，照拦，并写出是哪几张。
  - 重塑、英化选了重塑画风（docs/art-style.txt = remake）：照旧拦（feature_policy 的 dark_flat_original 行）。
  - docs/art/keep_original_style.json 记 Saul 的选择（谁定的、哪天）。art_check 把它写进报告，art_receipt
    把它写进回执和出包表，写包入口不再要会话里另记人工授权：
      {"schema": "keep-original-style.v1", "decided_by": "Saul", "date": "2026-11-05",
       "why": "保留原画风/原背景", "source": "对话或选择题的出处（可选）"}

  python3 original_style.py --project <工程> [--board localize|remake]     # 只读，打印判断
退出码：0 不拦；1 要拦；2 参数错误。只用标准库（量图要 Pillow，没有就照旧拦）。
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

RULE = 'dark_flat_original'
RECORD = Path('docs') / 'art' / 'keep_original_style.json'
RECORD_SCHEMA = 'keep-original-style.v1'
IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp')
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', '.tiktok-kit', '__macosx'}
DARK_MIN_SIDE = 96          # same size floor as audit_new_english_images.FLAT_MIN_SIDE
DARK_LUMA = 60              # same as FLAT_DARK: mean luma below this on a big opaque picture = a dark block
NEW_MIN_SIDE = 256         # R4Q3: a new picture this big on both sides is a panel / background


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _raw_records(project):
    """`_原始输入/原始输入登记.json` in the project folder or up to two folders above it (unpack_source puts the raw
    copy next to --out, one level up by default)."""
    import raw_inputs
    project = Path(project).resolve()
    out = []
    for folder in (project, project.parent, project.parent.parent):
        raw = folder / raw_inputs.RAW_DIR
        record = raw_inputs.read_record(raw)
        if record is not None:
            out.append((raw, record))
    return out


def original_hashes(project):
    """(set of sha256 of the Chinese original's images, [where they came from]). Read only."""
    shas, sources = set(), []
    for raw, record in _raw_records(project):
        n = len(shas)
        for entry in record.get('entries', []):
            files = entry.get('files') or {}
            for rel, sha in files.items():
                if str(rel).lower().endswith(IMAGE_SUFFIXES):
                    shas.add(str(sha).lower())
            kept = raw / str(entry.get('name', ''))
            if entry.get('kind') == 'file' and kept.is_file() and zipfile.is_zipfile(kept):
                try:
                    with zipfile.ZipFile(kept) as z:
                        for name in z.namelist():
                            if name.lower().endswith(IMAGE_SUFFIXES) and not name.endswith('/'):
                                shas.add(_sha(z.read(name)))
                except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError):
                    pass
        sources.append('%s（%d 张）' % (raw / 'raw_inputs登记', len(shas) - n))
    base = Path(project) / 'docs' / 'art' / 'base-assets.json'
    try:
        doc = json.loads(base.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        doc = None
    if isinstance(doc, dict) and doc.get('kind') == 'base-assets':
        n = len(shas)
        for key in ('images', 'embedded'):
            for v in (doc.get(key) or {}).values():
                if isinstance(v, str):
                    shas.add(v.lower())
        sources.append('docs/art/base-assets.json（%d 张）' % (len(shas) - n))
    return shas, sources


def keep_record(project):
    """The keep_original_style.json record when it names who decided and when, else None."""
    try:
        doc = json.loads((Path(project) / RECORD).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or not str(doc.get('decided_by', '')).strip() or not str(doc.get('date', '')).strip():
        return None
    return {k: doc.get(k) for k in ('schema', 'decided_by', 'date', 'why', 'source') if doc.get(k) is not None}


def dark_flat_reason(img):
    """Why a picture is a big plain-colour or dark block (audit_new_english_images.flat_panel_reason, plus a big
    opaque picture whose mean luma is below DARK_LUMA), or None."""
    from audit_new_english_images import flat_panel_reason
    why = flat_panel_reason(img)
    if why:
        return why.split(';', 1)[0]
    im = img.convert('RGBA')
    if min(im.size) < DARK_MIN_SIDE:
        return None
    small = im.resize((48, 48))
    px = [p for p in small.getdata() if p[3] > 128]
    if len(px) < 0.6 * 48 * 48:
        return None
    luma = sum(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in px) / len(px)
    return 'dark_picture: mean luma %d (< %d)' % (luma, DARK_LUMA) if luma < DARK_LUMA else None


def dark_flat_images(project):
    """[{'file', 'sha256', 'reason'}] for the pictures under <project>/assets that are big plain-colour or dark blocks.
    None when Pillow is missing (nothing can be measured)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    project = Path(project)
    rows = []
    root = project / 'assets'
    if not root.is_dir():
        return rows
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.is_symlink() or not p.name.lower().endswith(IMAGE_SUFFIXES) or p.name.startswith('._'):
            continue
        rel = p.relative_to(project)
        if SKIP_DIRS & {x.lower() for x in rel.parts[:-1]}:
            continue
        try:
            data = p.read_bytes()
            with Image.open(p) as im:
                why = dark_flat_reason(im)
                size = list(im.size)
        except (OSError, ValueError):
            continue
        if why:
            rows.append({'file': rel.as_posix(), 'sha256': _sha(data), 'reason': why, 'size': size})
    return rows


def verdict(project, board):
    """-> dict: applies ('block' | 'not_applicable' from feature_policy), state, original [...], new [...], record,
    sources, detail.
    state: 'remake'          rule blocks (remake / remake art): the dark-area row is judged as before
           'kept_original'   English original art; every big dark / plain picture is the original's -> 不适用
           'new_art'         English original art; some NEW pictures are dark / plain blocks -> still blocks
           'no_original'     English, but no original hashes recorded (raw_inputs keep / art_records base) -> blocks
           'unmeasured'      Pillow missing -> blocks"""
    import feature_policy
    applies = feature_policy.applies(RULE, board, project)
    out = {'rule': RULE, 'applies': applies, 'original': [], 'new': [], 'record': keep_record(project), 'sources': []}
    if applies != 'not_applicable':
        out.update(state='remake', detail='重塑（或英化选了重塑画风）：大块深色/纯色照查，原图也要重做')
        return out
    shas, sources = original_hashes(project)
    out['sources'] = sources
    if not shas:
        out.update(state='no_original', detail='没有中文原包的图片登记（_原始输入/原始输入登记.json 或 docs/art/base-assets.json），'
                   '分不出哪张是原图：先跑 raw_inputs.py keep 或 art_records.py base 再重跑 art_check')
        return out
    rows = dark_flat_images(project)
    if rows is None:
        out.update(state='unmeasured', detail='没有 Pillow，量不了图，深色/纯色这一行照旧判')
        return out
    out['original'] = [r for r in rows if r['sha256'] in shas]
    # a NEW picture counts when it can make a screen dark or plain: dark, or panel / background size (both sides >=
    # NEW_MIN_SIDE). Small plain word images and icons (弹球传奇 check_box 128x128, txt_music 800x128) do not.
    out['new'] = [r for r in rows if r['sha256'] not in shas and ('dark' in r['reason'] or min(r['size']) >= NEW_MIN_SIDE)]
    who = out['record']
    by = ('%s %s 定的保留原画风（%s）' % (who.get('decided_by'), who.get('date'), RECORD.as_posix()) if who
          else '英化第一轮照原画风（Saul 2026-10-31）')
    if out['new']:
        out.update(state='new_art', detail='新做的图里有大块纯色/深色 %d 张（原图保留只管原图）：%s' % (
            len(out['new']), '；'.join('%s %s' % (r['file'], r['reason']) for r in out['new'][:5])))
    else:
        out.update(state='kept_original', detail='原图保留，不适用：%s；大块纯色/深色的图 %d 张都和中文原包同 SHA，'
                   '新做的图没有大块纯色/深色（原包登记：%s）' % (by, len(out['original']), '、'.join(sources)))
    return out


def summary(v):
    """Short form for art_check's report and the art receipt (no full lists)."""
    return {'rule': v['rule'], 'applies': v['applies'], 'state': v['state'], 'record': v['record'],
            'original': [r['file'] for r in v['original']][:30], 'new': [r['file'] for r in v['new']][:30],
            'sources': v['sources']}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--board', choices=('localize', 'remake'))
    a = ap.parse_args(argv)
    import feature_policy
    board = feature_policy.board_of(a.project, a.board)[0] or 'remake'
    v = verdict(a.project, board)
    print(json.dumps(dict(summary(v), detail=v['detail'], board=board), ensure_ascii=False, indent=1))
    return 0 if v['state'] == 'kept_original' else 1


if __name__ == '__main__':
    sys.exit(main())
