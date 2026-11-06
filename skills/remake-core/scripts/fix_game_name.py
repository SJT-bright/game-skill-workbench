#!/usr/bin/env python3
"""Fix the game's own name where game_name_scan finds it (生成时预防 R4R1; Saul 2026-11-05 09:4x: 「以后的标题不止是拦截，
而是发现问题直接处理啊，直接修改图片」). Runs without asking the user; only what it cannot fix stays blocked.

  python3 fix_game_name.py --project P [--dry-run]       fix texts now, write the picture list, scan again
  python3 fix_game_name.py --project P --apply-images DIR put the new pictures (same file names) in, scan again

Texts (hits of tiktok_finalize_steps/game_name_scan.scan):
  * a Label / RichText in a scene or prefab whose whole text is the name ("BALL MASTER", "Ball Master 2"): the text
    is emptied and that Label / RichText component is switched off (_enabled false); node, size and layout stay.
    An EditBox is only emptied.
  * a text or an English copy-table cell that carries the name inside a sentence: the name becomes "the game"
    ("Welcome to Ball Master!" -> "Welcome to the game!"; "THE GAME" in capitals, "The game" at a sentence start,
    "本游戏" in Chinese text). A cell that is only the name is emptied.
  Originals go to docs/english/game-name-fix/backup/<same path>.orig (the first original is kept), every change to
  docs/english/game-name-fix/record.json.
Pictures (title / logo pictures whose transcription carries the name): this script does not draw. It writes
docs/art/game_name_fix.json: per picture its path, width x height, alpha, the pages / prefabs using it, a prompt
(hero / pattern / scene, no game name, no words; checked by remake-art/scripts/prompt_name_guard.py) and reference
pictures (other art of this game, never title / logo / banner pictures). The AI generates each picture with the same
file name into one folder and runs --apply-images: a picture of the same format and the same width x height replaces
the old one (its .meta is kept), others are left with the reason; then the scan runs again.
Exit: 0 the scan is clean, 1 hits remain (the JSON says which and what to do), 2 bad input. --dry-run writes nothing.
Legacy games are not touched (Saul: old / finished games are not managed).
"""
import argparse
import csv
import datetime
import io
import json
import re
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tiktok_finalize_steps import game_name_scan as G  # noqa: E402

ART_SCRIPTS = HERE.parent.parent / 'remake-art' / 'scripts'
FIX_DIR = Path('docs') / 'english' / 'game-name-fix'
IMAGE_LIST = Path('docs') / 'art' / 'game_name_fix.json'
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp')
LABEL_TYPES = ('cc.Label', 'cc.RichText')
STRING_KEYS = ('_N$string', '_string')
REF_TITLE = re.compile(r'(?i)(title|logo|banner|wordmark|biaoti|game[_\- ]?name|标题|游戏名|名字|横幅)')
CJK = re.compile(r'[\u4e00-\u9fff]')


def _guard():
    """remake-art prompt_name_guard (same pack); None when the pack has no remake-art."""
    if not (ART_SCRIPTS / 'prompt_name_guard.py').is_file():
        return None
    sys.path.insert(0, str(ART_SCRIPTS))
    try:
        import prompt_name_guard
        return prompt_name_guard
    except ImportError:
        return None


# ---------- texts ----------

def name_pattern(name):
    """'Ball Master' -> regex matching 'BALL MASTER', 'Ball-Master', 'BallMaster' (case, spaces, punctuation ignored)."""
    chars = [c for c in G.norm(name)]
    return re.compile(r"(?i)" + r"[^0-9a-z\u4e00-\u9fff]*".join(re.escape(c) for c in chars) + r"(?:['’]s\b)?")


def whole_name(text, pats):
    """True when the text is only the name (plus spaces, punctuation or a number: 'BALL MASTER 2!')."""
    rest = text
    for p in pats:
        rest = p.sub('', rest)
    r = G.norm(rest)
    if r == G.norm(text):
        return False
    if r == '' or r.isdigit():
        return True
    # a longer form of the title ("Dino Merge Evolution", "BALL MASTER DELUXE"): at most 2 capitalized words, no
    # sentence punctuation, none of them an ordinary sentence word -> still the title, emptied
    words = re.findall(r"[A-Za-z]+", rest)
    return (0 < len(words) <= 2 and not re.search(r'[.!?,:;]', rest) and not CJK.search(rest)
            and all(w[0].isupper() and w.lower() not in SENTENCE_WORDS for w in words))


SENTENCE_WORDS = {'play', 'start', 'welcome', 'to', 'in', 'of', 'the', 'a', 'an', 'tap', 'go', 'join', 'enter', 'open',
                  'back', 'with', 'and', 'for', 'new', 'my', 'your', 'now', 'here', 'is', 'love', 'thanks', 'by'}


def neutral(text, pats):
    """Replace the name inside a sentence with a neutral word. -> new text."""
    def repl(m):
        s, start = m.string, m.start()
        poss = m.group(0)[-2:] in ("'s", "’s")
        if CJK.search(m.group(0)) or (CJK.search(s) and not re.search(r'[A-Za-z]', s.replace(m.group(0), ''))):
            return '本游戏'
        word = 'game' if re.search(r'(?i)\bthe\s+$', s[:start]) else 'the game'
        before = s[:start].rstrip()
        letters = re.sub(r'[^A-Za-z]', '', s.replace(m.group(0), ''))
        if letters and letters.isupper():
            word = word.upper()
        elif not before or before[-1] in '.!?:':
            word = word[0].upper() + word[1:]
        return word + ("'s" if poss else '')
    out = text
    for p in pats:
        out = p.sub(repl, out)
    return re.sub(r'\s{2,}', ' ', out)


def _walk(data):
    if isinstance(data, dict):
        yield data
        for v in data.values():
            yield from _walk(v)
    elif isinstance(data, list):
        for v in data:
            yield from _walk(v)


def fix_scene(root, rel, pats, ok, changes):
    """-> new file text or None. Fixes Label / RichText / EditBox strings that carry the name."""
    p = root / rel
    raw = p.read_text(encoding='utf-8')
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    touched = False
    for i, obj in enumerate(_walk(data)):
        keys = [k for k in STRING_KEYS if isinstance(obj.get(k), str)]
        if not keys:
            continue
        s = obj[keys[0]]
        if not s.strip() or G.norm(s) in ok or not any(pt.search(s) for pt in pats):
            continue
        typ = str(obj.get('__type__') or '')
        if whole_name(s, pats):
            new = ''
            for k in keys:
                obj[k] = ''
            kind = 'text_cleared'
            if typ in LABEL_TYPES or typ.endswith('Label') or typ.endswith('RichText'):
                obj['_enabled'] = False
                kind = 'label_cleared_and_disabled'
        else:
            new = neutral(s, pats)
            for k in keys:
                obj[k] = new
            kind = 'text_rewritten'
        touched = True
        changes.append({'file': rel, 'where': '%s #%d (node id %s)' % (typ or 'object', i, _node_ref(obj)),
                        'kind': kind, 'before': s, 'after': new})
    if not touched:
        return None
    indent = 2 if re.match(r'^[\[{]\s*\n  ', raw) or '\n  ' in raw[:200] else None
    return json.dumps(data, ensure_ascii=False, indent=indent) + ('\n' if raw.endswith('\n') else '')


def _node_ref(obj):
    n = obj.get('node')
    return n.get('__id__') if isinstance(n, dict) else '-'


def fix_table(root, rel, pats, ok, changes):
    p = root / rel
    raw_bytes = p.read_bytes()
    bom = raw_bytes.startswith(b'\xef\xbb\xbf')
    raw = raw_bytes.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        return None
    cols = [i for i, h in enumerate(rows[0]) if h.strip().lower() in ('en', 'english', 'en-us', 'text_en')]
    touched = False
    for ln, row in enumerate(rows[1:], 2):
        for i in cols:
            if i >= len(row) or not row[i].strip():
                continue
            s = row[i]
            if G.norm(s) in ok or not any(pt.search(s) for pt in pats):
                continue
            new = '' if whole_name(s, pats) else neutral(s, pats)
            row[i] = new
            touched = True
            changes.append({'file': rel, 'where': 'line %d column %s' % (ln, rows[0][i]),
                            'kind': 'cell_cleared' if not new else 'cell_rewritten', 'before': s, 'after': new})
    if not touched:
        return None
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\r\n' if '\r\n' in raw else '\n').writerows(rows)
    return ('\ufeff' if bom else '') + buf.getvalue()


# ---------- pictures ----------

def image_size(p):
    """-> (w, h, alpha or None) for PNG / JPEG / WebP, standard library only; None when unreadable."""
    try:
        b = p.read_bytes()
    except OSError:
        return None
    if b[:8] == b'\x89PNG\r\n\x1a\n' and len(b) >= 26 and b[12:16] == b'IHDR':
        w, h = struct.unpack('>II', b[16:24])
        return w, h, b[25] in (4, 6) or b'tRNS' in b[:4096]
    if b[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            m = b[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack('>HH', b[i + 5:i + 9])
                return w, h, False
            i += 2 + struct.unpack('>H', b[i + 2:i + 4])[0]
        return None
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
        c = b[12:16]
        if c == b'VP8X':
            return 1 + int.from_bytes(b[24:27], 'little'), 1 + int.from_bytes(b[27:30], 'little'), bool(b[20] & 0x10)
        if c == b'VP8L':
            v = int.from_bytes(b[21:25], 'little')
            return (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1, bool((v >> 28) & 1)
        if c == b'VP8 ':
            w, h = struct.unpack('<HH', b[26:30])
            return w & 0x3FFF, h & 0x3FFF, False
    return None


def _uuids(p):
    meta = G._read_json(Path(str(p) + '.meta'))
    out = []
    if isinstance(meta, dict):
        if isinstance(meta.get('uuid'), str):
            out.append(meta['uuid'])
        for sub in (meta.get('subMetas') or {}).values():
            if isinstance(sub, dict) and isinstance(sub.get('uuid'), str):
                out.append(sub['uuid'])
    return out


def _scene_files(root):
    out = []
    for p in sorted(root.rglob('*')):
        parts = p.relative_to(root).parts
        if p.suffix.lower() in G.SCENE_SUFFIXES and p.is_file() and \
                not any(x.lower() in G.SKIP_DIRS for x in parts[:-1]) and p.stat().st_size <= G.MAX_BYTES:
            out.append(p)
    return out


def _art_files(root):
    out = []
    for p in sorted((root / 'assets').rglob('*')) if (root / 'assets').is_dir() else []:
        parts = p.relative_to(root).parts
        if p.suffix.lower() in IMAGE_EXT and p.is_file() and not any(x.lower() in G.SKIP_DIRS for x in parts[:-1]):
            out.append(p)
    return out


def _hero(root):
    g = G.glossary(root)
    for k in ('hero', 'protagonist', 'main_character', 'mascot'):
        if isinstance(g.get(k), str) and g[k].strip():
            return g[k].strip()
    return None


def make_prompt(root, rel, size, pages, names, guard):
    w, h, alpha = size if size else (None, None, None)
    hero = _hero(root)
    who = hero if hero and not any(name_pattern(n).search(hero) for n, _ in names) else "the game's main character"
    page = ', '.join(Path(x).stem for x in pages[:3]) or Path(rel).parent.name or 'home'
    shape = 'wide banner-shaped' if w and h and w > 1.3 * h else 'tall' if w and h and h > 1.3 * w else 'square-ish'
    prompt = ('Header artwork for the %s screen, %s picture %sx%s px: %s with props from the game, a pattern and a '
              'piece of the scene, in the same art style, colors and outline as the reference pictures%s. '
              'Pure picture only: no text, no letters, no numbers, no words anywhere.' % (
                  page, shape, w or '?', h or '?', who, ', transparent background' if alpha else ''))
    check = 'not_run (remake-art/scripts/prompt_name_guard.py not found)'
    if guard is not None:
        gn = guard.game_names(root) + [n for n, _ in names]
        hits = guard.scan(prompt, gn, 'prompt')
        if hits:
            prompt, _ = rewrite_with_guard(guard, prompt, gn)
            hits = guard.scan(prompt, gn, 'prompt')
        check = 'clean' if not hits else 'hits: %s' % hits
    return prompt, check


def rewrite_with_guard(guard, text, names):
    if hasattr(guard, 'fix_text'):
        return guard.fix_text(text, names)
    return text, []


def pick_refs(root, exclude, pages_of, rel, limit=3):
    """Other art of this game, never title / logo / banner pictures: first art on the same pages, then the largest."""
    pool = [p for p in _art_files(root) if p.relative_to(root).as_posix() not in exclude
            and not REF_TITLE.search(p.name) and (image_size(p) or (0, 0, 0))[0] >= 64]
    same = [p for p in pool if set(pages_of.get(p.relative_to(root).as_posix(), ())) & set(pages_of.get(rel, ()))]
    rest = sorted((p for p in pool if p not in same), key=lambda p: -p.stat().st_size)
    return [p.relative_to(root).as_posix() for p in (same + rest)[:limit]]


def image_list(root, image_hits, names):
    guard = _guard()
    scenes = _scene_files(root)
    texts = {}
    for s in scenes:
        try:
            texts[s.relative_to(root).as_posix()] = s.read_text(encoding='utf-8', errors='replace')
        except OSError:
            pass
    pages_of = {}

    def pages(rel):
        if rel not in pages_of:
            ids = _uuids(root / rel)
            pages_of[rel] = [k for k, t in texts.items() if any(u in t for u in ids)]
        return pages_of[rel]
    for p in _art_files(root):
        pages(p.relative_to(root).as_posix())
    rels = sorted({h['file'] for h in image_hits})
    out = []
    for rel in rels:
        p = root / rel
        size = image_size(p)
        pg = pages(rel)
        prompt, check = make_prompt(root, rel, size, pg, names, guard)
        refs = pick_refs(root, set(rels), pages_of, rel)
        ref_check = 'not_run'
        if guard is not None:
            ref_check = 'clean' if not [r for r in refs if REF_TITLE.search(Path(r).name)] else 'title reference left'
        out.append({'path': rel, 'file_name': p.name, 'width': size[0] if size else None,
                    'height': size[1] if size else None, 'alpha': size[2] if size else None,
                    'format': p.suffix.lower().lstrip('.'), 'used_on': pg,
                    'name_seen': sorted({h['text'] for h in image_hits if h['file'] == rel}),
                    'prompt': prompt, 'prompt_check': check, 'references': refs, 'references_check': ref_check,
                    'save_as': p.name})
    return {'tool': 'fix_game_name', 'made': _now(),
            'how': 'Generate each picture with the image model (prompt + references), same width x height and format, '
                   'save it under save_as in one folder, then run fix_game_name.py --project <P> --apply-images '
                   '<folder>. No need to ask the user.',
            'images': out}


def _now():
    return datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')


# ---------- record / backup ----------

def backup(root, rel):
    dst = root / FIX_DIR / 'backup' / (rel + '.orig')   # .orig: never read again as a scene / picture
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    return (FIX_DIR / 'backup' / (rel + '.orig')).as_posix()


def write_record(root, entry):
    path = root / FIX_DIR / 'record.json'
    rec = G._read_json(path) if path.is_file() else {}
    if not isinstance(rec, dict):
        rec = {}
    rec.setdefault('tool', 'fix_game_name')
    rec.setdefault('runs', []).append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def _policy(root):
    try:
        from tiktok_finalize_steps import policy as P
        return P.decide(project=root)['policy']
    except Exception:  # noqa: BLE001 - a project without marker is treated as new
        return 'new'


# ---------- main steps ----------

def fix_texts(root, dry_run=False):
    found = G.scan(root)
    names = found['names']
    pats = [name_pattern(n) for n, _ in names]
    ok = {G.norm(x) for x in (G.glossary(root).get('game_name_ok') or []) if isinstance(x, str)}
    text_files = sorted({h['file'] for h in found['hits'] if not h['file'].lower().endswith(IMAGE_EXT)})
    image_hits = [h for h in found['hits'] if h['file'].lower().endswith(IMAGE_EXT)]
    changes, writes, left = [], {}, []
    for rel in text_files:
        before = len(changes)
        if rel.lower().endswith(G.SCENE_SUFFIXES):
            new = fix_scene(root, rel, pats, ok, changes)
        elif rel.lower().endswith('.csv'):
            new = fix_table(root, rel, pats, ok, changes)
        else:
            new = None
        if new is None or len(changes) == before:
            left.append({'file': rel, 'why': 'could not rewrite this file automatically'})
        else:
            writes[rel] = new
    if not dry_run:
        for rel, text in writes.items():
            b = backup(root, rel)
            for c in changes:
                if c['file'] == rel:
                    c['backup'] = b
            (root / rel).write_text(text, encoding='utf-8')
    return names, changes, image_hits, left


def run_fix(root, dry_run=False):
    names, changes, image_hits, left = fix_texts(root, dry_run)
    imgs = image_list(root, image_hits, names) if image_hits else None
    if not dry_run:
        if imgs:
            (root / IMAGE_LIST).parent.mkdir(parents=True, exist_ok=True)
            (root / IMAGE_LIST).write_text(json.dumps(imgs, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        if changes or imgs:
            write_record(root, {'at': _now(), 'step': 'texts', 'changes': changes,
                                'image_list': IMAGE_LIST.as_posix() if imgs else None})
    after = G.scan(root) if not dry_run else None
    return {'tool': 'fix_game_name', 'project': str(root), 'dry_run': dry_run,
            'names': [n for n, _ in names], 'text_changes': changes, 'not_fixed': left,
            'image_list': (IMAGE_LIST.as_posix() if not dry_run else imgs) if imgs else None,
            'remaining_hits': after['hits'] if after else None,
            'next': ('generate the pictures in %s (no words), then --apply-images <folder>; no need to ask the user'
                     % IMAGE_LIST.as_posix()) if imgs else None}


def apply_images(root, folder):
    lst = G._read_json(root / IMAGE_LIST)
    if not isinstance(lst, dict) or not lst.get('images'):
        return {'tool': 'fix_game_name', 'error': 'no picture list %s; run fix_game_name.py first' % IMAGE_LIST}, 2
    done, skipped = [], []
    for it in lst['images']:
        new = Path(folder) / it['save_as']
        old = root / it['path']
        if not new.is_file():
            skipped.append({'path': it['path'], 'why': 'no %s in %s' % (it['save_as'], folder)})
            continue
        if new.suffix.lower() != old.suffix.lower():
            skipped.append({'path': it['path'], 'why': 'format %s, needs %s' % (new.suffix, old.suffix)})
            continue
        ns, os_ = image_size(new), image_size(old)
        if not ns:
            skipped.append({'path': it['path'], 'why': 'new picture not readable'})
            continue
        want = (it.get('width') or (os_ or (0, 0))[0], it.get('height') or (os_ or (0, 0))[1])
        if (ns[0], ns[1]) != tuple(want):
            ratio = '' if not want[1] else ' (ratio %.3f, needs %.3f)' % (ns[0] / ns[1], want[0] / want[1])
            skipped.append({'path': it['path'], 'why': 'size %dx%d, needs %dx%d%s; resize or regenerate' % (
                ns[0], ns[1], want[0], want[1], ratio)})
            continue
        b = backup(root, it['path'])
        shutil.copyfile(new, old)          # bytes only; the .meta (uuid, sprite frames) is kept
        done.append({'path': it['path'], 'from': str(new), 'backup': b})
    write_record(root, {'at': _now(), 'step': 'apply_images', 'replaced': done, 'skipped': skipped})
    after = G.scan(root)
    out = {'tool': 'fix_game_name', 'project': str(root), 'replaced': done, 'skipped': skipped,
           'remaining_hits': after['hits'], 'clean': not after['hits']}
    return out, 0 if not after['hits'] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dry-run', action='store_true', help='report what would change; write nothing')
    ap.add_argument('--apply-images', type=Path, help='folder with the new pictures (same file names)')
    ap.add_argument('--force', action='store_true', help='also on a legacy game (only when Saul asks)')
    a = ap.parse_args(argv)
    root = a.project
    if not root.is_dir():
        print('fix_game_name: no project folder %s' % root, file=sys.stderr)
        return 2
    if _policy(root) == 'legacy' and not a.force:
        print(json.dumps({'tool': 'fix_game_name', 'project': str(root), 'skipped': 'legacy game: not touched'}))
        return 0
    if a.apply_images:
        if a.dry_run:
            print('fix_game_name: --apply-images cannot be a dry run', file=sys.stderr)
            return 2
        if not a.apply_images.is_dir():
            print('fix_game_name: no folder %s' % a.apply_images, file=sys.stderr)
            return 2
        out, code = apply_images(root, a.apply_images)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return code
    out = run_fix(root, a.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.dry_run:
        return 0 if not (out['text_changes'] or out['image_list'] or out['not_fixed']) else 1
    return 0 if not out['remaining_hits'] else 1


if __name__ == '__main__':
    sys.exit(main())
