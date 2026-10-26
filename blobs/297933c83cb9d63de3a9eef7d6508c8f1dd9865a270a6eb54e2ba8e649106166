#!/usr/bin/env python3
"""Top resource bar (HUD-01, both boards; user 2026-10-22). references/top-bar-and-level-map.md

Things the player watches grow (currency, energy, level/best score) sit in one designed bar at the top of the
screen and change the moment they change. Declared in docs/top-bar.json:
  {"schema": "top_bar.v1", "theme": "ocean",
   "resources": [
     {"kind": "currency", "name": "Pearls", "icon": "pearl", "why": "(only for a plain coin: why coins fit this theme)",
      "node": "TopBar/Pearls", "count": "TopBar/Pearls/Count" or ["...", "Shop/Pearls/Count"]},
     {"kind": "energy", "name": "Energy", "icon": "lightning", "node": "TopBar/Energy", "count": "TopBar/Energy/Count"},
     {"kind": "progress", "name": "Level", "icon": "flag", "node": "TopBar/Level", "count": "TopBar/Level/Count"}]}
Checks (dumps from chrome_touch dump_ui, default <project>/docs/test):
  declared      currency and progress are required (progress = level for level games, best score for endless);
                energy only when the game has energy; a currency named after the game's world (ocean -> pearls,
                candy -> candies, space -> star gems ...): a plain coin icon/name needs "why"; energy uses a lightning icon
  on_pages      home (and map for level games): every resource's count is visible, has a number, sits in the top
                band (top <= 12% of the screen, bottom <= 20%) and keeps the top-right corner free for the platform
                menu capsule (x > 72%, y < 10%); its icon is a sprite whose frame name has the icon word
                (energy: lightning/bolt/thunder); shop and skins pages: the currency count is visible above any mask
  currency_only_at_top  every page except shop/skins/rewards/results/check-in/league (where prices and rewards are
                content) and gameplay: any number next to a currency/energy icon (the declared icons and coin, gem,
                pearl, gold, energy ...) sits in the top band - never in the middle of the screen (user 2026-10-23
                negative example: a "coin 0 / item 1" bar in the middle of the home page). Popups above a mask skipped.
  live          currency (and the level number of a level game) is higher on the first home/map page after a won
                level than on the last one before it, in the same test run
Usage:
  python audit_top_bar.py --project <game> [--dumps <folder> ...] [--binding review.json] --out report.json
Exit codes: 0 pass, 1 fail, 2 bad input. Codex still looks at the bar on the contact sheet (art_check LOOK list).
"""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_page_richness import load as load_dumps, text as node_text, area  # noqa: E402
from audit_level_plan import plan_mode  # noqa: E402

GENERIC_COIN = re.compile(r'^(coin|coins|gold|gold[\s_-]?coins?|money|cash)$', re.I)
LIGHTNING = re.compile(r'lightning|bolt|thunder|flash', re.I)
NUMBER = re.compile(r'(\d[\d,\s]*(?:\.\d+)?)\s*([kKmM]?)')
PROJECT_FOR_SCOPE = None
TOP_MAX, BOTTOM_MAX = 0.12, 0.20
CAPSULE = (0.72, 0.10)          # TikTok menu capsule: top-right corner stays free
# user 2026-10-23: the currency bar is always at the very top, never in the middle (prices/rewards on these pages are content)
CURRENCY_WORDS = r'coin|gem|diamond|gold|cash|money|pearl|currency|acorn|cand(y|ies)|energy|lightning|bolt|stamina'
CONTENT_PAGES = {'shop', 'skins', 'result_win', 'result_fail', 'checkin', 'league', 'reward', 'revive', 'trial', 'gift', 'offer'}


def value(s):
    m = NUMBER.search(s or '')
    if not m:
        return None
    v = float(re.sub(r'[,\s]', '', m.group(1)))
    return v * {'k': 1e3, 'm': 1e6}.get(m.group(2).lower(), 1)


def ends(path, decl):
    return path == decl or path.endswith('/' + decl)


def visible(n):
    return n.get('opacity', 1) > 0.05 and area(n['rect']) > 0


def mask_order(d):
    return max((n['order'] for n in d.get('nodes', []) if n['comps'].get('block_input') and visible(n) and area(n['rect']) >= 0.85),
               default=-1)


def energy_word(res):
    """A user-requested battery is allowed only with exact authorization and current art hashes."""
    override=res.get('energy_icon_override')
    if not override:return LIGHTNING
    try:
        from maintenance_scope import checked_ref
        if PROJECT_FOR_SCOPE is None or override.get('kind')!='battery':raise ValueError('explicit battery request required')
        auth=override['authorization'];source=checked_ref(auth,PROJECT_FOR_SCOPE)
        if not auth.get('excerpt') or auth['excerpt'] not in source.read_text() or '电池' not in auth['excerpt']:raise ValueError('battery request not in source')
        art=checked_ref(override['art'],PROJECT_FOR_SCOPE)
        if not art.is_relative_to(PROJECT_FOR_SCOPE/'assets'):raise ValueError('battery artwork outside project')
        return re.compile(re.escape(art.stem),re.I)
    except (ValueError,OSError,KeyError,TypeError):return LIGHTNING


def find(d, res):
    """(count node, container node, icon node) of a resource on this dump."""
    counts = res['count'] if isinstance(res.get('count'), list) else [res.get('count')]
    nodes = [n for n in d.get('nodes', []) if visible(n)]
    count = next((n for c in counts if c for n in nodes if ends(n['path'], c) and node_text(n)), None)
    if not count:
        return None, None, None
    box = next((n for n in nodes if res.get('node') and ends(n['path'], res['node'])), None)
    scope = box['path'] if box else count['path'].rsplit('/', 1)[0]
    word = energy_word(res) if res['kind'] == 'energy' else re.compile(re.escape(str(res.get('icon_frame') or res.get('icon') or '')), re.I)
    icon = next((n for n in nodes if (n['path'] + '/').startswith(scope + '/') and 'sprite' in n['comps'] and n is not box
                 and word.pattern and word.search(str(n['comps']['sprite'].get('frame', '')))), None)
    return count, box, icon


def declared(cfg, mode, add):
    res = cfg.get('resources') if isinstance(cfg.get('resources'), list) else []
    ok = cfg.get('schema') == 'top_bar.v1' and str(cfg.get('theme', '')).strip() and res
    if not ok:
        add('declared', False, 'docs/top-bar.json needs schema top_bar.v1, theme and resources (currency, progress, energy if any)')
        return []
    kinds = [r.get('kind') for r in res if isinstance(r, dict)]
    need = [k for k in ('currency', 'progress') if k not in kinds]
    bad = [r for r in res if not isinstance(r, dict) or r.get('kind') not in ('currency', 'energy', 'progress')
           or not str(r.get('name', '')).strip() or not str(r.get('icon', '')).strip() or not r.get('count')]
    add('declared', not need and not bad, 'resources: %s' % ', '.join('%s %s' % (r['kind'], r['name']) for r in res if isinstance(r, dict))
        if not need and not bad else 'missing %s; every resource needs kind, name, icon and count (node path)' % (need or 'nothing'))
    for r in res:
        if not isinstance(r, dict):
            continue
        if r.get('kind') == 'currency':
            generic = GENERIC_COIN.match(str(r.get('icon', '')).strip()) or GENERIC_COIN.match(str(r.get('name', '')).strip())
            ok = not generic or str(r.get('why', '')).strip()
            add('themed_currency', ok, '%s (%s) for a %s game' % (r.get('name'), r.get('icon'), cfg['theme']) if ok else
                'a plain coin for a %s game: name and draw the currency after the game world (ocean -> Pearls, candy -> Candies, '
                'space -> Star Gems, forest -> Acorns ...); if coins really fit (pirates, treasure, shop, or the original game\'s own '
                'currency in 英化) write "why"' % cfg['theme'])
        if r.get('kind') == 'energy':
            ok = bool(energy_word(r).search(str(r.get('icon', ''))))
            add('energy_lightning', ok, 'energy icon: %s' % r.get('icon') if ok else 'energy uses a lightning icon (found %r)' % r.get('icon'))
    return [r for r in res if isinstance(r, dict) and r.get('kind') in ('currency', 'energy', 'progress') and r.get('count')]


def on_pages(dumps, res, mode, add):
    pages = ['home'] + (['map'] if mode == 'levels' and __import__('maintenance_scope').required_map(PROJECT_FOR_SCOPE) else [])
    for purpose in pages:
        ds = [d for d in dumps if d.get('purpose') == purpose]
        if not ds:
            add('bar_on_' + purpose, False, 'no %s dump: read the %s page with chrome_touch dump_ui' % (purpose, purpose))
            continue
        problems = []
        for r in res:
            for d in ds:
                count, box, icon = find(d, r)
                where = '%s on %s' % (r['name'], d.get('screen'))
                if not count:
                    problems.append('%s: count %s not found or empty' % (where, r['count']))
                    continue
                if value(node_text(count)) is None:
                    problems.append('%s: "%s" has no number' % (where, node_text(count)))
                rect = (box or count).get('screen') or (box or count)['rect']
                if rect[1] > TOP_MAX or rect[1] + rect[3] > BOTTOM_MAX:
                    problems.append('%s: not at the top (top %.0f%%, bottom %.0f%% of the screen; needs <= 12%% / 20%%)'
                                    % (where, rect[1] * 100, (rect[1] + rect[3]) * 100))
                if rect[0] + rect[2] > CAPSULE[0] and rect[1] < CAPSULE[1]:
                    problems.append('%s: in the top-right corner where the platform menu capsule sits (keep x > 72%% free at the top)' % where)
                if not icon:
                    problems.append('%s: no icon sprite whose frame name has "%s" next to the number' %
                                    (where, 'lightning' if r['kind'] == 'energy' else r.get('icon_frame') or r['icon']))
                if mask_order(d) > count['order']:
                    problems.append('%s: under a popup mask' % where)
        add('bar_on_' + purpose, not problems, '%d resources at the top of %d %s dumps' % (len(res), len(ds), purpose)
            if not problems else '; '.join(problems[:6]))
    cur = [r for r in res if r['kind'] == 'currency']
    for purpose in ('shop', 'skins'):
        ds = [d for d in dumps if d.get('purpose') == purpose]
        if not ds or not cur:
            continue
        miss = [d.get('screen') for d in ds if not any((lambda c: c and mask_order(d) <= c['order'])(find(d, r)[0]) for r in cur)]
        add('currency_on_' + purpose, not miss, 'currency shown on the %s page' % purpose if not miss else
            'the %s page must show the currency count (top bar above the mask, or a count in the panel; add its path to "count"): %s'
            % (purpose, miss[:4]))


def currency_only_at_top(dumps, res, add):
    extra = [re.escape(str(r.get(k))) for r in res for k in ('icon', 'icon_frame', 'name')
             if r.get(k) and r.get('kind') in ('currency', 'energy')]
    words = re.compile('|'.join([CURRENCY_WORDS] + extra), re.I)
    problems, pages = [], 0
    for d in dumps:
        if d.get('purpose') in CONTENT_PAGES or d.get('kind') == 'gameplay':
            continue
        pages += 1
        mo = mask_order(d)
        nodes = [n for n in d.get('nodes', []) if visible(n)]
        icons = [n for n in nodes if 'sprite' in n['comps'] and not node_text(n)
                 and words.search(n['path'].rsplit('/', 1)[-1] + ' ' + str(n['comps']['sprite'].get('frame', '')))]
        for n in nodes:
            if value(node_text(n)) is None or (mo >= 0 and n['order'] > mo):
                continue
            r = n.get('screen') or n['rect']
            near = [i for i in icons if (lambda q: abs((q[1] + q[3] / 2) - (r[1] + r[3] / 2)) <= max(q[3], r[3])
                                         and abs((q[0] + q[2] / 2) - (r[0] + r[2] / 2)) <= 0.25)(i.get('screen') or i['rect'])]
            near.sort(key=lambda i: area(i['rect']))
            if near and (r[1] > TOP_MAX or r[1] + r[3] > BOTTOM_MAX):
                problems.append('%s: "%s" next to %s is at %.0f%% of the screen height' % (
                    d.get('screen'), node_text(n)[:12], near[0]['path'].rsplit('/', 1)[-1], (r[1] + r[3] / 2) * 100))
    if pages:
        add('currency_only_at_top', not problems, 'currency and energy only in the top band on %d pages' % pages if not problems else
            'currency must be at the very top of the screen, never in the middle (move the whole bar into the top resource '
            'bar): ' + '; '.join(problems[:5]))


def live(folders, res, mode, add):
    watch = [r for r in res if r['kind'] == 'currency'] + [r for r in res if r['kind'] == 'progress' and mode == 'levels']
    for r in watch:
        seen, drops = 0, []
        for folder in folders:
            for run in sorted({Path(d['_file']).parent for d in load_dumps([folder])}):
                ds = sorted(load_dumps([run]), key=lambda d: Path(d['_file']).name)
                for i, d in enumerate(ds):
                    if d.get('purpose') != 'result_win':
                        continue
                    before = [value(node_text(find(x, r)[0])) for x in ds[:i] if x.get('purpose') in ('home', 'map') and find(x, r)[0]]
                    after = [value(node_text(find(x, r)[0])) for x in ds[i + 1:] if x.get('purpose') in ('home', 'map') and find(x, r)[0]]
                    if before and after and before[-1] is not None and after[0] is not None:
                        seen += 1
                        if after[0] <= before[-1]:
                            drops.append('%s: %s before the win, %s after (%s)' % (run.name, before[-1], after[0], d.get('screen')))
        ok = seen and not drops
        add('live_' + r['kind'], ok, '%s went up after %d won levels' % (r['name'], seen) if ok else
            ('%s did not go up after a win: %s (update the bar the moment it changes)' % (r['name'], '; '.join(drops[:3])) if drops else
             'no home/map -> won level -> home/map sequence in one test run: dump the home or map page, win a level, dump '
             'home/map again so the %s update can be seen' % r['name']))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dumps', type=Path, nargs='*', help='folders with chrome_touch dump_ui files (default <project>/docs/test)')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    global PROJECT_FOR_SCOPE
    proj = a.project.resolve();PROJECT_FOR_SCOPE=proj
    if not (proj / 'assets').is_dir():
        ap.error('%s is not a Cocos project (no assets folder)' % proj)
    checks = []

    def add(cid, ok, detail):
        checks.append({'id': cid, 'passed': bool(ok), 'detail': detail})

    mode = plan_mode(proj)
    try:
        cfg = json.loads((proj / 'docs/top-bar.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        cfg = None
        add('declared', False, 'docs/top-bar.json missing: declare the top bar (theme, currency, progress, energy if any) '
            '— references/top-bar-and-level-map.md')
    if cfg is not None:
        res = declared(cfg if isinstance(cfg, dict) else {}, mode, add)
        if res:
            folders = [f for f in (a.dumps or [proj / 'docs/test']) if Path(f).is_dir()]
            dumps = load_dumps(folders)
            on_pages(dumps, res, mode, add)
            currency_only_at_top(dumps, res, add)
            live(folders, res, mode, add)
    failed = [c for c in checks if not c['passed']]
    report = {'tool': 'audit_top_bar', 'schema': 1, 'mode': mode, 'checks': checks, 'checked': len(checks), 'failed': len(failed),
              'passed': not failed and bool(checks), 'status': 'pass' if not failed and checks else 'fail',
              'boundary': 'Declared resources and dump_ui of the running game; the icon art and the count-up animation are judged '
                          'by Codex on the contact sheet and in the browser (HUD-01 observations).'}
    if a.binding:
        try:
            b = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError) as exc:
            ap.error('binding: %s' % exc)
        if not isinstance(b, dict):
            ap.error('no binding object in %s' % a.binding)
        report['binding'] = b
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'checked': len(checks), 'failed': len(failed),
                      'found': [{'id': c['id'], 'detail': c['detail'][:200]} for c in failed][:8], 'report': str(a.out)}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
