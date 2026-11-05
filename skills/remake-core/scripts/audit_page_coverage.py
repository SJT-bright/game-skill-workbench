#!/usr/bin/env python3
"""Every page and popup with words or buttons has been looked at (Saul 2026-11-04, 蛋壳特工队).

The six screenshots Saul sent on 11-04 came from VipLayer, PatrolFastLayer, LetterLayer, RewardSkinLayer and the shop
poster. The art check of that round had passed its capture gate with 8 pages listed in docs/art/screens.json; 21 of
the game's 47 layers had never been dumped, so nothing could have found the problems on them. The list of pages to
check therefore comes from the project itself, not from what someone remembered to write down:

  page        a prefab with text or buttons that is a page / popup (name ends in Layer, Panel, Dialog, Popup, View,
              Window, Page, Menu ...; or it blocks input; or it is nearly screen-sized), or a scene
  covered     some dump has a node named like the prefab's root (or most of its text/button nodes) -- at two phone sizes
  string      an English text from docs/copy/copy-table.csv that still sits in a covered page's prefab, but never
              showed in any dump: a state nobody opened (PatrolFastLayer's「Get Free」)

Pages that really cannot be reached, and texts that never show, go into docs/art/screens.json with a reason:
  "not_reachable": [{"prefab": "MoreGameLayer", "why": "更多游戏入口按英化规则删了，代码不再打开"}],
  "text_not_shown": [{"text": "Network error", "why": "只有断网才出，试玩里断不了网"}]

  python audit_page_coverage.py --project GAME --dumps DIR [--out result.json]
Exit codes: 0 all covered, 1 gaps, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', '.tiktok-kit', 'settings', 'removed'}
PAGE_NAME = re.compile(r'(Layer|Panel|Dialog|Dlg|Popup|Pop|View|Window|Win|Page|Menu|Screen|Scene|Box|Tips?|UI|Ui)$')
PLACEHOLDER = {'label', 'text', 'name', 'title', 'desc', 'num', 'new label', 'richtext', 'label1', 'tip', 'tips', 'button'}
PLACEHOLDER_TEXT = re.compile(r'\b(name|description|desc|placeholder|lorem)\b|[{}%]|\$\{', re.I)
LETTERS = re.compile(r'[A-Za-z]')


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', re.sub(r'<[^>]*>', '', str(s or '')).lower()).strip()


def load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def design_size(project):
    for rel in ('settings/v2/packages/project.json', 'settings/project.json', 'project.json'):
        d = load_json(Path(project) / rel)
        if not isinstance(d, dict):
            continue
        g = d.get('general') or {}
        dr = g.get('designResolution') or d.get('designResolution') or {}
        w, h = dr.get('width') or d.get('design-resolution-width'), dr.get('height') or d.get('design-resolution-height')
        if w and h:
            return float(w), float(h)
    return None


def components(arr, node):
    for c in node.get('_components') or []:
        if isinstance(c, dict) and isinstance(c.get('__id__'), int) and c['__id__'] < len(arr):
            yield arr[c['__id__']]


def label_string(o):
    for k in ('_string', '_N$string', 'string'):
        v = o.get(k)
        if isinstance(v, str):
            return v
    return ''


def read_ui_file(path, design):
    """Root name, text strings and page-likeness of a prefab or scene file."""
    arr = load_json(path)
    if not isinstance(arr, list) or not arr:
        return None
    nodes = [o for o in arr if isinstance(o, dict) and o.get('__type__') in ('cc.Node', 'cc.Scene', 'cc.PrivateNode')]
    if not nodes:
        return None
    root = None
    head = arr[0] if isinstance(arr[0], dict) else {}
    ref = (head.get('data') or head.get('scene') or {}).get('__id__') if isinstance(head.get('data') or head.get('scene'), dict) else None
    if isinstance(ref, int) and ref < len(arr) and isinstance(arr[ref], dict):
        root = arr[ref]
    root = root or nodes[0]
    strings, buttons, blocks = [], 0, False
    for i, o in enumerate(arr):
        if not isinstance(o, dict):
            continue
        t = o.get('__type__')
        if t in ('cc.Label', 'cc.RichText'):
            s = label_string(o)
            if s.strip():
                strings.append((i, s))
        elif t == 'cc.Button':
            buttons += 1
        elif t == 'cc.BlockInputEvents':
            blocks = True
    size = None
    for c in components(arr, root):
        if c.get('__type__') == 'cc.UITransform':
            size = c.get('_contentSize')
    size = size or root.get('_contentSize')
    big = False
    if isinstance(size, dict) and design:
        big = (size.get('width') or 0) >= 0.6 * design[0] and (size.get('height') or 0) >= 0.6 * design[1]
    name = str(root.get('_name') or Path(path).stem)
    scene = Path(path).suffix in ('.fire', '.scene')
    page = scene or bool(PAGE_NAME.search(Path(path).stem) or PAGE_NAME.search(name)) or blocks or big
    names = {str(o.get('_name')) for o in nodes if o.get('_name')}
    return {'file': path, 'root': name, 'scene': scene, 'page': page, 'strings': strings, 'buttons': buttons,
            'node_names': names, 'array': arr}


def read_dumps(dumps):
    files = []
    for raw in dumps:
        p = Path(raw)
        files += sorted(p.rglob('*ui-dump*.json')) if p.is_dir() else ([p] if p.is_file() else [])
    out = []
    for f in files:
        d = load_json(f)
        if not isinstance(d, dict) or d.get('tool') != 'ui_dump' or d.get('error') or not d.get('nodes'):
            continue
        vp = d.get('viewport') or {}
        c = d.get('canvas_css') or [0, 0, 0, 0]
        size = (int(vp.get('width') or round(c[2] if len(c) > 2 else 0)), int(vp.get('height') or round(c[3] if len(c) > 3 else 0)))
        segs, texts = set(), []
        for n in d['nodes']:
            if (n.get('opacity', 1) or 0) < 0.05:
                continue
            segs.update(str(n.get('path') or '').split('/'))
            comps = n.get('comps') or {}
            lab = comps.get('label') or comps.get('richtext') or comps.get('image_text') or {}
            s = lab.get('string') or lab.get('desired')
            if s:
                texts.append(norm(s))
        out.append({'file': str(f), 'size': size, 'scene': str(d.get('scene') or ''), 'segments': segs, 'texts': texts})
    return out


def pointer_value(arr, pointer):
    """'/57/_string' -> arr[57]['_string']."""
    cur = arr
    for part in [p for p in str(pointer).split('/') if p]:
        try:
            cur = cur[int(part)] if isinstance(cur, list) else cur[part]
        except (KeyError, IndexError, ValueError, TypeError):
            return None
    return cur


def audit(project, dumps):
    project = Path(project).resolve()
    design = design_size(project)
    manifest = load_json(project / 'docs/art/screens.json') or {}
    unreachable = {}
    for row in manifest.get('not_reachable') or []:
        if isinstance(row, dict) and row.get('prefab') and len(str(row.get('why') or '').strip()) >= 4:
            unreachable[str(row['prefab'])] = str(row['why']).strip()
    not_shown = {norm(r['text']): str(r['why']).strip() for r in manifest.get('text_not_shown') or []
                 if isinstance(r, dict) and r.get('text') and len(str(r.get('why') or '').strip()) >= 4}
    viewports = {(int(v['width']), int(v['height'])) for v in manifest.get('required_viewports') or []
                 if isinstance(v, dict) and isinstance(v.get('width'), int) and isinstance(v.get('height'), int)}
    need_sizes = max(2, len(viewports))

    ui = []
    for p in sorted((project / 'assets').rglob('*')):
        if p.suffix not in ('.prefab', '.fire', '.scene') or not p.is_file():
            continue
        if SKIP_DIRS & {x.lower() for x in p.relative_to(project).parts[:-1]}:
            continue
        info = read_ui_file(p, design)
        if info and (info['strings'] or info['buttons']) and info['page']:
            info['rel'] = p.relative_to(project).as_posix()
            ui.append(info)
    shots = read_dumps(dumps)
    if not shots:
        return {'tool': 'audit_page_coverage', 'schema': 1, 'error': 'no ui_dump files'}
    pages, missing, exempt = [], [], []
    by_rel = {}
    for info in ui:
        by_rel[info['rel']] = info
        if info['scene']:
            seen = {s['size'] for s in shots if s['scene'] and (s['scene'] == info['root'] or s['scene'] == Path(info['rel']).stem)}
        else:
            seen = {s['size'] for s in shots if info['root'] in s['segments']}
            if not seen:                       # an instance renamed by code: most of its own node names show up
                own = {n for n in info['node_names'] if n and n != info['root'] and not re.fullmatch(r'(New )?Node|Label|Sprite|bg|icon|text', n)}
                if len(own) >= 3:
                    seen = {s['size'] for s in shots if len(own & s['segments']) >= 0.8 * len(own)}
        rec = {'prefab': info['rel'], 'root': info['root'], 'texts': len(info['strings']), 'buttons': info['buttons'],
               'sizes': sorted('%dx%d' % s for s in seen),
               'sample': [s for _, s in info['strings'][:3]]}
        reason = unreachable.get(info['root']) or unreachable.get(info['rel']) or unreachable.get(Path(info['rel']).stem)
        if len(seen) >= need_sizes and (not viewports or viewports <= seen):
            rec['status'] = 'covered'
        elif reason:
            rec['status'] = 'not_reachable'
            rec['why'] = reason
            exempt.append(rec)
        else:
            rec['status'] = 'seen_once' if seen else 'never'
            missing.append(rec)
        pages.append(rec)

    # English texts of covered pages that never showed: a state nobody opened
    strings_missing = []
    shown = [t for s in shots for t in s['texts']]
    table = project / 'docs/copy/copy-table.csv'
    covered = {r['prefab'] for r in pages if r['status'] == 'covered'}
    if table.is_file():
        try:
            rows = list(csv.reader(table.read_text(encoding='utf-8-sig').splitlines()))
        except (OSError, csv.Error):
            rows = []
        if rows and {x.strip().lower() for x in rows[0][:2]} & {'zh', 'en', 'cn', 'english', 'chinese'}:
            rows = rows[1:]                        # header row
        for r in rows:
            if len(r) < 4:
                continue
            en, where, pointer = r[1].strip(), r[2].strip(), r[3].strip()
            if where not in covered or not en or len(LETTERS.findall(en)) < 3 or norm(en) in PLACEHOLDER:
                continue
            if pointer_value(by_rel[where]['array'], pointer) != en:
                continue                           # stale row: the prefab has changed since the table was written
            key = norm(en)
            if not key or key in not_shown or any(key in t for t in shown) or PLACEHOLDER_TEXT.search(en):
                continue
            strings_missing.append({'text': en, 'prefab': where, 'where': pointer})
    # Pages decide: a prefab text may be a placeholder code overwrites, or a label hidden behind word art, so texts
    # that never showed are a list to look at (states nobody opened), not a failure by themselves.
    passed = not missing
    return {'tool': 'audit_page_coverage', 'schema': 1, 'passed': passed, 'pages': len(pages),
            'covered': sum(1 for r in pages if r['status'] == 'covered'), 'missing': missing, 'not_reachable': exempt,
            'strings_missing': strings_missing, 'need_sizes': need_sizes, 'dumps': len(shots),
            'design_resolution': list(design) if design else None, 'pages_list': pages}


def summary(result):
    if result.get('error'):
        return result['error']
    parts = []
    if result['missing']:
        never = [r['root'] for r in result['missing'] if r['status'] == 'never']
        once = [r['root'] for r in result['missing'] if r['status'] == 'seen_once']
        if never:
            parts.append('%d 个有字或按钮的页面/弹窗从没采集过：%s' % (len(never), '、'.join(never[:14]) + ('…' if len(never) > 14 else '')))
        if once:
            parts.append('%d 个只采了一种尺寸：%s' % (len(once), '、'.join(once[:10])))
    head = '；'.join(parts) or '通过：%d 个页面/弹窗都在两种尺寸采集过' % result['covered']
    if result['strings_missing']:
        s = result['strings_missing']
        head += '；提示：%d 句英文没在任何采集里出现过，看是不是有状态没打开（是占位字或被字图替掉的不用管）：%s' % (
            len(s), '；'.join('「%s」(%s)' % (x['text'][:30], Path(x['prefab']).stem) for x in s[:8]))
    return head


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dumps', nargs='+', required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'error': 'not a Cocos project: %s' % a.project}, ensure_ascii=False))
        return 2
    result = audit(a.project, a.dumps)
    if result.get('error'):
        print(json.dumps(result, ensure_ascii=False))
        return 2
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'tool': 'audit_page_coverage', 'passed': result['passed'], 'pages': result['pages'],
                      'covered': result['covered'], 'summary': summary(result)}, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
