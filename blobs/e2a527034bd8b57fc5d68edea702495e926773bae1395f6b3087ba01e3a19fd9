#!/usr/bin/env python3
"""Check that UI leaves the play area free (user rule 2026-10-20).

Reads docs/ui-layout.json written by the assembly line (one entry per screen and phone ratio):

  {"screens": [
    {"name": "play_9x19", "kind": "gameplay", "size": [750, 1624],
     "elements": [{"name": "pause", "rect": [650, 40, 80, 80]},
                  {"name": "tip", "rect": [100, 300, 400, 90], "temporary": true}]},
    {"name": "pause_9x19", "kind": "popup", "size": [750, 1624], "panel": [95, 420, 560, 700]},
    {"name": "shop_9x19", "kind": "page"}]}

rect = [x, y, width, height] in screenshot pixels, top-left origin.
  gameplay: persistent UI (union of non-temporary rects) <= --max-ui of the screen (default 0.20,
            i.e. play area >= 80%); persistent elements must not overlap; each temporary tip
            <= --max-tip (default 0.08) and must not sit in the central third of the screen.
  popup:    panel <= --max-popup of the screen (default 0.60).
  page:     full pages with their own background; not limited by area (screenshots still measured).

Frames and plaques (anti-clipping, user rule 2026-10-20): every popup, and every framed panel
on a page or in the HUD (listed under "boxes"), declares
    "safe":        [x, y, w, h]  the inner content box: inside the frame border, clear of corner
                                 ornaments, ribbons and plaque edges (from the art line's asset list)
    "decorations": [{"name": "corner_tl", "rect": [...]}, ...]  ornaments, tassels, ribbons
    "contents":    [{"name": "title", "rect": [...]}, ...]      EVERYTHING placed on it: title and
                                 status plaques, text, item showcase, prices, buttons
  each content must sit inside "safe" with >= --min-pad px on every side, must not touch any
  decoration, and contents must not overlap each other. A title ribbon that crosses the frame edge
  must be painted into the frame image itself, not placed on top at runtime.
  Popup: "panel" + "safe"/"decorations"/"contents" directly. Page/gameplay: optional
  "boxes": [{"name", "frame", "safe", "decorations", "contents"}].

Home layout (user rules 2026-10-21, changed 2026-10-23: no more "spread to the four sides"). Menu pages list
    {"name": "home", "kind": "page", "role": "home", "size": [w, h],
     "buttons": [{"name": "play", "rect": [...], "primary": true, "label": "text"},
                 {"name": "settings", "rect": [...], "label": "none"},      # icon only
                 {"name": "wardrobe", "rect": [...], "label": "small"}]}    # icon + one small word
  primary (PLAY/NEXT/main reward): at most 2, each <= --max-primary of the screen and <= 70% width.
  secondary: icon buttons (label none/small, never a text tile), each <= --max-icon of the screen.
  role home, by button name:
    settings / sound / music           a top corner (centre in the top 15%, left or right 25%)
    currency / coin / energy / plus    the top band (centre in the top 20%) with the resource bar
    every other feature                (rewards, map, gift packs, daily check-in, skins, shop, league, add to home,
                                        revisit, help, video ...) together at the BOTTOM: centre below 65% of the height,
                                        in at most 2 rows, side by side with small gaps (<= one button width or 12% of
                                        the screen width) - not split into the corners, not scattered over the page
  other menu pages: secondary buttons not in the middle.
  all buttons together <= --max-menu of the screen (default 0.40, user 2026-10-23: up to 40%, not more).
  At least one page must have role "home". Gameplay HUD elements stay in the edge zones.

Home entries and no sharing (user 2026-10-23, above all for 英化; both boards):
  every role-home page has BOTH the desktop-shortcut button (Add to Home Screen: name like shortcut / add_to_home /
  home_screen / desktop) and the profile-revisit button (name like revisit / profile / entrance / sidebar). 英化 adds
  them to the original home without asking the user.
  No page, popup or HUD may have a share button or share entry (name or button words share / 分享 / invite / 邀请 /
  tell friends / send to friend / 炫耀 / 转发): sharing cannot be used, so an original game's share feature is removed.
  The same for ranking / leaderboard / league, 7-day check-in / sign-in and more games / cross-promotion (removed_feature).

Where the layout comes from (user rule 2026-10-21): docs/ui-layout.json must be produced by
extract_ui_layout.py from chrome_touch.py dump_ui dumps of the running game. This tool re-runs the
extraction from the recorded dumps and rejects a layout that was typed or edited by hand (exit 2).

  python audit_ui_coverage.py docs/ui-layout.json [--binding review.json] [--out report.json]
Exit codes: 0 pass, 1 over a limit, 2 bad input.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def verify_provenance(layout):
    """The layout must be exactly what extract_ui_layout.py builds from the recorded runtime dumps."""
    if not isinstance(layout, dict) or layout.get('provenance') != 'runtime_dump':
        raise ValueError('ui-layout.json must be built by extract_ui_layout.py from dump_ui dumps of the running game '
                         '(chrome_touch.py {"type":"dump_ui"}); hand-typed layouts are not accepted')
    import extract_ui_layout as ex
    dumps = layout.get('dumps')
    if not isinstance(dumps, list) or not dumps:
        raise ValueError('ui-layout.json lists no dumps')
    for d in dumps:
        p = Path(str(d.get('path', '')))
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != d.get('sha256'):
            raise ValueError('dump missing or changed since extraction: %s (dump again and re-run extract_ui_layout.py)' % p)
    ov = layout.get('overrides')
    ov_path = None
    if ov:
        ov_path = Path(str(ov.get('path', '')))
        if not ov_path.is_file() or hashlib.sha256(ov_path.read_bytes()).hexdigest() != ov.get('sha256'):
            raise ValueError('overrides file missing or changed since extraction: %s (re-run extract_ui_layout.py)' % ov_path)
    again = ex.build([d['path'] for d in dumps], ov_path)
    if again['screens'] != layout.get('screens') or again['generator'] != layout.get('generator'):
        raise ValueError('ui-layout.json differs from what the recorded dumps give (edited by hand, or made with an older '
                         'extract_ui_layout.py); re-run extract_ui_layout.py instead of editing the file')
    return sum(len(s.get('auto_notes', [])) for s in layout['screens'])


def area_union(rects):
    xs = sorted({v for x, y, w, h in rects for v in (x, x + w)})
    total = 0
    for x0, x1 in zip(xs, xs[1:]):
        spans = sorted((y, y + h) for x, y, w, h in rects if x <= x0 and x + w >= x1)
        covered, end = 0, None
        for a, b in spans:
            if end is None or a > end:
                covered += b - a; end = b
            elif b > end:
                covered += b - end; end = b
        total += covered * (x1 - x0)
    return total


def clip(rect, size):
    x, y, w, h = rect
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(size[0], x + w), min(size[1], y + h)
    return (x0, y0, max(0, x1 - x0), max(0, y1 - y0))


def overlap(a, b, tol=2):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return min(ax + aw, bx + bw) - max(ax, bx) > tol and min(ay + ah, by + bh) - max(ay, by) > tol


def inside(inner, outer, pad=0):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return ix >= ox + pad and iy >= oy + pad and ix + iw <= ox + ow - pad and iy + ih <= oy + oh - pad


def check_box(box, label, frame, problems, pad):
    """Content must stay inside the frame's inner box and off its ornaments."""
    safe = box.get('safe')
    if not valid_rect(safe):
        raise ValueError(label + ': "safe" inner content box [x, y, w, h] required (frame inset from the art asset list)')
    if not inside(safe, frame):
        problems.append(label + ': inner content box extends outside the frame')
    decorations = box.get('decorations', [])
    contents = box.get('contents')
    if not isinstance(decorations, list) or not isinstance(contents, list) or not contents:
        raise ValueError(label + ': list every item placed on it under "contents" (title/status plaques, text, showcase, buttons)')
    named = []
    for kind, items in (('decoration', decorations), ('content', contents)):
        for e in items:
            if not isinstance(e, dict) or not e.get('name') or not valid_rect(e.get('rect')):
                raise ValueError(label + ': each %s needs name and rect' % kind)
    for c in contents:
        if not inside(c['rect'], safe, pad):
            problems.append('%s: %s crosses the inner border (needs %dpx padding inside the frame)' % (label, c['name'], pad))
        for d in decorations:
            if overlap(c['rect'], d['rect']):
                problems.append('%s: %s overlaps frame ornament %s' % (label, c['name'], d['name']))
        named.append(c)
    for i, a in enumerate(named):
        for b in named[i + 1:]:
            if overlap(a['rect'], b['rect']):
                problems.append('%s: %s overlaps %s' % (label, a['name'], b['name']))


def zone(rect, size):
    cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
    w, h = size
    if cy < 0.22 * h:
        return 'top'
    if cy > 0.75 * h:
        return 'bottom'
    if cx < 0.22 * w:
        return 'left'
    if cx > 0.78 * w:
        return 'right'
    return 'center'


# user 2026-10-23: home = currency at the very top, settings in a top corner, all other features compact at the bottom
CORNER_NAMES = re.compile(r'setting|option|gear|config|sound|audio|music|mute|volume', re.I)
TOP_NAMES = re.compile(r'currency|coin|gem|diamond|gold|cash|money|pearl|energy|lightning|stamina|plus|add_?(coin|gem|energy)|'
                       r'buy_?(coin|gem|energy)|top_?bar|wallet', re.I)
TOP_PATHS = re.compile(r'top_?bar|resource_?bar|currency_?bar|hud_?top|(?:^|/)bar/(?:power|key|coin|energy)(?:/|$)', re.I)   # buttons inside the resource bar
SHORTCUT_NAMES = re.compile(r'shortcut|add_?to_?home|addhome|home_?screen|desktop|桌面', re.I)
REVISIT_NAMES = re.compile(r'revisit|profile|entrance|sidebar|side_?bar|return_?visit|回访|个人主页', re.I)
SHARE_WORDS = re.compile(r'share|分享|invite|邀请|tell_?friends?|send_?to_?friends?|炫耀|转发', re.I)
# user 2026-10-23 (both boards): "do more, break more" - no ranking/leaderboard, no 7-day check-in, no more-games cross-promotion
OPTIONAL = {}
REMOVED_WORDS = re.compile(r'leader_?board|ranking|rank_?list|league|排行|排名|check_?in|sign_?in|签到|daily_?login|more_?games|'
                           r'moregame|cross_?promo|更多游戏|交叉推广', re.I)
CORNER_TOP, CORNER_SIDE, TOP_BAND, BOTTOM_AREA, MAX_ROWS, GAP_SHARE = 0.25, 0.25, 0.20, 0.65, 2, 0.12


def leaf(name):
    return str(name).replace('\\', '/').rstrip('/').rsplit('/', 1)[-1]


def home_places(name, sec, size, problems):
    w, h = size
    feats = []
    for b in sec:
        r = clip(b['rect'], size)
        cx, cy = (r[0] + r[2] / 2) / w, (r[1] + r[3] / 2) / h
        n = leaf(b['name'])
        if CORNER_NAMES.search(n):
            if not (cy < CORNER_TOP and (cx < CORNER_SIDE or cx > 1 - CORNER_SIDE)):
                problems.append('%s: %s goes in the top-left or top-right corner (centre at x %.0f%%, y %.0f%%)'
                                % (name, b['name'], cx * 100, cy * 100))
        elif TOP_NAMES.search(n) or TOP_PATHS.search(str(b['name'])):
            if cy >= TOP_BAND:
                problems.append('%s: %s belongs to the resource bar at the very top of the screen (centre at y %.0f%%; '
                                'currency is never in the middle)' % (name, b['name'], cy * 100))
        else:
            feats.append((b, r, cx, cy))
    # User 2026-10-24 supersedes the old all-bottom layout: real entrances on
    # both sides of the hero, at most five beneath PLAY across every row.
    primary_y = getattr(home_places, '_primary_y', 0.7)
    below = [f for f in feats if f[3] > primary_y]
    if len(below) > 5:
        problems.append('%s: %d feature buttons below PLAY (at most 5)' % (name,len(below)))
    middle = [f for f in feats if 0.28 <= f[3] < primary_y]
    if not any(f[2] < 0.4 for f in middle) or not any(f[2] > 0.6 for f in middle):
        problems.append('%s: put at least one real feature entrance on each side of the hero above PLAY' % name)


def check_buttons(s, size, problems, a):
    buttons = s.get('buttons')
    if not isinstance(buttons, list) or not buttons:
        raise ValueError(s['name'] + ': list the page buttons under "buttons"')
    screen = size[0] * size[1]
    prim, sec = [], []
    for b in buttons:
        if not isinstance(b, dict) or not b.get('name') or not valid_rect(b.get('rect')):
            raise ValueError(s['name'] + ': each button needs name and rect')
        if b.get('label', 'none') not in {'none', 'small', 'text'}:
            raise ValueError(s['name'] + ': button label must be none/small/text')
        (prim if b.get('primary') else sec).append(b)
    name = s['name']
    if len(prim) > 2:
        problems.append('%s: %d primary buttons; keep at most 2 big text buttons' % (name, len(prim)))
    for b in prim:
        r = clip(b['rect'], size)
        if r[2] * r[3] / screen > a.max_primary:
            problems.append('%s: primary %s covers %.1f%% of the screen (limit %.0f%%)' % (name, b['name'], r[2] * r[3] / screen * 100, a.max_primary * 100))
        if r[2] > 0.7 * size[0]:
            problems.append('%s: primary %s is wider than 70%% of the screen' % (name, b['name']))
    zones = {}
    for b in sec:
        r = clip(b['rect'], size)
        if b.get('label') == 'text':
            problems.append('%s: %s is a text tile; secondary features use an icon (optionally one small word)' % (name, b['name']))
        if r[2] * r[3] / screen > (max(a.max_icon,0.10) if s.get('role') == 'home' else a.max_icon):
            problems.append('%s: %s covers %.1f%% of the screen (icon limit %.1f%%)' % (name, b['name'], r[2] * r[3] / screen * 100, a.max_icon * 100))
        z = zone(r, size)
        if z == 'center' and s.get('role') != 'home':
            problems.append('%s: %s sits in the middle; move it to the edge' % (name, b['name']))
        zones.setdefault(z, []).append(b['name'])
    if s.get('role') == 'home':
        home_places._primary_y = min(((b['rect'][1]+b['rect'][3]/2)/size[1] for b in prim),default=0.7)
        home_places(name, sec, size, problems)
        leaves = [leaf(b['name']) for b in buttons] + [leaf(n) for n in s.get('entry_names',[])]
        if not any(SHORTCUT_NAMES.search(n) for n in leaves):
            problems.append('%s: no desktop-shortcut button (Add to Home Screen, house icon) on the home page; add it '
                            '(英化 too, without asking the user)' % name)
        if not any(REVISIT_NAMES.search(n) for n in leaves):
            problems.append('%s: no profile-revisit button (Profile Revisit) on the home page; add it '
                            '(英化 too, without asking the user)' % name)
    for i, x in enumerate(buttons):
        for y in buttons[i + 1:]:
            if overlap(clip(x['rect'], size), clip(y['rect'], size)):
                problems.append('%s: buttons %s and %s overlap' % (name, x['name'], y['name']))
    total = area_union([clip(b['rect'], size) for b in buttons]) / screen
    if total > a.max_menu:
        problems.append('%s: buttons cover %.0f%% of the screen (limit %.0f%%)' % (name, total * 100, a.max_menu * 100))
    return {'buttons_ratio': round(total, 4), 'zones': {z: len(v) for z, v in zones.items()}}


def share_entries(s, words=SHARE_WORDS):
    """Names of buttons / elements / popup contents that offer sharing (user 2026-10-23: no share feature at all)."""
    found = []
    for key in ('buttons', 'elements', 'contents'):
        for e in s.get(key) or []:
            if isinstance(e, dict) and e.get('name') and (words.search(leaf(e['name'])) or words.search(str(e.get('text') or ''))):
                found.append(e['name'])
    for b in s.get('boxes') or []:
        if isinstance(b, dict):
            found += share_entries({'contents': b.get('contents')}, words)
    return found


def valid_rect(r):
    return isinstance(r, list) and len(r) == 4 and all(type(v) in (int, float) for v in r) and r[2] > 0 and r[3] > 0


def check(layout, a):
    screens = layout.get('screens') if isinstance(layout,dict) else None
    if not isinstance(screens, list) or not screens:
        raise ValueError('layout needs a non-empty "screens" list')
    if not any(isinstance(s, dict) and s.get('kind') == 'gameplay' for s in screens):
        raise ValueError('at least one gameplay screen is required (one per phone ratio)')
    if not any(isinstance(s, dict) and s.get('role') == 'home' and s.get('buttons') for s in screens):
        raise ValueError('at least one page with role "home" and its "buttons" is required (one per phone ratio)')
    results = []
    for s in screens:
        if not isinstance(s, dict) or not s.get('name') or s.get('kind') not in {'gameplay', 'popup', 'page'}:
            raise ValueError('each screen needs name and kind gameplay/popup/page')
        r = {'name': s['name'], 'kind': s['kind'], 'problems': []}
        shares = share_entries(s)
        if shares or SHARE_WORDS.search(leaf(s['name'])):
            r['problems'].append('share feature on %s (%s): sharing cannot be used, remove the share button/entry and its '
                                 'popup and reward (user 2026-10-23)' % (s['name'], ', '.join(shares[:4]) or 'the screen itself'))
        from feature_policy import removed
        gone = [n for n in share_entries(s, REMOVED_WORDS) if removed(n, OPTIONAL)]
        if gone or removed(leaf(s['name']), OPTIONAL):
            r['problems'].append('removed feature on %s (%s): no ranking/leaderboard, no 7-day check-in, no more games / '
                                 'cross-promotion (user 2026-10-23, references/game-modules.md): delete the button, page and code'
                                 % (s['name'], ', '.join(gone[:4]) or 'the screen itself'))
        for b in s.get('boxes', []) if s['kind'] != 'popup' else []:
            if not isinstance(b, dict) or not b.get('name') or not valid_rect(b.get('frame')):
                raise ValueError(s['name'] + ': each box needs name and frame [x, y, w, h]')
            check_box(b, s['name'] + '/' + b['name'], b['frame'], r['problems'], a.min_pad)
        if s['kind'] == 'page':
            if s.get('buttons'):
                size = s.get('size')
                if not (isinstance(size, list) and len(size) == 2 and all(type(v) in (int, float) and v > 0 for v in size)):
                    raise ValueError(s['name'] + ': size [width, height] required with buttons')
                r.update(check_buttons(s, size, r['problems'], a))
            r['passed'] = not r['problems']; results.append(r); continue
        size = s.get('size')
        if not (isinstance(size, list) and len(size) == 2 and all(type(v) in (int, float) and v > 0 for v in size)):
            raise ValueError(s['name'] + ': size [width, height] required')
        screen = size[0] * size[1]
        if s['kind'] == 'gameplay':
            elements = s.get('elements')
            if not isinstance(elements, list) or not elements:
                raise ValueError(s['name'] + ': list every on-screen UI element')
            fixed, temp = [], []
            for e in elements:
                if not isinstance(e, dict) or not e.get('name') or not valid_rect(e.get('rect')):
                    raise ValueError(s['name'] + ': each element needs name and rect [x, y, w, h]')
                (temp if e.get('temporary') else fixed).append((e['name'], clip(e['rect'], size)))
            ui = area_union([rc for _, rc in fixed]) / screen if fixed else 0.0
            r['ui_ratio'] = round(ui, 4)
            r['play_ratio'] = round(1 - ui, 4)
            if ui > a.max_ui:
                r['problems'].append('persistent UI covers %.0f%% of the screen (limit %.0f%%)' % (ui * 100, a.max_ui * 100))
            for i, (n1, r1) in enumerate(fixed):
                for n2, r2 in fixed[i + 1:]:
                    if overlap(r1, r2):
                        r['problems'].append('UI elements overlap: %s / %s' % (n1, n2))
                if zone(r1, size) == 'center':
                    r['problems'].append('HUD element %s sits in the middle of the play area; move it to an edge' % n1)
            cx0, cx1, cy0, cy1 = size[0] / 3, size[0] * 2 / 3, size[1] / 3, size[1] * 2 / 3
            for n, rc in temp:
                share = rc[2] * rc[3] / screen
                if share > a.max_tip:
                    r['problems'].append('tip %s covers %.0f%% of the screen (limit %.0f%%)' % (n, share * 100, a.max_tip * 100))
                if overlap(rc, (cx0, cy0, cx1 - cx0, cy1 - cy0), tol=0):
                    r['problems'].append('tip %s sits over the central play area' % n)
        else:
            panel = s.get('panel')
            if not valid_rect(panel):
                raise ValueError(s['name'] + ': popup needs panel [x, y, w, h]')
            share = area_union([clip(panel, size)]) / screen
            r['panel_ratio'] = round(share, 4)
            check_box(s, s['name'], panel, r['problems'], a.min_pad)
            if share > a.max_popup:
                r['problems'].append('popup panel covers %.0f%% of the screen (limit %.0f%%)' % (share * 100, a.max_popup * 100))
        r['passed'] = not r['problems']
        results.append(r)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('layout', type=Path)
    ap.add_argument('--max-ui', type=float, default=0.20)
    ap.add_argument('--max-popup', type=float, default=0.60)
    ap.add_argument('--max-tip', type=float, default=0.08)
    ap.add_argument('--max-primary', type=float, default=0.08, help='max screen share of one primary button')
    ap.add_argument('--max-icon', type=float, default=0.025, help='max screen share of one secondary (icon) button')
    ap.add_argument('--max-menu', type=float, default=0.40, help='max screen share of all buttons on a menu page (user 2026-10-23: 40%%)')
    ap.add_argument('--min-pad', type=int, default=8, help='min px between content and the inner frame border (default 8)')
    ap.add_argument('--binding', type=Path, help='known-issue review JSON whose "binding" is copied into the report')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--rules-selftest', action='store_true', help=argparse.SUPPRESS)  # Skill self-tests of the geometry rules only
    a = ap.parse_args()
    global OPTIONAL
    from feature_policy import enabled
    OPTIONAL = enabled(next((p for p in a.layout.resolve().parents if (p / 'assets').is_dir()), a.layout.parent))
    try:
        if a.rules_selftest and (a.out or a.binding):
            raise ValueError('--rules-selftest only checks the geometry rules and never writes a gate report')
        layout = json.loads(a.layout.read_text(encoding='utf-8'))
        notes = None if a.rules_selftest else verify_provenance(layout)
        results = check(layout, a)
        for s, r in zip(layout['screens'], results):
            if s.get('auto_notes'):
                r['auto_notes'] = s['auto_notes']
            if s.get('safe_estimated'):
                r['safe_estimated'] = True
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError('no binding object in ' + str(a.binding))
        if a.out and a.out.exists():
            raise ValueError('output exists: ' + str(a.out))
    except (OSError, ValueError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    failed = sum(1 for r in results if not r['passed'])
    report = {'tool': 'audit_ui_coverage', 'provenance': 'rules_selftest' if a.rules_selftest else 'runtime_dump',
              'auto_notes': notes, 'max_ui': a.max_ui, 'max_popup': a.max_popup, 'max_tip': a.max_tip,
              'min_pad': a.min_pad,
              'checked': len(results), 'failed': failed, 'passed': failed == 0,
              'checks': [{'name': r['name'], 'passed': r['passed']} for r in results], 'results': results,
              'note': 'Measures the layout read from the running game; GPT still compares auto_notes and safe_estimated '
                      'boxes with the contact sheets of the same build.'}
    if binding is not None:
        report['binding'] = binding
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'checked': len(results), 'failed': failed,
                      'over': [{'name': r['name'], 'problems': r['problems']} for r in results if not r['passed']][:10]},
                     ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
