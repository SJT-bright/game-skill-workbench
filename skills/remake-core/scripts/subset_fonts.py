#!/usr/bin/env python3
"""Font subsets for the first download (生成时预防 R4F2, census #8: 蛋壳特工队 put whole fonts into the main package,
main package 8.7 MB until the glyphs were cut).

Run it when a TTF/OTF font is added to the project (art or English step), before first_screen.py. Static, seconds,
no build. The AI runs it; the user never runs commands.

  python3 -B subset_fonts.py --project <cocos project> [--font assets/x.ttf ...] [--extra-chars TEXT] [--dry-run]

What it does:
  1. collects the characters the game itself shows: Label strings in scenes/prefabs (_string, _N$string), string
     literals in scripts, string values in JSON under assets/ (levels, i18n tables), docs/english text pairs, plus
     printable ASCII (digits, A-Z, a-z, punctuation) so numbers and English always render.
  2. cuts every TTF/OTF font bigger than THRESHOLD_KB (or the --font files) to those characters with fontTools,
     in place: the .meta and uuid stay, so no scene changes. The original goes to .tiktok-kit/font-backup/.
  3. writes docs/startup/font-subset.json: per font the original bytes, the subset bytes, the subset sha256 and the
     character count. first_screen.py treats a font whose sha256 matches that record as subset.
Without fontTools the step is "not_run" (exit 3), never "ok": install it (python3 -m pip install fonttools) and
run again. preflight.py reminds about it when the project has a TTF/OTF font.
Exit: 0 ok / nothing to cut, 1 a font could not be cut, 2 bad input, 3 not_run (fontTools missing).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

THRESHOLD_KB = 200                    # a TTF/OTF in the first download bigger than this must be a subset
FONT_EXT = ('.ttf', '.otf')
RECORD = ('docs', 'startup', 'font-subset.json')
BACKUP = ('.tiktok-kit', 'font-backup')
ASCII = ''.join(chr(c) for c in range(0x20, 0x7f))
LABEL_STRING = re.compile(r'"_(?:N\$)?string"\s*:\s*"((?:[^"\\]|\\.)*)"')
JS_STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`')
SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'local', '.git', '.tiktok-kit'}


def fonttools_available() -> bool:
    try:
        import fontTools.subset  # noqa: F401
        return True
    except ImportError:
        return False


def _unescape(s: str) -> str:
    try:
        return json.loads('"%s"' % s.replace('\n', '\\n'))
    except ValueError:
        return s


def _walk(root: Path):
    if not root.is_dir():
        return
    for p in sorted(root.rglob('*')):
        if p.is_file() and not SKIP_DIRS & set(p.relative_to(root).parts[:-1]):
            yield p


def _json_strings(node, out: set):
    if isinstance(node, str):
        out.update(node)
    elif isinstance(node, dict):
        for k, v in node.items():
            if not str(k).startswith('__'):
                _json_strings(v, out)
    elif isinstance(node, list):
        for v in node:
            _json_strings(v, out)


def collect_chars(project, extra: str = '') -> str:
    """Characters the game shows, sorted, always including printable ASCII."""
    project = Path(project)
    chars = set(ASCII) | set(extra or '')
    for p in _walk(project / 'assets'):
        suf = p.suffix.lower()
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        if suf in ('.fire', '.scene', '.prefab'):
            for m in LABEL_STRING.finditer(text):
                chars.update(_unescape(m.group(1)))
        elif suf in ('.js', '.ts'):
            for m in JS_STRING.finditer(text):
                chars.update(_unescape(next(g for g in m.groups() if g is not None)))
        elif suf == '.json':
            try:
                _json_strings(json.loads(text), chars)
            except ValueError:
                pass
    for p in _walk(project / 'docs' / 'english'):
        if p.suffix.lower() == '.json':
            try:
                _json_strings(json.loads(p.read_text(encoding='utf-8', errors='ignore')), chars)
            except ValueError:
                pass
    return ''.join(sorted(c for c in chars if c >= ' ' and c not in '\x7f\ufeff'))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_record(project) -> dict:
    p = Path(project).joinpath(*RECORD)
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data.get('fonts') or {} if isinstance(data, dict) else {}


def is_subset(project, rel: str) -> bool:
    """True when assets font `rel` (project-relative) is the file subset_fonts.py wrote."""
    row = read_record(project).get(rel)
    f = Path(project) / rel
    return bool(row) and f.is_file() and row.get('sha256') == sha256(f)


def big_fonts(project, threshold_kb: int = THRESHOLD_KB) -> list:
    project = Path(project)
    return [p.relative_to(project).as_posix() for p in _walk(project / 'assets')
            if p.suffix.lower() in FONT_EXT and p.stat().st_size > threshold_kb * 1024]


def subset(project, fonts=None, extra: str = '', dry_run: bool = False) -> dict:
    project = Path(project)
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    fonts = [f for f in (fonts or big_fonts(project))]
    chars = collect_chars(project, extra)
    out = {'tool': 'subset_fonts', 'threshold_kb': THRESHOLD_KB, 'chars': len(chars), 'fonts': {}}
    todo = [f for f in fonts if not is_subset(project, f)]
    if not todo:
        out['status'] = 'ok'
        return out
    if dry_run:
        out.update(status='dry_run', would_cut=todo, sample=chars[:200])
        return out
    if not fonttools_available():
        out.update(status='not_run', would_cut=todo,
                   why='fontTools is not installed: python3 -m pip install fonttools, then run subset_fonts.py again')
        return out
    from fontTools import subset as fts
    record_path = project.joinpath(*RECORD)
    record = {'schema': 'font_subset.v1', 'tool': 'subset_fonts', 'fonts': read_record(project)}
    failed = []
    for rel in todo:
        src = project / rel
        if src.suffix.lower() not in FONT_EXT or not src.is_file():
            failed.append('%s: not a TTF/OTF file' % rel)
            continue
        backup = project.joinpath(*BACKUP, rel)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.is_file():
            shutil.copy2(src, backup)
        before = backup.stat().st_size
        opts = fts.Options()
        opts.layout_features = ['*']
        opts.name_IDs = ['*']
        opts.notdef_outline = True
        try:
            font = fts.load_font(str(backup), opts)
            sub = fts.Subsetter(opts)
            sub.populate(text=chars)
            sub.subset(font)
            tmp = src.with_name(src.name + '.subset.tmp')
            fts.save_font(font, str(tmp), opts)
            tmp.replace(src)
        except Exception as exc:  # noqa: BLE001 - report per font, keep the original
            failed.append('%s: %s' % (rel, repr(exc)[:200]))
            continue
        row = {'original_bytes': before, 'subset_bytes': src.stat().st_size, 'sha256': sha256(src),
               'chars': len(chars), 'backup': '/'.join(BACKUP + (rel,))}
        record['fonts'][rel] = row
        out['fonts'][rel] = row
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    out.update(status='failed' if failed else 'ok', failed=failed, record='/'.join(RECORD))
    return out


def preflight_line(project, available=None):
    """One preflight hint (Chinese) or None: the project has a TTF/OTF font and fontTools is missing."""
    project = Path(project)
    fonts = [p for p in _walk(project / 'assets') if p.suffix.lower() in FONT_EXT]
    if not fonts:
        return None
    if available is None:
        available = fonttools_available()
    if available:
        return None
    big = big_fonts(project)
    return ('工程里有 %d 个 TTF/OTF 字体（超过 %d KB 的 %d 个），本机 Python 没装 fontTools：字体子集一步会判「未执行」，'
            '不算通过。AI 先装：python3 -m pip install fonttools，再跑 subset_fonts.py --project'
            % (len(fonts), THRESHOLD_KB, len(big)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--font', action='append', help='project-relative font path (default: every TTF/OTF > %d KB)'
                    % THRESHOLD_KB)
    ap.add_argument('--extra-chars', default='', help='characters the game builds at run time (names, symbols)')
    ap.add_argument('--dry-run', action='store_true', help='list fonts and characters, change nothing')
    a = ap.parse_args(argv)
    try:
        out = subset(a.project, a.font, a.extra_chars, a.dry_run)
    except ValueError as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(out, ensure_ascii=False))
    return {'ok': 0, 'dry_run': 0, 'not_run': 3}.get(out['status'], 1)


if __name__ == '__main__':
    sys.exit(main())
