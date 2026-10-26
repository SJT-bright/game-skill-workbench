#!/usr/bin/env python3
"""English copy quality check for player-visible text (user rule 2026-10-21: copy quality is required).

Collects English text from
  - UI dumps of the running game (chrome_touch.py {"type":"dump_ui"}): what players actually see, per screen,
    with font size, overflow mode and the box it must fit in. Found automatically under PROJECT/docs/test.
  - scenes/prefabs (Label/RichText strings), language JSON files, `.string = "..."` in scripts
  - the copy table docs/copy/copy-table.csv (columns zh,en; 英化) if present
and checks:
  blocking  Chinese characters or full-width punctuation in English text; misspelled words (offline dictionary
            assets/english-words.txt.gz + game words + docs/copy/glossary.json "allow"); repeated words ("the the");
            placeholders ({0} %d ${x}) that differ between zh and en; text sticking out of its button/frame
            (measured from the dump); a variant the project glossary bans ("terms": {"Coins": ["Gold"]})
  review    Chinglish phrases with a suggestion ("Receive" -> "Claim", "Gold coins" -> "Coins", "Click" -> "Tap" ...);
            mixed names for one thing (Coins/Gold, Energy/Stamina, Back/Return ...); mixed button case
            (PLAY / Play); one Chinese source translated two ways; text that may be cut (CLAMP) or shrunk
            too small (SHRINK); spacing slips; very long button labels
Natural wording and tone still need a reader: --sheet writes a review sheet for GPT (COPY-01 "native_phrasing_review").

  python audit_copy_quality.py --project GAME [--dumps DIR_OR_FILES...] [--copy-table CSV] [--glossary JSON]
                               [--sheet copy-review.md] [--binding review.json] [--out result.json]
Exit codes: 0 nothing blocking, 1 blocking issues, 2 bad input.
"""
import argparse
import csv
import fnmatch
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORDS = HERE.parent / 'assets' / 'english-words.txt.gz'
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles'}
HAN = re.compile('[㐀-䶿一-鿿豈-﫿]')
FULLWIDTH = re.compile('[，。！？：；“”‘’（）【】、…—《》]')
LATIN = re.compile('[A-Za-z]')
PLACEHOLDER = re.compile(r'\{[^{}]{0,20}\}|%[-+0-9.]*[sdif@]|\$\{[^}]{0,40}\}')
TAG = re.compile(r'<[^<>]{1,80}>')
TOKEN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
GAME_WORDS = set('''leaderboard leaderboards powerup powerups respawn respawns tiktok sfx bgm ui hud vip xp hp lvl lv pts ok
x2 x3 x5 gameplay minigame minigames unlockable unlockables emoji emojis app apps ad ads booster boosters checkpoint
checkpoints combo combos revisit rewarded skin skins avatar avatars username nickname offline online login logout
signup multiplayer pvp pve npc fps gg wifi ios android faq diy ingame mini megacombo playable hiscore highscore
tap taps swipe swipes unlocked unlocks shortcut shortcuts homescreen pts aww yay woohoo whoa oops hmm brr'''.split())
CHINGLISH = [
    (r'\breceive\b', '"Receive" 是中式说法（领取）→ 用 "Claim"'),
    (r'\bgold coins?\b', '"Gold coins" → 一般就叫 "Coins"'),
    (r'\bphysical strength\b', '"Physical strength"（体力）→ "Energy" 或 "Lives"'),
    (r'\bprops?\b', '"Prop(s)"（道具）→ "Item(s)" 或 "Booster(s)"'),
    (r'\bchallenge (failed|failure|fail)\b', '"Challenge failed" → "Level Failed"'),
    (r'\b(challenge success(ful)?|congratulations on passing|pass(ed)? the level|level passed|successfully passed)\b',
     '过关 → "Level Complete!"'),
    (r'\b(customs clearance|clear(ed)? (the )?customs|clearance)\b', '"通关" 被机翻成海关用语 → "Level Complete"'),
    (r'\bsign[ -]?in\b', '"Sign in"（签到）→ "Daily Reward" 或 "Check-in"'),
    (r'\bstart (the )?game\b', '"Start game" → "Play"'),
    (r'^return$', '"Return"（返回）按钮 → "Back" 或 "Home"'),
    (r'\bexperience\b', '"Experience"（体验/试用）→ "Try" / "Try it"'),
    (r'\b(turntable|lucky draw)\b', '"Turntable/Lucky draw"（转盘/抽奖）→ "Lucky Spin" / "Spin"'),
    (r'\badvertis(e|ement|ing)\b', '"Advertisement" → 按钮写 "Watch Ad"'),
    (r'\b(free to get|get for free)\b', '→ "Free" 或 "Get Free"'),
    (r'\bdouble (receive|reward|claim)\b', '"双倍领取" → "Claim x2"'),
    (r'\bplease\b', 'UI 里少用 "Please"，直接说动作（"Tap to continue"）'),
    (r'\bclick\b', '手机游戏用 "Tap"，不用 "Click"'),
    (r'\binsufficient\b', '"Insufficient ..." → "Not enough ..."'),
    (r'\b\w+ (successfully|success)!?$', '"... successfully" → 简短感叹，如 "Unlocked!" "Purchased!"'),
    (r'\b(network (is )?(abnormal|anomaly)|abnormal)\b', '"网络异常" → "Connection error. Try again."'),
    (r'\bresurrect(ion)?\b', '"Resurrect" → "Revive"'),
    (r'^setting$', '"Setting" → "Settings"'),
    (r'\b(music effect|sound effect switch)\b', '→ "Sound" / "SFX"'),
    (r'^(open|close)$', '开关状态的 "Open/Close" → "On/Off"'),
    (r'\bshake\b', '"Shake"（震动开关）→ "Vibration"'),
    (r'\bobtain(ed)?\b', '"Obtain" 太正式 → "Get" / "You got ..."'),
    (r'\bcongratulations (to you|you|on obtaining|on getting)\b', '→ "You got ...!" / "Congrats!"'),
    (r'\bcan not\b', '"can not" → "can\'t" 或 "cannot"'),
    (r'\bremaining times?\b|\btimes left\b', '剩余次数 → "x left" / "Left today: x"'),
    (r'\bcheckpoint\b', '"Checkpoint"（关卡）→ "Level"'),
]
CONCEPTS = [
    ('金币', {'Coins': r'\bcoins?\b', 'Gold': r'\bgold\b(?! (medal|star|cup|trophy))'}),
    ('体力', {'Energy': r'\benergy\b', 'Stamina': r'\bstamina\b', 'Strength': r'\bstrength\b', 'Lives': r'\blives\b', 'Hearts': r'\bhearts\b'}),
    ('领取', {'Claim': r'^claim\b', 'Receive': r'^receive\b', 'Collect': r'^collect\b', 'Get': r'^get\b'}),
    ('关卡', {'Level': r'\blevels?\b', 'Stage': r'\bstages?\b', 'Round': r'\brounds?\b'}),
    ('返回', {'Back': r'^back$', 'Return': r'^return$'}),
    ('重玩', {'Retry': r'^retry$', 'Try Again': r'^try again$', 'Restart': r'^restart$', 'Replay': r'^replay$'}),
    ('设置', {'Settings': r'^settings$', 'Setting': r'^setting$', 'Options': r'^options$'}),
    ('音效', {'Sound': r'^sound$', 'SFX': r'^sfx$', 'Sound Effects': r'^sound effects$'}),
]


def load_words(extra):
    words = set(GAME_WORDS)
    with gzip.open(WORDS, 'rt', encoding='utf-8') as f:
        for line in f:
            if line and not line.startswith('#'):
                words.add(line.strip())
    for w in extra:
        for t in TOKEN.findall(w):
            words.add(t.lower())
    return words


def misspelled(body, words):
    bad = set()
    for t in TOKEN.findall(body):
        w = t.lower()
        if len(w) <= 2 or w in words:
            continue
        if (w.endswith("'s") and w[:-2] in words) or (w.endswith('s') and w[:-1] in words):
            continue
        bad.add(t)
    return sorted(bad)


def clean(s):
    return ' '.join(TAG.sub('', s).replace('\\n', ' ').split())


def case_style(s):
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return None
    if all(c.isupper() for c in letters):
        return 'UPPER'
    ws = [w for w in re.findall(r'[A-Za-z]+', s)]
    if len(ws) == 1:
        return 'Title' if ws[0][0].isupper() else 'lower'
    if all(w[0].isupper() for w in ws if len(w) > 3):
        return 'Title'
    return 'Sentence' if ws[0][0].isupper() else 'lower'


def under(path, prefix):
    return path == prefix or path.startswith(prefix + '/')


def runtime_strings(dump_inputs):
    files = []
    for raw in dump_inputs:
        p = Path(raw)
        if p.is_dir():
            files += sorted(p.rglob('*ui-dump*.json'))
        elif p.is_file():
            files.append(p)
    out = []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or d.get('tool') != 'ui_dump' or d.get('error'):
            continue
        nodes = [n for n in d.get('nodes', []) if n.get('opacity', 1) >= 0.05]
        buttons = [n['path'] for n in nodes if 'button' in n.get('comps', {})]
        for n in nodes:
            c = n.get('comps', {})
            lab = c.get('label') or c.get('richtext')
            if not lab or not str(lab.get('string', '')).strip():
                continue
            text = clean(str(lab['string']))
            owner = next((b for b in sorted(buttons, key=len, reverse=True) if under(n['path'], b)), None)
            # the box the text must fit in: its button, else the nearest ancestor with a sprite (plaque/frame)
            container = None
            if owner:
                container = next(x for x in nodes if x['path'] == owner)
            else:
                anc = [x for x in nodes if 'sprite' in x.get('comps', {}) and x['path'] != n['path'] and under(n['path'], x['path'])]
                container = max(anc, key=lambda x: x['path'].count('/')) if anc else None
            out.append({'text': text, 'source': 'runtime', 'path': n['path'], 'where': '%s:%s' % (d.get('screen', f.stem), n['path']),
                        'screen': d.get('screen', f.stem), 'button': bool(owner), 'rect': n.get('rect'),
                        'container': container.get('rect') if container else None,
                        'container_path': container['path'] if container else None,
                        'canvas': d.get('canvas_css'), 'dpr': (d.get('page') or {}).get('dpr', 1),
                        'fontSize': lab.get('fontSize'), 'overflow': lab.get('overflow'), 'actualFontSize': lab.get('actualFontSize'),
                        'width': lab.get('width')})
    return out, len(files)


def static_strings(project):
    out = []
    for p in sorted((project / 'assets').rglob('*')):
        if not p.is_file() or SKIP_DIRS & {x.lower() for x in p.relative_to(project).parts}:
            continue
        rel = p.relative_to(project).as_posix()
        try:
            text = p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if p.suffix in {'.prefab', '.fire', '.scene'}:
            for m in re.finditer(r'"_(?:N\$)?string"\s*:\s*"((?:[^"\\]|\\.)*)"', text):
                out.append({'text': clean(json.loads('"' + m.group(1) + '"')), 'source': 'scene', 'where': rel})
        elif p.suffix == '.json' and re.search(r'i18n|lang|locale|language|text|copy|string', rel, re.I):
            try:
                data = json.loads(text)
            except ValueError:
                continue
            stack = [data]
            while stack:
                x = stack.pop()
                if isinstance(x, dict):
                    stack += list(x.values())
                elif isinstance(x, list):
                    stack += x
                elif isinstance(x, str) and ' ' in x.strip() or (isinstance(x, str) and x[:1].isupper()):
                    out.append({'text': clean(x), 'source': 'lang', 'where': rel})
        elif p.suffix in {'.ts', '.js'}:
            for m in re.finditer(r'\.string\s*=\s*([\'"`])((?:(?!\1)[^\\]|\\.){1,300})\1', text):
                raw = re.sub(r'\\u\{?([0-9a-fA-F]{4,5})\}?', lambda u: chr(int(u.group(1), 16)), m.group(2))
                out.append({'text': clean(raw.replace('\\"', '"').replace("\\'", "'")), 'source': 'code', 'where': rel})
    return [s for s in out if LATIN.search(s['text']) and not HAN.search(s['text'])
            and not re.fullmatch(r'[\w./-]*(_|/|\.png|\.json)[\w./-]*', s['text'])]


def copy_table(path):
    rows = []
    if not path or not Path(path).is_file():
        return rows
    with open(path, encoding='utf-8-sig', newline='') as f:
        for i, r in enumerate(csv.DictReader(f), 2):
            zh, en = (r.get('zh') or r.get('cn') or r.get('chinese') or '').strip(), (r.get('en') or r.get('english') or '').strip()
            if en or zh:
                rows.append({'zh': zh, 'en': clean(en), 'where': '%s:%d' % (Path(path).name, i)})
    return rows


def px(rect, canvas, dpr):
    cx, cy, cw, ch = canvas
    return [(cx + rect[0] * cw) * dpr, (cy + rect[1] * ch) * dpr, rect[2] * cw * dpr, rect[3] * ch * dpr]


def audit(project, dumps, table_path, glossary_path):
    glossary = json.loads(Path(glossary_path).read_text(encoding='utf-8')) if glossary_path and Path(glossary_path).is_file() else {}
    words = load_words(glossary.get('allow', []))
    try:
        runtime_manifest = json.loads((Path(project) / 'docs' / 'text' / 'runtime-text.json').read_text(encoding='utf-8-sig'))
        runtime_patterns = [str(x['path']) for x in runtime_manifest.get('labels', [])
                            if isinstance(x, dict) and x.get('path') and str(x.get('why', '')).strip()]
    except (OSError, ValueError, AttributeError, TypeError):
        runtime_patterns = []
    runtime, dump_files = runtime_strings(dumps)
    strings = runtime + static_strings(project)
    table = copy_table(table_path)
    strings += [{'text': r['en'], 'source': 'copy_table', 'where': r['where']} for r in table if r['en']]
    blocking, review = [], []

    def add(lst, s, kind, msg):
        lst.append({'kind': kind, 'text': s['text'], 'where': s['where'], 'source': s['source'], 'message': msg})

    seen = {}
    for s in strings:
        seen.setdefault(s['text'], []).append(s)
    for text, occ in seen.items():
        s = occ[0]
        if HAN.search(text):
            add(blocking, s, 'chinese', '英文里还有中文')
            continue
        if FULLWIDTH.search(text) and LATIN.search(text):
            add(blocking, s, 'fullwidth_punctuation', '英文里用了中文全角标点：' + ''.join(sorted(set(FULLWIDTH.findall(text)))))
        body = PLACEHOLDER.sub(' ', text)
        bad = misspelled(body, words)
        spelling_targets = [o for o in occ if not (
            o.get('source') == 'runtime' and any(fnmatch.fnmatch(o.get('path', ''), p) or
                                                  fnmatch.fnmatch(o.get('path', ''), '*/' + p)
                                                  for p in runtime_patterns))]
        if bad and spelling_targets:
            add(blocking, spelling_targets[0], 'spelling', '拼写不在词典里：' + ', '.join(bad) + '（真是游戏专有词就加进 docs/copy/glossary.json 的 allow）')
        rep = re.search(r'\b(\w+)\s+\1\b', body, re.I)
        if rep and not rep.group(1).isdigit():
            add(blocking, s, 'repeated_word', '重复的词："%s %s"' % (rep.group(1), rep.group(1)))
        for canon, banned in (glossary.get('terms') or {}).items():
            for b in banned:
                if re.search(r'\b' + re.escape(b) + r'\b', text, re.I):
                    add(blocking, s, 'glossary', '本游戏规定叫 "%s"，不用 "%s"' % (canon, b))
        low = text.lower()
        for pat, tip in CHINGLISH:
            if re.search(pat, low):
                add(review, s, 'chinglish', tip)
        if re.search(r'\s[,.!?;:]', text) or re.search(r'[,!?;](?=[A-Za-z])', text) or '  ' in text:
            add(review, s, 'spacing', '空格或标点位置不对')
        if any(o.get('button') for o in occ) and len(text) > 18:
            add(review, s, 'long_button', '按钮文字太长（%d 个字符），手机上不好读' % len(text))
        if len(text.split()) > 6 and text.isupper():
            add(review, s, 'all_caps_sentence', '整句全大写不好读，长句用正常大小写')
    # text must fit: measured from the running game
    for s in runtime:
        if not s.get('rect') or not s.get('canvas'):
            continue
        r = px(s['rect'], s['canvas'], s['dpr'] or 1)
        if s.get('container'):
            c = px(s['container'], s['canvas'], s['dpr'] or 1)
            over = max(c[0] - r[0], c[1] - r[1], (r[0] + r[2]) - (c[0] + c[2]), (r[1] + r[3]) - (c[1] + c[3]))
            if s.get('overflow') in (0, 3, None) and over > 4:
                add(blocking, s, 'overflow', '文字超出 %s %.0fpx（%s）' % ('按钮' if s['button'] else '底图', over, s['container_path']))
        fs, ov, width = s.get('fontSize') or 0, s.get('overflow'), s.get('width') or 0
        if ov == 1 and fs and width and len(s['text']) * fs * 0.55 > width * 1.05 and '\n' not in s['text']:
            add(review, s, 'maybe_cut', '这段字可能被截断（CLAMP 模式，估计需要 %.0f，只有 %.0f）' % (len(s['text']) * fs * 0.55, width))
        if ov == 2 and fs and s.get('actualFontSize') and s['actualFontSize'] < 0.6 * fs:
            add(review, s, 'shrunk', '字被自动缩到 %s（原 %s），手机上可能看不清' % (s['actualFontSize'], fs))
    # one thing, one name
    for concept, variants in CONCEPTS:
        found = {}
        for text in seen:
            for name, pat in variants.items():
                if re.search(pat, text.lower()):
                    found.setdefault(name, []).append(text)
        if len(found) > 1:
            review.append({'kind': 'terminology', 'text': ' / '.join(sorted(found)), 'where': concept, 'source': 'all',
                           'message': '同一个东西（%s）用了不同叫法：%s；统一成一个' % (concept, '；'.join(
                               '%s（%s）' % (k, '、'.join(sorted(v)[:3])) for k, v in sorted(found.items())))})
    styles = {}
    for s in runtime:
        if s['button']:
            st = case_style(s['text'])
            if st:
                styles.setdefault(st, set()).add(s['text'])
    if len(styles) > 1:
        review.append({'kind': 'button_case', 'text': '', 'where': 'buttons', 'source': 'runtime',
                       'message': '按钮大小写不统一：' + '；'.join('%s：%s' % (k, '、'.join(sorted(v)[:4])) for k, v in sorted(styles.items()))})
    by_zh = {}
    for r in table:
        if r['zh'] and r['en']:
            by_zh.setdefault(r['zh'], set()).add(r['en'])
        zp, ep = sorted(PLACEHOLDER.findall(r['zh'])), sorted(PLACEHOLDER.findall(r['en']))
        if zp != ep and r['en']:
            blocking.append({'kind': 'placeholder', 'text': r['en'], 'where': r['where'], 'source': 'copy_table',
                             'message': '占位符对不上：中文 %s，英文 %s' % (zp or '无', ep or '无')})
    for zh, ens in by_zh.items():
        if len(ens) > 1:
            review.append({'kind': 'translated_two_ways', 'text': ' / '.join(sorted(ens)), 'where': zh, 'source': 'copy_table',
                           'message': '同一句中文"%s"翻成了不同英文' % zh})
    return {'strings': strings, 'unique': len(seen), 'runtime': len(runtime), 'dump_files': dump_files,
            'table_rows': len(table), 'blocking': blocking, 'review': review}


def sheet(result, path):
    lines = ['# 英文文案审查单', '', '给 GPT：逐条读玩家看到的英文。看是否自然地道、语气统一（轻松友好的休闲游戏口吻）、意思和中文一致、'
             '按钮短而清楚。自动标记只是线索，最后的判断写进 COPY-01 的 native_phrasing_review（改了哪些、为什么）。', '',
             '自动检查：%d 条阻断，%d 条待看。' % (len(result['blocking']), len(result['review'])), '']
    flags = {}
    for x in result['blocking'] + result['review']:
        flags.setdefault(x['text'], []).append(('❌ ' if x in result['blocking'] else '⚠️ ') + x['message'])
    screens = {}
    for s in result['strings']:
        screens.setdefault(s.get('screen') or ('（源码）' + s['source']), {}).setdefault(s['text'], s)
    for scr in sorted(screens):
        lines += ['## ' + scr, '', '| 文字 | 位置 | 自动标记 |', '| --- | --- | --- |']
        for text, s in screens[scr].items():
            lines.append('| %s | %s | %s |' % (text.replace('|', '/'), s['where'].replace('|', '/')[-60:], '<br>'.join(flags.get(text, []))))
        lines.append('')
    other = [x for x in result['review'] if x['kind'] in ('terminology', 'button_case', 'translated_two_ways')]
    if other:
        lines += ['## 全局', ''] + ['- ' + x['message'] for x in other]
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dumps', nargs='*', help='ui-dump files or folders (default: PROJECT/docs/test if it exists)')
    ap.add_argument('--copy-table', type=Path)
    ap.add_argument('--glossary', type=Path)
    ap.add_argument('--sheet', type=Path, help='write a markdown review sheet for GPT')
    ap.add_argument('--require-runtime', action='store_true', help='fail when no UI dump of the running game was found')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        if not (a.project / 'assets').is_dir():
            raise ValueError('no assets folder in %s' % a.project)
        if a.out and a.out.exists():
            raise ValueError('output exists: %s' % a.out)
        if not WORDS.is_file():
            raise ValueError('dictionary missing: %s (reinstall the skill package)' % WORDS)
        dumps = a.dumps if a.dumps else ([a.project / 'docs' / 'test'] if (a.project / 'docs' / 'test').is_dir() else [])
        table = a.copy_table or (a.project / 'docs' / 'copy' / 'copy-table.csv')
        glossary = a.glossary or (a.project / 'docs' / 'copy' / 'glossary.json')
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError('no binding object in %s' % a.binding)
        r = audit(a.project, dumps, table, glossary)
    except (OSError, ValueError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False))
        return 2
    blocking = list(r['blocking'])
    if a.require_runtime and not r['runtime']:
        blocking.append({'kind': 'no_runtime_text', 'text': '', 'where': '', 'source': 'runtime',
                         'message': '没有读到运行中游戏的文字：先用 chrome_touch.py dump_ui 把每个页面和弹窗读一遍'})
    report = {'tool': 'audit_copy_quality', 'checked': r['unique'], 'failed': len(blocking), 'passed': not blocking,
              'runtime_strings': r['runtime'], 'dump_files': r['dump_files'], 'copy_table_rows': r['table_rows'],
              'checks': [dict(x, id='%s:%s' % (x['kind'], x['where'])[:120], passed=False) for x in blocking],
              'review': r['review'],
              'note': 'Automatic checks only. Natural wording, tone and meaning are judged by GPT from the review sheet (COPY-01).'}
    if binding is not None:
        report['binding'] = binding
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if a.sheet:
        a.sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet(dict(r, blocking=blocking), a.sheet)
    print(json.dumps({'checked': r['unique'], 'runtime_strings': r['runtime'], 'blocking': len(blocking), 'review': len(r['review']),
                      'found': [{k: x[k] for k in ('where', 'text', 'message')} for x in blocking[:8]],
                      'look_at': [{k: x[k] for k in ('where', 'text', 'message')} for x in r['review'][:6]]}, ensure_ascii=False))
    return 1 if blocking else 0


if __name__ == '__main__':
    sys.exit(main())
