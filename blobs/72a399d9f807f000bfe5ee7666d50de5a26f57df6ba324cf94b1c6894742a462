#!/usr/bin/env python3
"""Skin previews use each skin's own picture, never a slot frame or a colour tint (R4O2, 补查2 第 7 组).

SLS35 (2026-11-05): the store preview was bound to the slot frame TileIn.png, and skins were "made" by setting
Sprite.color on the whole preview node, so the white tile face was tinted too. make_skin_table.py now writes a
previewFrame per item; the store / trial template binds only that field.

    python3 check_skin_preview.py --table assets/resources/config/unlock_table.json [--src assets/scripts] [--board B]

Table: every skin/background row needs its own previewFrame (missing / TODO / shared by two rows / a slot, frame,
tile-in or placeholder picture are reported). Source (.ts/.js under --src): a preview or skin node whose colour is set
to anything but white is reported as tint_as_skin (resetting to white is fine; tinting particles or labels is not
looked at). --board remake (default, new games): findings exit 1. --board localize: warnings, exit 0. --board legacy:
report only, exit 0 (finished games are not changed). Standard library only, runs in well under a second.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

GROUPS = ('skin', 'background')
SLOT = re.compile(r'(?i)(slot|tile[_-]?in|placeholder|empty[_-]|frame[_-]?bg|cell[_-]?bg|槽|框)')
TINT = re.compile(r'(?i)\b\w*(preview|skin)\w*(\s*\.\s*\w+)*\s*\.\s*(color\s*=(?!=)|setColor\s*\(|color\s*\.\s*set\s*\()(.*)')
WHITE = re.compile(r'(?i)(Color\s*\.\s*WHITE|\(\s*255\s*,\s*255\s*,\s*255|#?fff(fff)?\b|rgb\(\s*255\s*,\s*255\s*,\s*255)')
SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'platform-kit', 'tiktok-platform', '.tiktok-kit'}


def check_table(table):
    out = []
    rows = [r for r in table.get('items', []) if isinstance(r, dict) and r.get('group') in GROUPS]
    frames = Counter(str(r.get('previewFrame')) for r in rows if isinstance(r.get('previewFrame'), str))
    for r in rows:
        pf, rid = r.get('previewFrame'), r.get('id')
        if not isinstance(pf, str) or not pf.strip():
            out.append({'kind': 'missing_preview_frame', 'id': rid})
        elif pf.strip().upper().startswith('TODO'):
            out.append({'kind': 'preview_frame_todo', 'id': rid})
        else:
            if frames[pf] > 1:
                out.append({'kind': 'shared_preview_frame', 'id': rid, 'previewFrame': pf})
            if SLOT.search(Path(pf).name):
                out.append({'kind': 'slot_art_as_preview', 'id': rid, 'previewFrame': pf})
    return out


def check_source(text, where='source'):
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        code = line.split('//', 1)[0]
        m = TINT.search(code)
        if m and not WHITE.search(m.group(4)):
            out.append({'kind': 'tint_as_skin', 'where': '%s:%d' % (where, no), 'line': line.strip()[:160]})
    return out


def scan_src(root):
    out = []
    for p in sorted(Path(root).rglob('*')):
        if p.suffix not in ('.ts', '.js') or SKIP_DIRS & set(p.parts) or not p.is_file():
            continue
        try:
            out += check_source(p.read_text(encoding='utf-8', errors='replace'), p.relative_to(root).as_posix())
        except OSError:
            continue
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--table', type=Path)
    ap.add_argument('--src', type=Path, action='append', default=[])
    ap.add_argument('--board', choices=['remake', 'localize', 'legacy'], default='remake')
    a = ap.parse_args(argv)
    if not a.table and not a.src:
        ap.error('give --table and/or --src')
    findings = []
    if a.table:
        try:
            findings += check_table(json.loads(a.table.read_text(encoding='utf-8')))
        except (OSError, ValueError) as exc:
            ap.exit(2, 'check_skin_preview: %s\n' % exc)
    for s in a.src:
        findings += scan_src(s)
    blocking = a.board == 'remake' and bool(findings)
    print(json.dumps({'tool': 'check_skin_preview', 'board': a.board, 'passed': not blocking,
                      'level': 'error' if blocking else ('warning' if findings else 'ok'), 'findings': findings,
                      'fix': 'give every skin its own previewFrame picture and bind only that; never tint the preview '
                             'node with Sprite.color, never fall back to a slot/frame picture'},
                     ensure_ascii=False, indent=1))
    return 1 if blocking else 0


if __name__ == '__main__':
    sys.exit(main())
