#!/usr/bin/env python3
"""Image prompts must not carry the game's name (Saul 2026-11-05: 以后的游戏都不要出现游戏名字，换成图案或主角).

Where a title or logo would go, ask the image model for the protagonist, characters, props, a pattern or the scene.
Page titles and button words (PLAY, SETTINGS, LEVEL COMPLETE) stay generated word pictures and are fine.

    python3 prompt_name_guard.py --project <game> --file docs/art/prompts.json [--file more.txt] [--text "..."]
    python3 prompt_name_guard.py --project <game> --names            only print the names it will look for

Names come from the project folder, settings/project.json (2.x: name / projectName / title), package.json (3.x name),
docs/copy/glossary.json "game_name" (the same names game_name_scan uses) and docs/game_name.json ({"names": [...]},
optional). Words that only look like the game name go to docs/game_name.json "allow_in_prompts"; glossary "allow" is
the spelling list (the English flow puts the game name there) and exempts nothing. "no game name" / "without the
title logo" / 不写游戏名 is the rule, not a request, and is not reported.
Matching ignores case, spaces, "-" and "_" (MergeShot2048 = "Merge Shot 2048"). Requests for a title logo or the
game name ("game title", "title logo", "游戏名", "标题logo") are reported too.
R4Q2 (2026-11-05): a name that is one plain English word (project "Wheel") is reported only where the prompt asks for
words: inside quotes, or next to reading / text / title / logo ("lucky wheel with 8 segments, no text" passes,
'title logo reading "WHEEL"' does not). --refs <image | list.json | list.txt>: reference pictures whose file name or
role says title / logo / banner are reported (the model copies the name from them); same words as ad-boost
extract_style skips.
Exit 1 when something is found (fix the prompt before generating), 0 clean, 2 bad input. --warn-only: always 0.
R4R1 (Saul 11-05 09:4x: 发现问题直接处理): --fix rewrites instead of only reporting: 'reading "NAME"' parts are
removed, the name and title / logo / game-name requests become the hero / pattern / scene, "no text, no letters,
no words" is added; it writes <file>.fixed.<ext> (--out-dir to put them elsewhere; title reference pictures dropped
from a --refs list), scans the rewritten prompts again and exits 0 when they are clean. Generate from the .fixed file.
JSON prompt files are read as data: every string value is scanned. Needs only the standard library.
"""
import argparse
import json
import re
import sys
from pathlib import Path

GENERIC = {'game', 'games', 'project', 'cocos', 'creator', 'newproject', 'helloworld', 'hello', 'demo', 'test',
           'tiktok', 'english', 'source', 'src', 'main', 'build', 'web', 'mobile', 'remake', 'reskin', 'copy', 'final',
           'assets', 'example', 'sample', 'tmp', 'work'}
NOISE = re.compile(r'(?i)(^|[ _\-])(tiktok|english|en|cn|zh|test|iaa|iap|src|source|final|copy|remake|reskin|'
                   r'fix\d*|r\d+|v\d+(\.\d+)*|\d{8})(?=$|[ _\-])')
# "puzzle game title sprite atlas" (page-title words) is fine; asking for THE game's title / name / logo is not
TITLE_ASK = re.compile(r"(?i)\bthe\s+game(['’]s)?\s+(title|name)\b|\bgame(['’]s)?[\s_-]*(name|logo)\b|\btitle[\s_-]*logo\b"
                       r"|\blogo\s+(text|with|of the game)\b|\bname[\s_-]*logo\b|\bwordmark of the game\b"
                       r"|游戏名|游戏标题|标题\s*logo|名字\s*logo")
# "no game name" / "without the game title" / 不写游戏名 is the rule itself, not a request (美工skill 11-05: 火箭三消
# RocketMatch "Hero illustration for the home top slot (no game name, ...)" was reported). A negation only counts in
# the same clause, so "no text, game logo in the middle" is still a request.
NEGATED = re.compile(r"(?i)(\b(no|not|without|never|avoid|exclude|excluding|don['’]?t|do\s+not)\b[^.;,:!?\n]{0,24}"
                     r"|(不|不要|别|无|没有|禁止|不能)[^。；，：！？.;,:!?\n]{0,8})$")
PATHLIKE = re.compile(r'^\S*([/\\]\S*|\.(png|webp|jpg|jpeg|json|meta))$', re.I)
FIX = 'use the protagonist, characters, props, a pattern or the scene instead of the game name / title logo'


def squash(text):
    return re.sub(r'[\s_\-·・.:：]+', '', str(text)).lower()


def _parts(raw):
    """'1香吉士-射击高手2048_TikTok_v3' -> ['射击高手2048', ...]; drops owner prefixes made of digits + 1-3 CJK."""
    raw = re.sub(r'[（(][^）)]*[）)]', ' ', str(raw)).strip()
    raw = NOISE.sub(' ', raw)
    raw = re.sub(r'^\d+[^\-—\s]{1,6}[-—]', '', raw).strip()   # Saul's folders: "<n><owner>-<game>"
    out = [raw]
    for piece in re.split(r'[-—_\s]+', raw):
        piece = re.sub(r'^\d+', '', piece).strip()
        # keep a piece alone only when it is a name by itself (CJK, or CamelCase like SnakeVSBlock); plain words such
        # as "lazy" / "dash" from package.json "lazy-cat-dash" would hit ordinary prompts
        if piece and piece != raw and (len(re.findall(r'[\u4e00-\u9fff]', piece)) >= 2 or
                                       re.search(r'[a-z][A-Z]', piece)):
            out.append(piece)
    return out


def _usable(name):
    s = squash(name)
    if not s or s in GENERIC or s.isdigit():
        return False
    cjk = len(re.findall(r'[\u4e00-\u9fff]', s))
    return cjk >= 2 or len(s) >= 4


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def game_names(project, extra=()):
    project = Path(project)
    raw = [project.resolve().name, *extra]
    d = _read_json(project / 'settings' / 'project.json') or {}
    raw += [d.get(k) for k in ('name', 'projectName', 'title') if isinstance(d.get(k), str)]
    d = _read_json(project / 'package.json') or {}
    if isinstance(d.get('name'), str):
        raw.append(d['name'])
    # docs/copy/glossary.json "game_name" (string or list, Chinese + English name): the English entry has every session
    # write it at the start and game_name_scan (R4O1) checks the shipped text against it, so the prompts are checked
    # against the same names (美工skill 11-05: 11.16 read only the folder, so 火箭三消 / Rocket Match were not seen)
    g = (_read_json(project / 'docs' / 'copy' / 'glossary.json') or {}).get('game_name')
    raw += [n for n in ([g] if isinstance(g, str) else g if isinstance(g, list) else []) if isinstance(n, str)]
    d = _read_json(project / 'docs' / 'game_name.json') or {}
    raw += [n for n in d.get('names', []) if isinstance(n, str)]
    # Not docs/copy/glossary.json "allow": that is the spelling-check list, and the English flow puts the game name
    # there on purpose (english-ui-rebuild.md 定词表), so it exempted the very name this guard looks for (RocketMatch,
    # CubeHarvest, BallMaster had no names left). Words that only look like the game name go to
    # docs/game_name.json "allow_in_prompts".
    allow = {squash(w) for w in (d.get('allow_in_prompts') or []) if isinstance(w, str)}
    names, seen = [], set()
    for r in raw:
        if not r:
            continue
        for p in _parts(r):
            key = squash(p)
            if _usable(p) and key not in seen and key not in allow:
                seen.add(key)
                names.append(p.strip())
    return names


def strings(data):
    if isinstance(data, str):
        yield data
    elif isinstance(data, dict):
        for v in data.values():
            yield from strings(v)
    elif isinstance(data, list):
        for v in data:
            yield from strings(v)


SINGLE_WORD = re.compile(r'^[A-Za-z]+$')
# R4Q2 (广告skill 11-05): a one-word name is reported only where the prompt asks for it to be drawn as words
TEXT_CUE = re.compile(r"(?i)\b(reading|reads|text|title|logo|word|words|wordmark|letters|lettering|says|saying|"
                      r"spelled|spelling|caption|label|banner|sign|written|typography)\b")
QUOTED = re.compile(r'"[^"\n]{0,60}"|“[^”\n]{0,60}”|‘[^’\n]{0,60}’|「[^」\n]{0,60}」')


def single_word(name):
    """'Wheel' -> True; 'Merge Shot 2048', 'SnakeVSBlock', '射击高手' -> False."""
    return bool(SINGLE_WORD.match(name.strip())) and not re.search(r'[a-z][A-Z]', name.strip())


def drawn_as_words(text, name):
    """A one-word name counts only inside quotes or next to a words cue ('title logo reading "WHEEL"', 'WHEEL logo')."""
    word = re.compile(r'(?i)\b%s\b' % re.escape(name.strip()))
    if any(word.search(q.group(0)) for q in QUOTED.finditer(text)):
        return True
    for m in word.finditer(text):
        before, after = text[max(0, m.start() - 25):m.start()], text[m.end():m.end() + 12]
        if TEXT_CUE.search(before) and not re.search(r'(?i)\bno\s+\w*\s*$', before) or \
                re.match(r'(?i)\s*(logo|title|text|wordmark|lettering|letters|sign|banner)\b', after):
            return True
    return False


REF_TITLE = re.compile(r'(?i)(title|logo|banner|wordmark|biaoti|game[_\- ]?name|标题|游戏名|名字|横幅)')
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp')


def _ref_entries(path):
    """--refs <image> or a list file (.json: [path | {path/file, role/name/label}], .txt: one path per line)."""
    p = Path(path)
    if p.suffix.lower() in IMAGE_EXT:
        return [(str(p), '')]
    text = p.read_text(encoding='utf-8')
    if p.suffix.lower() == '.json':
        data = json.loads(text)
        data = data.get('refs', data.get('references', data.get('images', []))) if isinstance(data, dict) else data
        out = []
        for e in data if isinstance(data, list) else []:
            if isinstance(e, str):
                out.append((e, ''))
            elif isinstance(e, dict):
                out.append((str(e.get('path') or e.get('file') or e.get('image') or ''),
                            ' '.join(str(e.get(k) or '') for k in ('role', 'name', 'label', 'kind', 'use'))))
        return out
    return [(ln.strip(), '') for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]


def scan_refs(paths):
    """R4Q2 (广告skill 11-05): a reference picture that is the original game's title logo makes the image model draw the
    name again. Reported when its file name (not the folders) or its role says title / logo / banner."""
    hits = []
    for path in paths:
        for ref, role in _ref_entries(path):
            name = Path(ref).name
            m = REF_TITLE.search(name) or REF_TITLE.search(role)
            if m:
                hits.append({'kind': 'title_logo_reference', 'ref': ref, 'matched': m.group(0), 'where': Path(path).name,
                             'fix': 'do not send the original title / logo picture as a reference; send the hero, a '
                                    'scene or a plain button instead'})
    return hits


def scan(text, names, where='text'):
    hits = []
    flat = squash(text)
    for n in names:
        if single_word(n):
            if drawn_as_words(text, n):
                hits.append({'kind': 'game_name_in_prompt', 'name': n, 'where': where, 'fix': FIX})
        elif squash(n) in flat:
            hits.append({'kind': 'game_name_in_prompt', 'name': n, 'where': where, 'fix': FIX})
    for m in TITLE_ASK.finditer(text):
        if NEGATED.search(text[max(0, m.start() - 40):m.start()]):
            continue
        hits.append({'kind': 'title_logo_request', 'text': m.group(0), 'where': where, 'fix': FIX})
    return hits


def scan_file(path, names):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if p.suffix.lower() == '.json':
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if data is not None:   # file paths and ids in a receipt are not prompt text
            return [h for i, s in enumerate(strings(data)) if not PATHLIKE.match(s)
                    for h in scan(s, names, '%s#%d' % (p.name, i))]
    return scan(text, names, p.name)


# R4R1 (Saul 11-05 09:4x: 发现问题直接处理): --fix rewrites the prompt instead of only reporting it
HERO = 'the main character with props from the game, a pattern or the scene'
NO_WORDS = 'no text, no letters, no words'
SAYS_QUOTED = re.compile(r'(?i)\s*,?\s*\b(?:that\s+reads|reading|reads|saying|says|which\s+says|spelling|spelled|'
                         r'with\s+the\s+(?:words?|text|letters|name)|with\s+(?:words?|text|letters))\s*[:：]?\s*'
                         r'(?:"[^"\n]{0,60}"|“[^”\n]{0,60}”|‘[^’\n]{0,60}’|「[^」\n]{0,60}」)')


def _loose(name):
    chars = [c for c in squash(name)]
    return re.compile(r'(?i)' + r'[\s_\-·・.:：]*'.join(re.escape(c) for c in chars) + r"(?:['’]s\b)?")


def fix_text(text, names):
    """-> (new_text, changes). Removes 'reading "NAME"' parts, turns title / logo / game-name requests and the name
    itself into the hero / pattern / scene, and adds 'no text, no letters, no words'. Scan it again afterwards."""
    out, changes = str(text), []

    def note(kind, old, new):
        changes.append({'kind': kind, 'old': old, 'new': new})
    for m in list(SAYS_QUOTED.finditer(out)):
        note('words_request_removed', m.group(0).strip(), '')
    out = SAYS_QUOTED.sub('', out)
    for n in names:
        if single_word(n):
            # only where it is drawn as words: quoted, or next to a words cue (same rule as scan)
            for q in list(QUOTED.finditer(out)):
                if re.search(r'(?i)\b%s\b' % re.escape(n.strip()), q.group(0)):
                    note('quoted_name_removed', q.group(0), '')
                    out = out.replace(q.group(0), '')
            pat = re.compile(r'(?i)\b%s\b(\s+(?:logo|title|text|wordmark|lettering|letters|sign|banner)\b)?' %
                             re.escape(n.strip()))
            if drawn_as_words(out, n):
                for m in list(pat.finditer(out)):
                    note('game_name_replaced', m.group(0), HERO)
                out = pat.sub(HERO, out)
        else:
            pat = _loose(n)
            for m in list(pat.finditer(out)):
                note('game_name_replaced', m.group(0), HERO)
            out = pat.sub(HERO, out)
    for m in list(TITLE_ASK.finditer(out)):
        note('title_logo_request_replaced', m.group(0), 'picture of ' + HERO)
    out = TITLE_ASK.sub('picture of ' + HERO, out)
    # one hero phrase is enough
    out = re.sub(r'(?i)(?:picture of\s+)?(%s)(?:\s*(?:,|and|with|of)?\s*(?:picture of\s+)?%s)+' % (
        re.escape(HERO), re.escape(HERO)), r'\1', out)
    if changes:   # leftover lettering asks ("in big golden letters") make the model draw words again
        out = re.sub(r'(?i)\s*,?\s*(?<!no )\b(?:in\s+)?(?:(?:big|bold|large|golden|gold|3d|shiny|glossy|chunky)\s+)*'
                     r'(?:letters|lettering|typography|wordmark)\b', '', out)
    out = re.sub(r'\s{2,}', ' ', out).replace(' ,', ',').strip(' ,')
    if changes and not re.search(r'(?i)\bno\s+(text|words|letters)\b', out):
        out = out.rstrip(' .') + ', ' + NO_WORDS + '.'
        note('no_words_added', '', NO_WORDS)
    return out, changes


def _fix_data(data, names, changes, where):
    if isinstance(data, str):
        if PATHLIKE.match(data):
            return data
        new, ch = fix_text(data, names)
        changes += [dict(c, where=where) for c in ch]
        return new
    if isinstance(data, dict):
        return {k: _fix_data(v, names, changes, where + '.' + str(k)) for k, v in data.items()}
    if isinstance(data, list):
        return [_fix_data(v, names, changes, '%s[%d]' % (where, i)) for i, v in enumerate(data)]
    return data


def fixed_path(path, out_dir=None):
    p = Path(path)
    return (Path(out_dir) if out_dir else p.parent) / (p.stem + '.fixed' + p.suffix)


def fix_file(path, names, out_dir=None):
    """-> (written path, changes). JSON prompt files keep their shape; ids and paths are left alone."""
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    changes = []
    data = None
    if p.suffix.lower() == '.json':
        try:
            data = json.loads(text)
        except ValueError:
            data = None
    if data is not None:
        new = json.dumps(_fix_data(data, names, changes, p.name), ensure_ascii=False, indent=1) + '\n'
    else:
        new, ch = fix_text(text, names)
        changes = [dict(c, where=p.name) for c in ch]
        new += '\n' if text.endswith('\n') and not new.endswith('\n') else ''
    dst = fixed_path(p, out_dir)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(new, encoding='utf-8')
    return dst, changes


def fix_refs(path, out_dir=None):
    """A .json / .txt reference list without its title / logo / banner pictures -> (written path or None, dropped)."""
    p = Path(path)
    if p.suffix.lower() in IMAGE_EXT:
        return None, [h['ref'] for h in scan_refs([p])]
    dropped = [h['ref'] for h in scan_refs([p])]
    if p.suffix.lower() == '.json':
        data = json.loads(p.read_text(encoding='utf-8'))

        def keep(e):
            ref = e if isinstance(e, str) else str(e.get('path') or e.get('file') or e.get('image') or '') \
                if isinstance(e, dict) else ''
            return ref not in dropped
        if isinstance(data, dict):
            for k in ('refs', 'references', 'images'):
                if isinstance(data.get(k), list):
                    data[k] = [e for e in data[k] if keep(e)]
        elif isinstance(data, list):
            data = [e for e in data if keep(e)]
        new = json.dumps(data, ensure_ascii=False, indent=1) + '\n'
    else:
        new = ''.join(ln + '\n' for ln in p.read_text(encoding='utf-8').splitlines() if ln.strip() not in dropped)
    dst = fixed_path(p, out_dir)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(new, encoding='utf-8')
    return dst, dropped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--file', type=Path, action='append', default=[])
    ap.add_argument('--text', action='append', default=[])
    ap.add_argument('--name', action='append', default=[], help='an extra name to look for')
    ap.add_argument('--names', action='store_true', help='print the names and stop')
    ap.add_argument('--refs', type=Path, action='append', default=[],
                    help='R4Q2: reference pictures sent with the prompt (an image, or a .json / .txt list of them)')
    ap.add_argument('--warn-only', action='store_true')
    ap.add_argument('--fix', action='store_true',
                    help='R4R1: rewrite the prompts (name / title / logo -> hero, pattern or scene, no words), write '
                         '<file>.fixed.<ext> (and a reference list without title pictures), check them again; exit 0 '
                         'when the rewritten prompts are clean')
    ap.add_argument('--out-dir', type=Path, help='with --fix: where the .fixed files go (default: next to each file)')
    a = ap.parse_args(argv)
    if not a.project.is_dir():
        ap.exit(2, 'prompt_name_guard: no project folder %s\n' % a.project)
    names = game_names(a.project, a.name)
    if a.names:
        print(json.dumps({'names': names}, ensure_ascii=False))
        return 0
    if not a.file and not a.text and not a.refs:
        ap.error('give --file, --text or --refs')
    if a.fix:
        written, changes, texts, hits = [], [], [], []
        try:
            for f in a.file:
                dst, ch = fix_file(f, names, a.out_dir)
                written.append(str(dst))
                changes += ch
                hits += scan_file(dst, names)
            for r in a.refs:
                dst, dropped = fix_refs(r, a.out_dir)
                changes += [{'kind': 'title_logo_reference_dropped', 'old': d, 'new': '', 'where': Path(r).name}
                            for d in dropped]
                if dst is not None:
                    written.append(str(dst))
                    hits += scan_refs([dst])
                else:
                    hits += scan_refs([r])     # a single title picture given as --refs: cannot be fixed, drop it
        except (OSError, ValueError) as exc:
            ap.exit(2, 'prompt_name_guard: %s\n' % exc)
        for i, t in enumerate(a.text):
            new, ch = fix_text(t, names)
            texts.append(new)
            changes += [dict(c, where='text#%d' % i) for c in ch]
            hits += scan(new, names, 'text#%d' % i)
        print(json.dumps({'tool': 'prompt_name_guard', 'mode': 'fix', 'names': names, 'written': written,
                          'fixed_texts': texts, 'changes': changes, 'passed': not hits, 'hits': hits},
                         ensure_ascii=False, indent=1))
        return 0 if (not hits or a.warn_only) else 1
    hits = []
    try:
        hits += scan_refs(a.refs)
        for f in a.file:
            hits += scan_file(f, names)
    except OSError as exc:
        ap.exit(2, 'prompt_name_guard: %s\n' % exc)
    for i, t in enumerate(a.text):
        hits += scan(t, names, 'text#%d' % i)
    print(json.dumps({'tool': 'prompt_name_guard', 'names': names, 'passed': not hits, 'hits': hits},
                     ensure_ascii=False, indent=1))
    return 0 if (not hits or a.warn_only) else 1


if __name__ == '__main__':
    sys.exit(main())
