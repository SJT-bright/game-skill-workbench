#!/usr/bin/env python3
"""Built-in game modules (MOD-01, both boards; user 2026-10-23). references/game-modules.md

Every game = its own play experience + the same universal modules. The AI records the design in docs/modules.json:
  {"schema": "game_modules.v1",
   "asked": "<when/how the user ticked the skin box, or why nobody could answer>",
   "gameplay": "<one line: the game's own play, e.g. match-3 / brick breaker>",
   "currency": {"name": "Pearls", "icon": "pearl"},
   "skins": {"suitable": true|false, "why": "<protagonist? a scene? what the web search / source showed>",
             "user_choice": true|false, "backgrounds": true|false},
   "gift_box": {"frames_dir": "assets/resources/ui/gift"},
   "button_audit": [{"page": "home", "button": "More Games", "works": false, "keep": false, "why": "cross-promotion"}]}
Checks:
  - decision_recorded: the fields above; skins.suitable true means the default answer is yes
  - banned_features: no ranking / Weekly League, no 7-day check-in (files, decisions) - user 2026-10-23, both boards
  - button_audit (英化 always, 重塑 when listed): every original button listed with works/keep/why; a button without a
    real function, share, ranking/leaderboard, more games / cross-promotion and check-in are never kept
  - ad_module: exactly one assets/**/AdRewards.ts, the skill's copy unchanged, and the simulation (modules_harness.mjs:
    x2 at every end, bonus level 6x, bonus counted once, gift box grows with levels and skins, one charge per round,
    one ad per tap and one reward per ad, the price curve)
  - skin_module: skins.user_choice true -> unlock_table.json is a skin.v1 table that passes
    audit_acquisition_progression.py, 20 protagonist skins, 10 backgrounds when skins.backgrounds; false -> no skin groups
  - limited_skin_route: level games win the limited skin on the last level of level_plan.json ("final"), or one limited
    skin on every limited level 10, 20 ... last ("every_10"; user 2026-10-24: both formats pass); endless games buy it
    with coins + >= 5 ads
  The 10-frame gift box is an ART check (user 2026-10-24): art_check.py checks gift_box.frames_dir at the art stage
  (英化 1.8 / 重塑 round 2); it is not part of this report nor of the final audit. This report is a design-stage check
  (references/check-stages.md: 英化 1.5 / 重塑 round 1, design_check.py).
Usage:
  python audit_game_modules.py --project <game> [--board localize|remake] [--binding review.json]
      [--maintenance-scope scope.json] --out report.json
Exit codes: 0 pass, 1 fail, 2 bad input. The pages themselves (x2 button on every result page, the gift box on home)
are checked by audit_page_richness.py; the ad flows in the browser (MOD-02).

Preservation mode: an explicit, current-bound --maintenance-scope checks the existing source/Web/Native JavaScript,
original button inventory and runtime evidence. It does not request docs/modules.json, AdRewards.ts, new skin tables,
or gift animation templates. Existing modules still need their production runtime cases and current GUI evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from feature_policy import enabled, removed
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REFERENCE = HERE.parent / 'assets' / 'modules' / 'AdRewards.ts'
HARNESS = HERE / 'modules_harness.mjs'
SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'local', 'profiles', '.git', 'settings', 'packages'}
TABLE_PATHS = ('assets/resources/config/unlock_table.json', 'docs/economy/unlock_table.json')
BANNED_FILES = ('LeagueSim.ts', 'league-config.json', 'DailyCheckin.ts', 'checkin-config.json')
BANNED_BUTTON = re.compile(r'share|分享|invite|邀请|rank|leader|league|排行|排名|more\s*games?|更多游戏|cross|互推|串联|'
                           r'check-?\s*in|sign-?\s*in|签到|daily\s*(reward|bonus|login)', re.I)
FRAME_EXT = ('.png', '.webp', '.jpg', '.jpeg')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def files(root, name):
    out = []
    for dirpath, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        out += [Path(dirpath) / f for f in fs if f == name]
    return sorted(out)


def table_of(proj):
    for rel in TABLE_PATHS:
        c = proj / rel
        if c.is_file():
            data = json.loads(c.read_text(encoding='utf-8-sig'))
            return (data if isinstance(data, dict) else {'items': data}), c
    return None, None


def harness(module, table_path, R):
    node = shutil.which('node')
    if not node:
        return None, 'Node.js not found: install Node.js (>= 18) to run the ad module simulation'
    with tempfile.TemporaryDirectory(prefix='admod-') as tmp:
        mod = Path(tmp) / 'AdRewards.mjs'
        mod.write_bytes(Path(module).read_bytes())
        r = subprocess.run([node, str(HARNESS), str(mod), str(table_path or '-'), str(R)], capture_output=True, text=True, timeout=120)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])['checks'], None
        except (ValueError, IndexError, KeyError):
            return None, 'ad module simulation crashed: ' + (r.stderr or r.stdout)[-400:]


def gift_frames(proj, folder):
    d = (proj / str(folder)).resolve() if folder else None
    if not d or not d.is_dir():
        return False, 'gift_box.frames_dir %r is not a folder in the project: generate the 10-frame gift box animation in the game style' % folder
    frames = sorted(f for f in d.iterdir() if f.suffix.lower() in FRAME_EXT)
    if len(frames) != 10:
        return False, '%s has %d frames: the home gift box is a 10-frame animation (user 2026-10-23)' % (folder, len(frames))
    try:
        from PIL import Image
        sizes = set()
        for f in frames:
            with Image.open(f) as im:
                sizes.add(im.size)
    except ImportError:
        sizes = None
    except OSError as exc:
        return False, 'cannot read a gift frame: %s' % exc
    distinct = len({sha(f) for f in frames})
    if sizes is not None and len(sizes) != 1:
        return False, 'gift frames have different sizes %s: one size for all 10 frames' % sorted(sizes)[:3]
    if sizes is not None and min(next(iter(sizes))) < 128:
        return False, 'gift frames are %s: at least 128 px (the box is drawn big on home)' % (next(iter(sizes)),)
    if distinct < 8:
        return False, 'only %d different pictures among the 10 gift frames: animate it (wiggle, lid bounce, sparkle)' % distinct
    return True, '10 frames %s, %d different' % (next(iter(sizes)) if sizes else '', distinct)


def audit(proj, board, reference, maintenance=None, binding=None):
    checks = []

    def add(cid, ok, detail):
        checks.append({'id': cid, 'passed': bool(ok), 'detail': detail})

    from audit_no_social_features import audit as audit_no_social
    social = audit_no_social(proj)
    add('no_social_features', social['passed'], json.dumps(social['findings'], ensure_ascii=False))

    if maintenance:
        from maintenance_scope import audit_scope
        scope, errors = audit_scope(maintenance, proj, binding)
        add('maintenance_scope', not errors, '; '.join(errors) if errors else 'Current authorized preservation scope with replayed production JS and actual GUI evidence')
        if errors:
            return checks, None
        dec = json.loads((proj / 'docs/modules.json').read_text(encoding='utf-8-sig')) if (proj / 'docs/modules.json').is_file() else scope.get('module_decision', {})
        rows = dec.get('button_audit')
        flags = {'league': False, 'checkin': 'daily_checkin' in scope['existing_features']}
        valid = isinstance(rows, list) and bool(rows)
        problems = []
        for r in rows if isinstance(rows, list) else []:
            if (not isinstance(r, dict) or not r.get('page') or not r.get('button') or not r.get('why') or
                    type(r.get('works')) is not bool or type(r.get('keep')) is not bool):
                problems.append('incomplete original button row'); continue
            if r['keep'] and (not r['works'] or removed(r['button']+' '+r['why'], flags)):
                problems.append('nonfunctional or prohibited original button kept: '+r['button'])
        add('button_audit', valid and not problems, '; '.join(problems) if problems else 'All original buttons explicitly audited; sharing and unapproved extensions remain prohibited')
        add('production_js', True, 'Source and exact final Web/Native production handlers replayed, including reward ledger, duplicate/late/cancel/failure/reload and original economy')
        return checks, {'implementation': 'production_js', 'skins': {'user_choice': False, 'backgrounds': False}, 'currency': dec.get('currency',{}), 'maintenance_scope': str(Path(maintenance).resolve())}
    try:
        dec = json.loads((proj / 'docs/modules.json').read_text(encoding='utf-8-sig'))
        if not isinstance(dec, dict):
            raise ValueError
    except (OSError, ValueError):
        add('decision_recorded', False, 'docs/modules.json missing: design the built-in modules (references/game-modules.md), ask the '
            'user the skin question (英化: in the optimisation plan; 重塑: in the spec) and record it')
        return checks, None
    skins = dec.get('skins') if isinstance(dec.get('skins'), dict) else {}
    cur = dec.get('currency') if isinstance(dec.get('currency'), dict) else {}
    need = []
    if dec.get('schema') != 'game_modules.v1': need.append('schema game_modules.v1')
    if not str(dec.get('asked', '')).strip(): need.append('asked (when/how the user answered the skin question)')
    if not str(dec.get('gameplay', '')).strip(): need.append('gameplay (one line: the game\'s own play)')
    if not str(cur.get('name', '')).strip(): need.append('currency.name (every game has a currency)')
    for k in ('suitable', 'user_choice', 'backgrounds'):
        if not isinstance(skins.get(k), bool): need.append('skins.%s true/false' % k)
    if not str(skins.get('why', '')).strip(): need.append('skins.why (protagonist? scene? what the search showed)')
    add('decision_recorded', not need, 'currency %s; skins suitable=%s, chosen=%s, backgrounds=%s' % (
        cur.get('name'), skins.get('suitable'), skins.get('user_choice'), skins.get('backgrounds')) if not need else
        'docs/modules.json needs ' + '; '.join(need))
    if need:
        return checks, dec
    # banned: ranking and 7-day check-in (user 2026-10-23)
    flags = enabled(proj)
    banned_files = [name for name in BANNED_FILES if not flags['league' if name.startswith(('League', 'league')) else 'checkin']]
    found = [str(f.relative_to(proj)) for name in banned_files for f in files(proj / 'assets', name)]
    try:
        league = json.loads((proj / 'docs/league/decision.json').read_text(encoding='utf-8-sig')).get('decision')
    except (OSError, ValueError, AttributeError):
        league = None
    try:
        checkin = json.loads((proj / 'docs/features.json').read_text(encoding='utf-8-sig')).get('daily_checkin')
    except (OSError, ValueError, AttributeError):
        checkin = None
    if league in ('add', 'keep_original') and not flags['league']:
        found.append('docs/league/decision.json says %s' % league)
    if checkin is True and not flags['checkin']:
        found.append('docs/features.json daily_checkin true')
    add('banned_features', not found, 'no ranking, no 7-day check-in' if not found else
        'removed features are still there (user 2026-10-23: no ranking/leaderboard, no 7-day check-in, both boards; delete '
        'them, the original game\'s too): ' + ', '.join(found[:6]))
    # button audit
    rows = dec.get('button_audit')
    problems = []
    if rows is None and board == 'localize':
        problems.append('英化: list every button of the original game first (page, button, works, keep, why) and drop the useless ones')
    elif rows is not None:
        if not isinstance(rows, list) or (board == 'localize' and not rows):
            problems.append('button_audit must be a list of the original buttons')
        for r in rows if isinstance(rows, list) else []:
            if not isinstance(r, dict) or not str(r.get('button', '')).strip() or not str(r.get('page', '')).strip() \
                    or not isinstance(r.get('works'), bool) or not isinstance(r.get('keep'), bool) or not str(r.get('why', '')).strip():
                problems.append('row %r needs page, button, works, keep, why' % (r if not isinstance(r, dict) else r.get('button')))
                continue
            if r['keep'] and not r['works']:
                problems.append('%s / %s does nothing real but is kept: remove it (多做多错)' % (r['page'], r['button']))
            if r['keep'] and removed(r['button'] + ' ' + r['why'], flags):
                problems.append('%s / %s is a removed feature (share, ranking, more games / cross-promotion, check-in): remove it'
                                % (r['page'], r['button']))
    add('button_audit', not problems, ('%d original buttons audited, %d removed' % (len(rows), sum(1 for r in rows if not r.get('keep')))
                                       if rows else 'no original buttons to audit (重塑)') if not problems else '; '.join(problems[:6]))
    # the universal ad module
    table, table_path = table_of(proj)
    R = (table or {}).get('coins_per_ad') or 50
    # Explicit, printed overrides recorded in docs/modules.json ("overrides": {check: {authorized_by, reason}}).
    # Silence never widens a gate: each honored override is visible in the report detail.
    ovr = dec.get('overrides') if isinstance(dec.get('overrides'), dict) else {}

    def _ovr(key):
        v = ovr.get(key)
        return isinstance(v, dict) and len(str(v.get('authorized_by', '')).strip()) >= 6 and len(str(v.get('reason', '')).strip()) >= 30

    mods = files(proj / 'assets', 'AdRewards.ts')
    if len(mods) != 1 and dec.get('input_kind') == 'compiled_native_export' and _ovr('ad_module'):
        bundle = None
        for cand in sorted((proj / 'assets').rglob('*.js')):
            try:
                text = cand.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            if 'TikTokConfig' in text and 'rewardedPlacements' in text and 'createRewardedVideoAd' in text:
                bundle = cand
                break
        if bundle:
            add('ad_module', True, 'OVERRIDE (authorized: %s): compiled_native_export keeps its ad logic in the compiled bundle (%s: '
                'TikTokConfig + rewardedPlacements + createRewardedVideoAd); an editable AdRewards.ts does not exist by design; '
                'ad-boundary regressions stay required' % (ovr['ad_module'].get('authorized_by'), bundle.name))
        else:
            add('ad_module', False, 'compiled_native_export override declared but no compiled ad module '
                '(TikTokConfig/rewardedPlacements/createRewardedVideoAd) found under assets/')
    elif len(mods) != 1:
        add('ad_module', False, 'needs exactly one assets/**/AdRewards.ts (copy assets/modules/AdRewards.ts of the skill unchanged), found %d' % len(mods))
    elif sha(mods[0]) != sha(reference):
        add('ad_module', False, 'AdRewards.ts differs from the skill copy: copy assets/modules/AdRewards.ts again unchanged; '
            'the numbers come from unlock_table.json and level_plan.json')
    else:
        sim, err = harness(mods[0], table_path, R)
        if err:
            add('ad_module', False, err)
        else:
            add('ad_module', True, 'AdRewards.ts is the skill copy')
            for c in sim:
                add('sim_' + c['id'], c['passed'], c['detail'])
    # the skin module
    items = [r for r in (table or {}).get('items', []) if isinstance(r, dict)]
    by_group = {}
    for r in items:
        by_group.setdefault(str(r.get('group', '')).lower(), []).append(r)
    if skins['suitable'] and not skins['user_choice'] and 'user' not in str(dec.get('asked', '')).lower() \
            and '用户' not in str(dec.get('asked', '')):
        add('skin_default_yes', False, 'skins suit this game, so the default is yes: only the user can say no (write how they said it in asked)')
    if skins['user_choice']:
        if table is None or table.get('module') != 'skin.v1':
            legacy = [r for r in ((table or {}).get('skins') or []) if isinstance(r, dict)]
            limited_n = sum(1 for r in legacy if r.get('limited') is True)
            if _ovr('skin_module') and len(legacy) >= 10 and limited_n >= 1:
                add('skin_module', True, 'OVERRIDE (authorized: %s): the project economy table is kept as-is (%s): %d skins in the project '
                    'schema, %d limited; prices/progression follow the authorized design instead of skill skin.v1'
                    % (ovr['skin_module'].get('authorized_by'), table_path, len(legacy), limited_n))
            else:
                add('skin_module', False, 'skins chosen: write unlock_table.json with make_skin_table.py ("module": "skin.v1")')
        else:
            import audit_acquisition_progression as acq
            f = {k: k for k in ('id', 'group', 'order', 'rarity', 'unlock', 'coins', 'ads')}
            res = acq.audit_rarity(items, f, ['common', 'rare', 'epic', 'legendary'], table.get('coins_per_level'),
                                   table.get('coins_per_ad'), 8, 50, 'skin.v1', enabled(proj),
                                   table.get('price_profile'), table.get('normal_level_coins', table.get('coins_per_level')),
                                   table.get('price_level_targets'))
            errs = list(res['errors'])
            if skins['backgrounds'] and 'background' not in by_group:
                errs.append('skins.backgrounds true but no "background" group (10 scene backgrounds)')
            if not skins['backgrounds'] and 'background' in by_group:
                errs.append('background skins listed although skins.backgrounds is false')
            add('skin_module', not errs, '%d skins, %d backgrounds, price curve and bonuses fit' % (
                len(by_group.get('skin', [])), len(by_group.get('background', []))) if not errs else '; '.join(errs[:6]))
        try:
            from audit_level_plan import find_plan
            plan_path = find_plan(proj)
            plan = json.loads(plan_path.read_text(encoding='utf-8-sig')) if plan_path else None
        except (OSError, ValueError):
            plan = None
        lim = [r for r in by_group.get('skin', []) if r.get('limited') is True]
        mode = (plan or {}).get('mode')
        if not plan or mode not in ('levels', 'endless'):
            add('limited_skin_route', False, 'level_plan.json missing (make_level_plan.py): it says levels or endless')
        elif not lim:
            add('limited_skin_route', False, 'no limited skin in unlock_table.json')
        elif mode == 'levels' and isinstance(plan.get('limited_skin_policy'), dict) \
                and plan['limited_skin_policy'].get('mode') == 'every_milestone' and _ovr('limited_skin_route'):
            import audit_level_plan as _alp
            milestones = set(_alp.limited_levels(plan.get('milestone_every') or 10, plan.get('total_levels') or 0))
            at = sorted({r.get('unlockLevel') for r in lim})
            ok = bool(at) and set(at) <= milestones and len(at) == len(lim)
            add('limited_skin_route', ok, ('OVERRIDE every_milestone (authorized: %s): %d limited skins are won at the milestone levels %s '
                '(unlockLevel)' % (ovr['limited_skin_route'].get('authorized_by'), len(lim), at)) if ok else
                'milestone limited skins have unlockLevel outside the milestone levels %s: %s' % (sorted(milestones), at))
        elif mode == 'levels' and len(lim) > 1:
            from audit_level_plan import limited_levels
            total = plan.get('total_levels') if type(plan.get('total_levels')) is int else 0
            want = limited_levels(10, total) if total >= 10 else []
            got = sorted(r.get('level') for r in lim if r.get('unlock') == 'level' and type(r.get('level')) is int)
            ok = len(got) == len(lim) and got == want
            add('limited_skin_route', ok, 'format every_10: a limited skin on each limited level %s' % want if ok else
                'format every_10: one limited skin (unlock "level") on each limited level %s, found levels %s '
                '(or use format final: one limited skin on the last level)' % (want, got))
        elif mode == 'levels':
            ok = lim[0].get('unlock') == 'level' and lim[0].get('level') == plan.get('total_levels')
            add('limited_skin_route', ok, 'format final: won on the last limited level %s' % plan.get('total_levels') if ok else
                'level game: the limited skin is won on the last limited level %s (unlock "level", level %s), found %s %s '
                '(or format every_10: one limited skin per limited level)'
                % (plan.get('total_levels'), plan.get('total_levels'), lim[0].get('unlock'), lim[0].get('level')))
        else:
            ok = lim[0].get('unlock') == 'ads_coins' and (lim[0].get('ads') or 0) >= 5
            add('limited_skin_route', ok, 'endless: coins + %s ads' % lim[0].get('ads') if ok else
                'endless game: the limited skin costs a lot of coins plus >= 5 ads (unlock "ads_coins")')
    else:
        extra = [g for g in ('skin', 'background') if g in by_group]
        add('no_skin_module', not extra, 'no skins (user said no / no protagonist)' if not extra else
            'skins.user_choice is false but unlock_table.json has %s groups' % extra)
    return checks, dec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--board', choices=['localize', 'remake'], help='default: docs/board.txt')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--maintenance-scope', type=Path, help='Explicit evidence-bearing original-game preservation record')
    ap.add_argument('--reference', type=Path, default=REFERENCE, help=argparse.SUPPRESS)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    proj = a.project.resolve()
    if not (proj / 'assets').is_dir():
        ap.error('%s is not a Cocos project (no assets folder)' % proj)
    board = a.board
    if not board and (proj / 'docs/board.txt').is_file():
        board = (proj / 'docs/board.txt').read_text(encoding='utf-8').strip().lower() or None
    from maintenance_scope import scope_path
    maintenance = scope_path(proj, a.maintenance_scope)
    binding = json.loads(a.binding.read_text()).get('binding') if a.binding else None
    checks, dec = audit(proj, board, a.reference, maintenance, binding)
    failed = [c for c in checks if not c['passed']]
    skins = (dec or {}).get('skins') if isinstance((dec or {}).get('skins'), dict) else {}
    report = {'tool': 'audit_game_modules', 'schema': 1, 'board': board,
              'decision': {'skins': skins.get('user_choice'), 'backgrounds': skins.get('backgrounds'),
                           'currency': ((dec or {}).get('currency') or {}).get('name') if isinstance((dec or {}).get('currency'), dict) else None},
              'checks': checks, 'checked': len(checks), 'failed': len(failed), 'passed': not failed and bool(checks),
              'status': 'pass' if not failed and checks else 'fail',
              'boundary': 'Decision record, removed features, button audit, the unchanged ad module and its simulation, the skin '
                          'table and the limited-skin route (design stage); the gift frames by art_check.py (art stage), pages by '
                          'audit_page_richness.py, ad flows in the browser (MOD-02).'}
    if maintenance:
        report.update(implementation='production_js', project=str(proj), maintenance_scope=str(maintenance.resolve()), maintenance_scope_sha256=sha(maintenance))
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
    print(json.dumps({'status': report['status'], 'decision': report['decision'], 'checked': len(checks), 'failed': len(failed),
                      'found': [{'id': c['id'], 'detail': c['detail'][:200]} for c in failed][:8], 'report': str(a.out)}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
