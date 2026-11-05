#!/usr/bin/env python3
"""Score/reward production preflight and runtime gate. Source mode is not visual acceptance.
Run --project GAME during first art integration; add --dumps DIR for actual runtime acceptance.
No runtime-text exemptions: fixed value words are picture words, live digits are bitmap digits.
"""
from __future__ import annotations
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import re

REVISION = 'score-reward-1'
VALUE_WORD = re.compile(r'^(?:score|best(?: score)?|high ?score|rewards?|coins?|gems?|diamonds?|gold|points?|level|stage|energy|lives?|price|cost|balance)\s*[:：]?$', re.I)
VALUE_PATH = re.compile(r'(?:score|reward|coin|gem|diamond|currency|balance|energy|level|stage|price|cost|lives)', re.I)
NUMERIC = re.compile(r'^[\s\d.,:/x×+%−-]*\d[\s\d.,:/x×+%−-]*$')
SUFFIXES = {'.ts', '.js', '.json', '.fire', '.scene', '.prefab', '.fnt', '.ttf', '.otf', '.meta'}
SKIP = {'node_modules', 'library', 'temp', 'build', '.git'}


def source_fingerprint(project):
    """Coordinates, bindings, fonts and text code all invalidate acceptance, even if PNGs are unchanged."""
    root = Path(project)
    files = {}
    for p in sorted((root / 'assets').rglob('*')):
        if p.is_file() and p.suffix.lower() in SUFFIXES and not SKIP.intersection(p.relative_to(root).parts):
            files[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def plain(value):
    return re.sub(r'<[^>]*>', '', str(value or '')).strip()


def value_text(text, path=''):
    from audit_page_richness import value_label
    text = plain(text)
    return bool(VALUE_WORD.fullmatch(text) or value_label(text) or (NUMERIC.fullmatch(text) and VALUE_PATH.search(path)))


def scene_findings(project):
    root = Path(project)
    fonts = {}
    for p in (root / 'assets').rglob('*.meta'):
        try:
            meta = json.loads(p.read_text(encoding='utf-8-sig'))
            fonts[meta.get('uuid')] = str(p)[:-5]
        except (OSError, ValueError, AttributeError):
            continue
    findings = []
    for p in sorted((root / 'assets').rglob('*')):
        if p.suffix not in {'.fire', '.scene', '.prefab'}:
            continue
        try:
            a = json.loads(p.read_text(encoding='utf-8-sig'))
            if not isinstance(a, list):
                continue
            def ref(r):
                return a[r['__id__']] if isinstance(r, dict) and isinstance(r.get('__id__'), int) and 0 <= r['__id__'] < len(a) else {}
            def node_path(n):
                seen = set(); parts = []
                while n and id(n) not in seen:
                    seen.add(id(n)); parts.append(n.get('_name', ''))
                    n = ref(n.get('_parent'))
                return '/'.join(reversed(parts))
            def enabled(n):
                seen = set()
                while n and id(n) not in seen:
                    seen.add(id(n))
                    if n.get('_active') is False:
                        return False
                    n = ref(n.get('_parent'))
                return True
            for c in a:
                if c.get('__type__') not in {'cc.Label', 'cc.RichText'} or c.get('_enabled') is False:
                    continue
                n = ref(c.get('node')); path = node_path(n)
                text = plain(c.get('_string', c.get('_N$string', '')))
                if not enabled(n) or not value_text(text, path):
                    continue
                f = c.get('_font') or c.get('_N$file') or {}
                font = fonts.get(f.get('__uuid__'), '')
                # A custom TTF is still ordinary font text. A word in a bitmap alphabet also needs a whole-word image.
                bitmap = font.lower().endswith('.fnt') and not c.get('_isSystemFont', False)
                if not bitmap or re.search(r'[A-Za-z]', text.replace('x', '')):
                    findings.append({'kind': 'source_value_font', 'file': p.relative_to(root).as_posix(),
                                     'path': path, 'text': text, 'font': font,
                                     'message': '固定词用整词图片；实时数量用生成的位图数字，不能用 TTF/系统字或整行普通字'})
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            findings.append({'kind': 'source_unreadable', 'file': p.relative_to(root).as_posix(), 'message': str(exc)})
    return findings


def runtime_findings(project, dumps):
    import audit_text_fit as T
    records = T.load_dumps(dumps)
    findings = []
    proj = T.Project(project)
    longest = T.load_longest(proj, None)
    for d in records:
        for n in d['nodes']:
            comps = n.get('comps') or {}
            lab = comps.get('label') or comps.get('richtext')
            if not lab or n.get('active') is False or n.get('opacity') == 0:
                continue
            text = plain(lab.get('string'))
            if not value_text(text, n.get('path', '')):
                continue
            if NUMERIC.fullmatch(text) and VALUE_PATH.search(n.get('path', '')):
                matching = [r for r in longest if fnmatch.fnmatch(n.get('path', ''), r['path'])]
                if not matching:
                    findings.append({'kind': 'value_longest_missing', 'file': d.get('_file'), 'path': n.get('path'),
                                     'text': text, 'message': '该实时数量缺最长合法显示值；填写 docs/art/longest-text.json 后实际显示该值采集，不以小数值通过'})
            bitmap = lab.get('font_kind') in {'bitmap', 'atlas'}
            if not bitmap or re.search(r'[A-Za-z]', text.replace('x', '')):
                findings.append({'kind': 'runtime_value_font', 'file': d.get('_file'), 'page': d.get('screen'),
                                 'path': n.get('path'), 'text': text,
                                 'message': '分数/奖励固定词或数量仍是普通字体；运行时文字登记不豁免'})
        # Reward overlays can exist in a dump marked gameplay: the generic fit checker intentionally skips world text.
        # Check only semantic HUD/reward value rows here, using its same measured glyph bodies.
        if d.get('kind') == 'gameplay':
            texts, pics, _ = T.collect(proj, d)
            targets = [t for t in texts if value_text(t.text, t.path) and not T.hidden(proj, t, pics)]
            for t in targets:
                if not t.measured:
                    findings.append({'kind': 'value_width_unmeasured', 'path': t.path, 'message': '缺实际字宽，不能核奖励行留白'})
            for i, left in enumerate(targets):
                for right in targets[i + 1:]:
                    if left.path.rsplit('/', 1)[0] != right.path.rsplit('/', 1)[0]:
                        continue
                    ox, oy = left.body.overlap(right.body)
                    if ox >= 3 and oy >= .35 * min(left.body.h, right.body.h):
                        findings.append({'kind': 'text_on_text', 'page': d.get('screen'), 'path': left.path,
                                         'other': right.path, 'message': '分数/奖励文字与数量重叠（实际字宽）'})
    # Same true glyph width checker used by art_check; no box-only shortcut and no declaration can waive it.
    fit = T.audit(project, dumps)
    blocking = {'text_on_text', 'text_over_words', 'text_on_icon', 'text_cut', 'text_off_screen',
                'text_outside_plate', 'longest_does_not_fit', 'unsettled_dump', 'pixel_checks_unavailable'}
    findings += [f for f in fit['findings'] if f['kind'] in blocking]
    if not records:
        findings.append({'kind': 'runtime_missing', 'message': '没有实际运行的 UI dump；源码扫描不能算视觉通过'})
    return findings, len(records)


def audit(project, dumps=None):
    root = Path(project)
    findings = scene_findings(root) if dumps is None else []
    pages = 0
    if dumps is not None:
        runtime, pages = runtime_findings(root, dumps)
        findings += runtime
    return {'tool': 'audit_value_presentation', 'schema': 1, 'revision': REVISION,
            'mode': 'runtime' if dumps is not None else 'source', 'passed': not findings,
            'source_sha256': source_fingerprint(root), 'pages': pages, 'findings': findings,
            'limits': '源码只预查序列化节点；脚本动态创建的 Score 等必须在首件真实页面采集后再验，不以源码通过替代。'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dumps', type=Path, nargs='+')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    if not (a.project / 'assets').is_dir():
        ap.error('project has no assets/')
    r = audit(a.project, a.dumps)
    s = json.dumps(r, ensure_ascii=False, indent=2) + '\n'
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(s, encoding='utf-8')
    print(s)
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
