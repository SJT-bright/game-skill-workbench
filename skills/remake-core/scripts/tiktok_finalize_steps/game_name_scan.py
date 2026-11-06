"""Source step (read only, well under 1 s): the game's own name shown as text in the game (生成时预防 Round 4 R4O1).

Saul 2026-11-05: "以后的游戏都不要出现游戏名字，把对应的部分换成图案或者主角等美工来填充". No home title, loading
title, settings / result / popup line carries the game's name; the place a title would take holds the hero, a
pattern or a scene picture. Page titles and button words (PLAY, SETTINGS, LEVEL COMPLETE) stay generated word pictures.
This step reads text: the string of every Label / RichText / EditBox in scenes and prefabs (`_string`,
`_N$string`), the English column of docs/copy/copy-table.csv, and (R4Q2) picture transcriptions already on disk.

Where the name comes from (all of them, deduplicated):
  1. docs/copy/glossary.json "game_name": a string or a list (English name, Chinese name, short name). Write it at
     the start of every new game; it is the only source a session controls on purpose.
  2. projectname in project.config.json / build-templates/bytedance*/project.config.json.
  3. "name" in package.json (Cocos 3.x), unless it is a default such as "my-project" / "NewProject".
  4. the project folder and its parent folder (prefixes like 新289_ and suffixes like _v3 / -Cocos-Source dropped):
     NimsNightJars -> "Nims Night Jars"; a Chinese run of 3+ characters (射击高手) counts as the Chinese name.
A text matches when, with case, spaces and punctuation removed, it contains a name of at least 6 letters / digits
(or 3 Chinese characters): "Nim's Night Jars" matches NimsNightJars. Texts listed in glossary "game_name_ok" are
allowed (a hero who carries the game's name, a sentence that has to say it).

Levels: new game (remake, or English since R4Q2) begun by `init` at / after NO_NAME_SINCE -> block (K_game_name_text);
other new games (in progress, begun earlier or taken over) -> warning (K_W_game_name_text); legacy -> not checked.
R4Q2: words in pictures are matched too, from transcriptions that already exist (image_texts: chinese-audit OCR rows of
pictures still in the project, review.py receipts); no new OCR is run here.
Called by tiktok_finalize `source` (SOURCE_STEPS) and `sync` (SYNC_SOURCE_STEPS). CLI: scripts/audit_game_name.py.
"""
import csv
import datetime
import io
import json
import re
import time
from pathlib import Path

from . import Result

STEP = 'game_name_scan'
GATE = 'K_game_name_text'
NO_NAME_SINCE = '2026-11-05T00:00:00-0800'     # Saul's rule, 2026-11-05 (PST)
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit', '__macosx', 'profiles',
             'tiktok-platform'}
SCENE_SUFFIXES = ('.fire', '.scene', '.prefab')
MAX_BYTES = 8 * 1024 * 1024
STRING_KEY = re.compile(r'"(?:_N\$string|_string)"\s*:\s*"((?:[^"\\]|\\.)*)"')
DEFAULT_NAMES = {'myproject', 'newproject', 'helloworld', 'cocosgame', 'cocostiktok', 'game', 'project', 'assets',
                 'cocoscreator', 'tiktokgame', 'minigame', 'bytedance', 'webmobile'}
WORKFLOW_WORDS = ('自制游戏', '自制', '交付候选', '交付', '候选', '源码', '测试', '英化', '重塑', '完结', '工程', '副本',
                  '新版', '最终', '修复', '试玩', '本地', '中文原版', '原版',
                  '英文成品', '成品')                                      # R4R1: 学习库 …/英文成品/X-English
CJK = re.compile(r'[\u4e00-\u9fff]{3,}')


def norm(text):
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]+', '', str(text).lower())


def _strong(n):
    cjk = len(re.findall(r'[\u4e00-\u9fff]', n))
    return cjk >= 3 or (cjk == 0 and len(n) >= 6)


def _folder_names(folder):
    out = []
    s = re.sub(r'^(?:新)?\d+[_\-. ]*', '', folder)                       # 新289_FogPier -> FogPier
    s = re.sub(r'[_\-. ]*(?:v|r|fix)\d+.*$', '', s, flags=re.I)          # _v3, -r27, _fix1 ...
    s = re.sub(r'[_\-. ]*(?:cocos.*source|source|english|tiktok.*|test.*|\d{8}.*)$', '', s, flags=re.I)
    for w in WORKFLOW_WORDS:
        s = s.replace(w, ' ')
    ascii_part = re.sub(r'[\u4e00-\u9fff]+', ' ', s)
    if norm(ascii_part):
        out.append(re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', ascii_part).strip(' _-.'))
    out += CJK.findall(s)
    return out


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}


def glossary(root):
    g = _read_json(root / 'docs' / 'copy' / 'glossary.json')
    return g if isinstance(g, dict) else {}


def names_of(root):
    """-> [(name, source)] for the project at root, strongest sources first, deduplicated by normalized form."""
    found = []
    g = glossary(root)
    v = g.get('game_name')
    for n in ([v] if isinstance(v, str) else v if isinstance(v, list) else []):
        found.append((n, 'docs/copy/glossary.json game_name'))
    cfgs = [root / 'project.config.json'] + sorted(root.glob('build-templates/bytedance*/project.config.json'))
    for p in cfgs:
        n = _read_json(p).get('projectname') if p.is_file() else None
        if isinstance(n, str):
            found.append((n, p.relative_to(root).as_posix() + ' projectname'))
    pk = _read_json(root / 'package.json') if (root / 'package.json').is_file() else {}
    if isinstance(pk.get('name'), str):
        found.append((pk['name'], 'package.json name'))
    for folder, src in ((root.name, 'project folder'), (root.parent.name, 'parent folder')):
        for n in _folder_names(folder):
            found.append((n, src + ' ' + folder))
    out, seen = [], set()
    for n, src in found:
        k = norm(n)
        if not k or k in seen or k in DEFAULT_NAMES or not _strong(k):
            continue
        seen.add(k)
        out.append((n, src))
    return out


def texts_of(root):
    """-> [(rel, where, text)]: Label / RichText strings in scenes and prefabs, English column of the copy table."""
    out = []
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root).as_posix()
        if any(part.lower() in SKIP_DIRS for part in p.relative_to(root).parts[:-1]):
            continue
        if p.suffix.lower() in SCENE_SUFFIXES and p.is_file() and p.stat().st_size <= MAX_BYTES:
            try:
                raw = p.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            for m in STRING_KEY.finditer(raw):
                try:
                    s = json.loads('"%s"' % m.group(1))
                except ValueError:
                    s = m.group(1)
                if s.strip():
                    out.append((rel, 'line %d' % (raw.count('\n', 0, m.start()) + 1), s))
    table = root / 'docs' / 'copy' / 'copy-table.csv'
    if table.is_file():
        try:
            rows = list(csv.reader(io.StringIO(table.read_text(encoding='utf-8-sig'))))
        except (OSError, csv.Error):
            rows = []
        if rows:
            cols = [i for i, h in enumerate(rows[0]) if h.strip().lower() in ('en', 'english', 'en-us', 'text_en')]
            for ln, row in enumerate(rows[1:], 2):
                for i in cols:
                    if i < len(row) and row[i].strip():
                        out.append(('docs/copy/copy-table.csv', 'line %d' % ln, row[i]))
    return out


def _sha_file(p):
    import hashlib
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def image_texts(root):
    """R4Q2 (补查3 第 2 组: ROCKET BLOCKS / CUBE HARVESTER title pictures): words already transcribed from the game's
    pictures, read from receipts that exist; no new OCR. -> [(rel, where, text)].
      1. docs/english/chinese-audit/audit.json (chinese_audit.py scan): each picture / slice row with ocr_text, kept only
         while that file is still in the project with the same bytes (a replaced picture's old receipt does not count).
      2. grok-image-review review.py receipts under docs/ (receipt.json image_path + image_sha256, result.json
         observations), kept only while a project file has that SHA-256."""
    out = []
    audit = _read_json(root / 'docs' / 'english' / 'chinese-audit' / 'audit.json')
    cache = {}
    for it in (audit.get('items') or []) if isinstance(audit, dict) else []:
        if not isinstance(it, dict) or it.get('kind') not in ('image', 'slice') or not it.get('ocr_text'):
            continue
        rel = str(it.get('file') or '')
        p = root / rel
        if not rel or not p.is_file():
            continue
        want = it.get('file_sha256')
        if want and cache.setdefault(rel, _sha_file(p)) != want:
            continue
        text = ' '.join(t for t in it['ocr_text'] if isinstance(t, str))
        if text.strip():
            out.append((rel, 'picture text%s (chinese-audit OCR)' % (' slice ' + str(it['slice']) if it.get('slice') else ''),
                        text))
    docs = root / 'docs'
    for rp in (sorted(docs.rglob('receipt.json')) if docs.is_dir() else [])[:400]:
        rec = _read_json(rp)
        res = _read_json(rp.parent / 'result.json')
        if not (isinstance(rec, dict) and rec.get('image_sha256') and isinstance(res, dict)):
            continue
        obs = res.get('observations')
        text = ' '.join(obs) if isinstance(obs, list) else str(obs or '')
        img = Path(str(rec.get('image_path') or ''))
        cand = [img] if img.is_absolute() else [root / img]
        cand.append(root / 'assets' / img.name)
        hit = next((c for c in cand if c.is_file() and _sha_file(c) == rec['image_sha256']), None)
        if hit is not None and text.strip():
            try:
                rel = hit.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                rel = hit.name
            out.append((rel, 'picture text (review.py %s)' % rp.parent.name, text))
    return out


def scan(root):
    t0 = time.time()
    names = names_of(root)
    ok = {norm(x) for x in (glossary(root).get('game_name_ok') or []) if isinstance(x, str)}
    keys = [(norm(n), n, src) for n, src in names]
    hits, texts = [], texts_of(root) + image_texts(root)
    for rel, where, s in texts:
        k = norm(s)
        if k in ok:
            continue
        for nk, n, src in keys:
            if nk in k:
                hits.append({'file': rel, 'where': where, 'text': s[:80], 'name': n, 'name_from': src})
                break
    return {'names': names, 'texts': len(texts), 'hits': hits, 'seconds': round(time.time() - t0, 3)}


def started_after_rule(root):
    """-> (bool, why): a new game begun by `init` at / after NO_NAME_SINCE (read only)."""
    from .policy import read_marker
    mark = read_marker(root) or {}
    if mark.get('by') != 'init':
        return False, 'not begun by init (marker by %s)' % (mark.get('by') or 'none')
    try:
        created = datetime.datetime.strptime(str(mark.get('created')), '%Y-%m-%dT%H:%M:%S%z')
        since = datetime.datetime.strptime(NO_NAME_SINCE, '%Y-%m-%dT%H:%M:%S%z')
    except ValueError:
        return False, 'start time not readable'
    if created >= since:
        return True, 'begun %s, after the no-game-name rule (2026-11-05)' % mark.get('created')
    return False, 'begun %s, before the no-game-name rule (in progress: warning)' % mark.get('created')


def level_of(policy='new', board=None, after_rule=False):
    if policy == 'legacy':
        return 'skip'
    # R4Q2: English games begun by `init` after the rule block too (before: warning only); earlier ones still warn
    if not after_rule:
        return 'warn'
    return 'block'


def message(hits):
    shown = '; '.join('%s %s "%s" (name "%s" from %s)' % (h['file'], h['where'], h['text'], h['name'], h['name_from'])
                      for h in hits[:8])
    return ('%d text(s) show the game\'s own name: %s. The game shows no game name (Saul 2026-11-05): put the hero, a '
            'pattern or a scene picture where the title was; page titles and button words stay generated word pictures. '
            'A text that must keep it goes into docs/copy/glossary.json "game_name_ok". '
            'Fix it now, no need to ask the user (R4R1): run scripts/fix_game_name.py --project <P> (texts are '
            'emptied / rewritten at once), generate the no-words pictures listed in docs/art/game_name_fix.json and '
            'put them in with the same file names via fix_game_name.py --apply-images <folder>; it scans again'
            % (len(hits), shown))


def detect(ctx):
    if ctx.policy == 'legacy':
        return 'kit_current'
    return 'conflict' if scan(ctx.root)['hits'] else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    if ctx.policy == 'legacy':
        r.state = 'kit_current'
        r.info.append('legacy game: game-name text not checked')
        return r.as_dict()
    found = scan(ctx.root)
    after, why = started_after_rule(ctx.root)
    level = level_of(ctx.policy, getattr(ctx, 'board', None), after)
    if found['hits']:
        if level == 'block':
            r.block(GATE, message(found['hits']), found['hits'][:30])
        else:
            r.warn(GATE.replace('K_', 'K_W_', 1), message(found['hits']), found['hits'][:30])
    r.state = 'conflict' if r.blocks else 'kit_current'
    r.info.append('%d name(s) %s; %d text(s) scanned in %.2f s; %d hit(s); level %s: %s' % (
        len(found['names']), ', '.join('"%s"' % n for n, _ in found['names'][:6]) or '(none found)',
        found['texts'], found['seconds'], len(found['hits']), level, why))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
