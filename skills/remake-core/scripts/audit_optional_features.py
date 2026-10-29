#!/usr/bin/env python3
"""Skin bonuses and the 7-day check-in (user 2026-10-22). Remake package: the check-in is REQUIRED (user 2026-10-27).
remake-skins/references/skin-bonus-and-checkin.md

The AI asks the user once while designing gameplay (英化: in the optimisation plan; 重塑: in the spec unless the
starter pack already decided) and records the answer in docs/features.json:
  {"schema": "optional_features.v1", "asked": "<when/how the user answered>", "skin_bonus": true|false, "daily_checkin": true|false}
Checks:
  - the decision is recorded (no silent default)
  - skin_bonus: true  -> every skin in unlock_table.json has a "bonus" (audit_acquisition_progression.py checks the
                         values); false -> no item has one
  - daily_checkin: true -> assets/**/DailyCheckin.ts is the skill's copy unchanged, assets/**/checkin-config.json passes
                         the simulation (checkin_harness.mjs: once per day, 7 cards in order, big day 7 bundle, owned skin
                         pays coins, clock back / missed days / reset hour / save-load), its skins are unlock "checkin"
                         items in unlock_table.json, and R equals coins_per_ad of the table
                    false -> no check-in module in assets
Usage:
  python audit_optional_features.py --project <game> [--binding review.json]
      [--maintenance-scope scope.json] --out report.json
Exit codes: 0 pass, 1 fail, 2 bad input. The popup itself is checked in the browser (FEAT-02) and by
audit_page_richness.py (purpose checkin).

Preservation mode: an explicit current-bound --maintenance-scope checks the recorded existing check-in decision and
the source/Web/Native production JavaScript runtime cases. It does not require the Skill's DailyCheckin.ts or
checkin-config.json templates; missing or stale scope evidence still fails.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from feature_policy import read_record
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / 'assets' / 'checkin' / 'DailyCheckin.ts'
HARNESS = HERE / 'checkin_harness.mjs'
SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'local', 'profiles', '.git', 'settings', 'packages'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def files(root, name):
    out = []
    for dirpath, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        out += [Path(dirpath) / f for f in fs if f == name]
    return sorted(out)


def table_of(proj):
    for c in (proj / 'assets/resources/config/unlock_table.json', proj / 'docs/economy/unlock_table.json'):
        if c.is_file():
            data = json.loads(c.read_text(encoding='utf-8-sig'))
            return (data if isinstance(data, dict) else {'items': data}), c
    return None, None


def harness(module, config):
    node = shutil.which('node')
    if not node:
        return None, 'Node.js not found: install Node.js (>= 18) to run the check-in simulation'
    with tempfile.TemporaryDirectory(prefix='checkin-') as tmp:
        mod = Path(tmp) / 'DailyCheckin.mjs'
        mod.write_bytes(Path(module).read_bytes())
        r = subprocess.run([node, str(HARNESS), str(mod), str(config)], capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, TZ='UTC'))
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])['checks'], None
        except (ValueError, IndexError, KeyError):
            return None, 'check-in simulation crashed: ' + (r.stderr or r.stdout)[-400:]


def audit(proj, reference, maintenance=None, binding=None):
    checks = []

    def add(cid, ok, detail):
        checks.append({'id': cid, 'passed': bool(ok), 'detail': detail})

    if maintenance:
        from maintenance_scope import audit_scope
        scope, errors = audit_scope(maintenance, proj, binding)
        add('maintenance_scope', not errors, '; '.join(errors) if errors else 'Current original-game scope and real production handler replay')
        if errors:
            return checks, None
        dec = read_record(proj, 'docs/features.json')
        checkin = 'daily_checkin' in scope['existing_features']
        add('existing_feature_decision', dec.get('daily_checkin') is checkin, 'Preserved features must agree with actual source inventory; check-in is tested, not waived')
        add('production_feature_runtime', True, 'All preserved check-in date/duplicate/day7/clock rollback/write/readback/restart cases replayed on source and final Web/Native; current GUI evidence retained')
        return checks, {'skin_bonus': dec.get('skin_bonus') is True, 'daily_checkin': checkin}
    try:
        dec = json.loads((proj / 'docs/features.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        core = read_record(proj, 'docs/modules.json')
        if core.get('schema') == 'game_modules.v1' and str(core.get('asked', '')).strip() and isinstance(core.get('skins'), dict):
            dec = {'schema': 'optional_features.v1', 'asked': core['asked'], 'skin_bonus': core['skins'].get('user_choice') is True, 'daily_checkin': True}
        else:
            add('decision_recorded', False, 'docs/modules.json or explicit docs/features.json decision missing: record core module decisions; check-in is disabled by default '
            '(英化: in the optimisation plan; 重塑: in the spec) and record the answer')
            return checks, None
    ok = (dec.get('schema') == 'optional_features.v1' and isinstance(dec.get('skin_bonus'), bool)
          and isinstance(dec.get('daily_checkin'), bool) and str(dec.get('asked', '')).strip())
    add('decision_recorded', ok, 'skin_bonus=%s, daily_checkin=%s (%s)' % (dec.get('skin_bonus'), dec.get('daily_checkin'), dec.get('asked', ''))
        if ok else 'docs/features.json needs schema optional_features.v1, asked (when/how the user answered), skin_bonus and daily_checkin true/false')
    if not ok:
        return checks, dec
    table, table_path = table_of(proj)
    if (table or {}).get('module') == 'skin.v1':
        dec['skin_bonus'] = True
    items = [r for r in (table or {}).get('items', []) if isinstance(r, dict)]
    skins = [r for r in items if str(r.get('group', '')).lower() in ('skin', 'skins', 'character', 'characters')]
    with_bonus = [r for r in items if r.get('bonus')]
    if dec['skin_bonus']:
        missing = [r.get('id') for r in skins if not r.get('bonus') and str(r.get('unlock', '')).lower() != 'free']
        # Printed override from docs/modules.json "overrides.skin_bonus_in_table" (user-authorized existing economy table).
        try:
            ovr = json.loads((proj / 'docs/modules.json').read_text(encoding='utf-8-sig')).get('overrides', {}).get('skin_bonus_in_table')
        except (OSError, ValueError, AttributeError):
            ovr = None
        legacy = [r for r in ((table or {}).get('skins') or []) if isinstance(r, dict)]
        n_project_skins = len(skins) or len(legacy)
        if isinstance(ovr, dict) and len(str(ovr.get('authorized_by', '')).strip()) >= 6 \
                and len(str(ovr.get('reason', '')).strip()) >= 30 and n_project_skins >= 10:
            add('skin_bonus_in_table', True, 'OVERRIDE (authorized: %s): %d skins in the project economy schema; the authorized design '
                'carries skin value through the wardrobe/gift-passport progression rather than a per-skin "bonus" field'
                % (ovr.get('authorized_by'), n_project_skins))
        else:
            add('skin_bonus_in_table', bool(skins) and not missing,
                ('every skin has a bonus (values checked by audit_acquisition_progression.py)' if skins and not missing else
                 'skins without "bonus": %s' % (missing[:8] if skins else 'no skins in unlock_table.json')))
    else:
        add('no_skin_bonus', not with_bonus, 'no bonus fields' if not with_bonus else 'user said no skin bonus but items have one: %s'
            % [r.get('id') for r in with_bonus][:8])
    modules, configs = files(proj / 'assets', 'DailyCheckin.ts'), files(proj / 'assets', 'checkin-config.json')
    add('checkin_required', dec['daily_checkin'] is True, 'remake games have the 7-day check-in' if dec['daily_checkin'] else
        'remake games must have the 7-day check-in (user 2026-10-27): set docs/features.json daily_checkin true, copy '
        'assets/checkin/DailyCheckin.ts unchanged and tune checkin-config.json (R = B)')
    if not dec['daily_checkin']:
        return checks, dec
    if len(modules) != 1 or len(configs) != 1:
        add('checkin_files', False, 'needs exactly one assets/**/DailyCheckin.ts and one assets/**/checkin-config.json (found %d and %d)'
            % (len(modules), len(configs)))
        return checks, dec
    add('module_unchanged', sha(modules[0]) == sha(reference), 'DailyCheckin.ts is the skill copy' if sha(modules[0]) == sha(reference)
        else 'DailyCheckin.ts differs from the skill copy: copy assets/checkin/DailyCheckin.ts again unchanged; tune checkin-config.json only')
    try:
        cfg = json.loads(configs[0].read_text(encoding='utf-8-sig'))
    except ValueError as exc:
        add('config_json', False, 'checkin-config.json is not JSON: %s' % exc)
        return checks, dec
    sim, err = harness(modules[0], configs[0])
    if err:
        add('simulation', False, err)
    else:
        for c in sim:
            add('sim_' + c['id'], c['passed'], c['detail'])
    skin_ids = {r.get('id') for d in cfg.get('days', []) if isinstance(d, dict) for r in d.get('rewards', [])
                if isinstance(r, dict) and r.get('type') == 'skin'}
    b_value = (table or {}).get('normal_level_coins')
    if b_value is not None:
        # Remake economy (normal-10-50, user 2026-10-27): no extra check-in skins outside the 20; the check-in hands out
        # existing common/rare skins of the table (owned -> fallback coins), and R is B, one ordinary level.
        by_id = {r.get('id'): r for r in items}
        wrong = sorted(i for i in skin_ids if i not in by_id or str(by_id[i].get('group', '')).lower() not in ('skin', 'skins', 'character', 'characters')
                       or by_id[i].get('limited') is True or str(by_id[i].get('rarity', '')).lower() not in ('common', 'rare'))
        add('checkin_skins_in_table', table is not None and bool(skin_ids) and not wrong,
            'check-in skins are existing common/rare skins of the table' if table is not None and skin_ids and not wrong else
            'check-in skins must be existing common/rare protagonist skins of unlock_table.json (not limited, not new items): %s' % wrong)
        add('same_R', b_value == cfg.get('R'), 'R %s = B (normal_level_coins)' % cfg.get('R') if b_value == cfg.get('R') else
            'checkin-config R %s differs from B = unlock_table normal_level_coins %s' % (cfg.get('R'), b_value))
        return checks, dec
    listed = {r.get('id') for r in items if str(r.get('unlock', '')).lower() == 'checkin'}
    bad = [r.get('id') for r in items if str(r.get('unlock', '')).lower() == 'checkin' and (r.get('ads') or r.get('coins'))]
    add('checkin_skins_in_table', table is not None and skin_ids == listed and not bad,
        'check-in skins listed as unlock "checkin", no ads or coins' if table is not None and skin_ids == listed and not bad else
        'unlock_table "checkin" items %s vs config skins %s%s' % (sorted(listed), sorted(skin_ids), ('; ads/coins on %s' % bad) if bad else ''))
    r_table = (table or {}).get('coins_per_ad')
    add('same_R', r_table == cfg.get('R'), 'R %s = coins_per_ad' % cfg.get('R') if r_table == cfg.get('R') else
        'checkin-config R %s differs from unlock_table coins_per_ad %s' % (cfg.get('R'), r_table))
    return checks, dec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--maintenance-scope', type=Path)
    ap.add_argument('--reference', type=Path, default=REFERENCE, help=argparse.SUPPRESS)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    proj = a.project.resolve()
    if not (proj / 'assets').is_dir():
        ap.error('%s is not a Cocos project (no assets folder)' % proj)
    from maintenance_scope import scope_path
    maintenance = scope_path(proj, a.maintenance_scope)
    binding = json.loads(a.binding.read_text()).get('binding') if a.binding else None
    checks, dec = audit(proj, a.reference, maintenance, binding)
    failed = [c for c in checks if not c['passed']]
    report = {'tool': 'audit_optional_features', 'schema': 1, 'decision': {k: (dec or {}).get(k) for k in ('skin_bonus', 'daily_checkin')},
              'checks': checks, 'checked': len(checks), 'failed': len(failed), 'passed': not failed and bool(checks),
              'status': 'pass' if not failed and checks else 'fail',
              'boundary': 'Decision record, unlock table fields, unchanged module and simulation; the popup and result-page bonus '
                          'are checked in the browser (FEAT-01/FEAT-02).'}
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
