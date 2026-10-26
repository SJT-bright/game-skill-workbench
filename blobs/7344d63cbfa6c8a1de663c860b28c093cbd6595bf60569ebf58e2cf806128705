"""Evidence-derived, criterion-level applicability for source maintenance reviews.

This module only filters named template additions. It never waives an entire
catalog row or any preserved-gameplay, reward, English/UI, storage, or loading
contract. Missing, stale, contradictory, or unbound documents fail closed.
"""
from pathlib import Path
import json

from maintenance_scope import checked_ref, audit_scope

SCHEMA = 'maintenance_criteria_scope.v1'
AVAILABLE_CHECK_DOMAINS = {'LOAD-01', 'LOAD-03', 'STORAGE-01', 'BUSINESS', 'PAGES',
                           'NORMAL', 'AUDIO', 'VISUAL', 'COVERAGE', 'SCOPE', 'ENGLISH'}
REQUIRED_DOCS = {
    'features': 'docs/features.json',
    'level_plan': 'docs/levels/level_plan.json',
    'league_decision': 'docs/league/decision.json',
}

# Each criterion is deliberately narrower than its catalog row. A row may
# contain both a scoped template addition and preserved mechanics that remain
# mandatory in the source-maintenance review.
ALWAYS_REQUIRED = {
    'AD-01.existing_ad_entry_inventory': ('BUSINESS', 'SCOPE'),
    'AD-02.existing_ad_completion_once': ('BUSINESS',),
    'CLAIM-01.existing_reward_claim_and_persistence': ('BUSINESS',),
    'CORE-01.original_match_and_round_flow': ('BUSINESS', 'NORMAL'),
    'UI-01.player_visible_english_and_no_share': ('ENGLISH', 'PAGES', 'SCOPE'),
    'STORAGE-01.current_native_storage_contract': ('STORAGE-01',),
    'LOAD-01.current_loading_and_recovery': ('LOAD-01', 'LOAD-03'),
    'MOD-01.original_buttons_and_currency': ('SCOPE', 'BUSINESS'),
    'MOD-01.share_and_promotion_removal': ('SCOPE', 'PAGES'),
    'MOD-02.original_reward_behavior_and_no_stall': ('BUSINESS', 'NORMAL'),
    'ECON-01.original_collection_and_prices': ('BUSINESS',),
    'ECON-02.original_trial_behavior': ('BUSINESS',),
    'FEAT-00.explicit_optional_feature_decisions': ('SCOPE',),
}



def _json_ref(record, base, expected_path):
    p = checked_ref(record, base)
    if p.resolve() != expected_path.resolve():
        raise ValueError('criteria-scope evidence must reference ' + str(expected_path))
    try:
        data = json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise ValueError('invalid criteria-scope input ' + str(p) + ': ' + str(exc))
    return p, data


def derive_criteria(features, level, league, scope, refs, route_labels, binding):
    """Derive narrow applicability from validated documents and scope."""
    existing = set(scope.get('existing_features', []))
    criteria = []
    def required(cid, checks, reason):
        criteria.append({'id': cid, 'disposition': 'required', 'checks': list(checks), 'basis': reason})
    def excluded(cid, reason, evidence):
        criteria.append({'id': cid, 'disposition': 'scoped_out', 'checks': [], 'basis': reason, 'evidence': [dict(x) for x in evidence]})

    for cid, checks in ALWAYS_REQUIRED.items():
        required(cid, checks, 'Preserved-gameplay acceptance; never removed by template applicability.')
    if features['daily_checkin']:
        required('FEAT-02.original_seven_day_signin', ('BUSINESS', 'PAGES'), 'Existing daily check-in is explicitly preserved and remains testable.')
    if 'collection' in existing:
        required('FEAT-01.original_collection_navigation_and_equip', ('BUSINESS', 'PAGES'), 'Existing collection remains required; only new skin bonuses may be scoped out.')
    if 'hero_trial' in existing:
        required('ECON-02.original_hero_trial_and_restore', ('BUSINESS', 'PAGES'), 'Existing hero trial remains required; only new map unlock flow may be scoped out.')
    if not features['skin_bonus']:
        for cid in ('MOD-01.add_skin_v1_module', 'ECON-01.add_skin_v1_bonus_values', 'FEAT-01.add_skin_v1_catalog_and_bonus'):
            excluded(cid, 'Current features evidence says skin_bonus=false; original game scope is validated.', [refs['features'], refs['maintenance_scope']])
    else:
        required('ECON-01.authorized_skin_bonus_progression', ('ECON-01', 'FEAT-01'), 'Current features evidence opts into skin bonuses.')
    if level['mode'] == 'endless':
        required('LEVEL-01.original_endless_mode_decision', ('SCOPE', 'NORMAL'), 'Endless-mode decision and actual current game flow remain in scope.')
        required('LEVEL-02.current_route_inventory_and_no_map', ('SCOPE', 'PAGES'), 'Source inventory and two-ratio route evidence remain required.')
        for cid in ('MOD-01.add_fixed_70_level_map', 'LEVEL-01.add_fixed_70_map_and_chapters', 'LEVEL-02.add_map_bonus_and_limited_level_flow', 'ECON-02.add_template_map_unlock_flow'):
            excluded(cid, 'Current level plan says endless; actual route presence/absence checks remain required.', [refs['level_plan'], refs['maintenance_scope']])
    else:
        required('LEVEL-01.authorized_fixed_level_plan', ('LEVEL-01',), 'Current level plan declares fixed levels.')
        required('LEVEL-02.authorized_level_map_behavior', ('LEVEL-02', 'PAGES'), 'Current level plan declares fixed levels.')
    if league['decision'] == 'none':
        if 'weekly_league' in existing or 'weekly league' in route_labels or 'leaderboard' in route_labels:
            raise ValueError('league decision none conflicts with current feature or UI-route inventory')
        required('RANK-01.explicit_no_weekly_league_decision', ('SCOPE',), 'No-weekly-league decision remains reviewable.')
        required('RANK-02.original_in_match_rank_behavior', ('BUSINESS', 'NORMAL'), 'Original in-match/result rank remains core behavior.')
        excluded('RANK-01.add_weekly_league_system', 'Current league decision is none.', [refs['league_decision'], refs['maintenance_scope']])
        excluded('RANK-02.add_weekly_league_behavior', 'Only weekly league is excluded; original in-match rank remains required.', [refs['league_decision'], refs['maintenance_scope']])
    else:
        required('RANK-01.authorized_weekly_league_decision', ('RANK-01',), 'Weekly league is explicitly selected or retained.')
        required('RANK-02.authorized_weekly_league_behavior', ('RANK-02',), 'Weekly league is explicitly selected or retained.')
    if features['daily_checkin'] and 'daily_checkin' in existing:
        excluded('FEAT-00.replace_original_signin_with_DailyCheckin_ts', 'Preserve the existing check-in; do not replace it with a template module.', [refs['features'], refs['maintenance_scope']])
    if scope.get('new_modules_requested') is False:
        for cid in ('MOD-01.add_ad_rewards_x2_template', 'MOD-01.add_home_gift_box_module', 'MOD-02.add_new_settlement_x2_reward', 'MOD-02.add_new_home_gift_box_flow'):
            excluded(cid, 'Preserve-existing-gameplay scope disallows a new module; existing ad/reward behavior remains required.', [refs['maintenance_scope']])
    else:
        required('MOD-01.authorized_new_reward_modules', ('MOD-01', 'MOD-02'), 'New modules are explicitly authorized and must be tested.')

    required_ids = {x['id'] for x in criteria if x['disposition'] == 'required'}
    excluded_ids = {x['id'] for x in criteria if x['disposition'] == 'scoped_out'}
    if len(required_ids) + len(excluded_ids) != len(criteria):
        raise ValueError('duplicate maintenance criterion ID')
    core_ids = set(ALWAYS_REQUIRED)
    if not core_ids <= required_ids:
        raise ValueError('attempted to scope out a mandatory preserved-game criterion')
    return {'schema': SCHEMA, 'binding': binding, 'required_criteria': sorted(required_ids), 'scoped_out_criteria': sorted(excluded_ids), 'criteria': criteria,
            'boundary': 'Only named template additions are filtered. Existing gameplay, rewards, ads, UI/English, storage, loading and no-share checks remain required.'}


def validate_supported_criteria(report):
    """Fail closed when an applicable criterion lacks an enforced check domain."""
    for row in report.get('criteria', []):
        unsupported = set(row.get('checks', [])) - AVAILABLE_CHECK_DOMAINS
        if row.get('disposition') == 'required' and unsupported:
            raise ValueError('applicable criterion has no enforced source-maintenance check domain: '
                             + row['id'] + ' (' + ', '.join(sorted(unsupported)) + ')')


def evaluate(record, project, binding, base):
    """Validate current evidence and return criterion dispositions; no row-level waiver."""
    project, base = Path(project).resolve(), Path(base).resolve()
    if not isinstance(record, dict) or record.get('schema') != SCHEMA:
        raise ValueError('source-maintenance criteria_scope must use ' + SCHEMA)
    if record.get('binding') != binding:
        raise ValueError('criteria_scope binding is missing or stale')
    inputs = record.get('inputs')
    if not isinstance(inputs, dict):
        raise ValueError('criteria_scope current input references are required')
    docs, refs = {}, {}
    for key, rel in REQUIRED_DOCS.items():
        path = project / rel
        if not path.is_file():
            raise ValueError('required current decision document missing: ' + str(path))
        p, data = _json_ref(inputs.get(key), base, path)
        docs[key] = data
        refs[key] = {'path': str(p), 'sha256': inputs[key]['sha256']}
    features, level, league = docs['features'], docs['level_plan'], docs['league_decision']
    if features.get('schema') != 'optional_features.v1' or type(features.get('skin_bonus')) is not bool or type(features.get('daily_checkin')) is not bool or not str(features.get('asked', '')).strip():
        raise ValueError('features decision must bind skin_bonus and daily_checkin booleans and explicit user decision')
    if level.get('schema') != 'level_plan.v1' or level.get('mode') not in ('endless', 'levels'):
        raise ValueError('level plan must declare endless or levels mode')
    if league.get('schema') != 'league_decision.v1' or league.get('decision') not in ('none', 'add', 'keep_original'):
        raise ValueError('league decision must declare none/add/keep_original')
    scope_ref = inputs.get('maintenance_scope')
    scope_file = checked_ref(scope_ref, base)
    if not scope_file.resolve().is_relative_to(project):
        raise ValueError('maintenance scope must be inside this project')
    scope, errors = audit_scope(scope_file, project, binding)
    if errors or scope is None:
        raise ValueError('current maintenance scope invalid: ' + '; '.join(errors))
    refs['maintenance_scope'] = {'path': str(scope_file), 'sha256': scope_ref['sha256']}
    existing = set(scope.get('existing_features', []))
    if features['daily_checkin'] != ('daily_checkin' in existing):
        raise ValueError('features.daily_checkin conflicts with validated original-feature inventory')
    if features['skin_bonus'] and 'skin_bonus' not in existing and scope.get('new_modules_requested') is False:
        raise ValueError('skin_bonus=true is not represented in validated original-feature inventory')
    inventory_ref = scope.get('source_inventory')
    inventory_file = checked_ref(inventory_ref, scope_file.parent)
    inventory = json.loads(inventory_file.read_text(encoding='utf-8-sig'))
    ui_file = checked_ref(inventory.get('ui_route_inventory'), inventory_file.parent)
    ui = json.loads(ui_file.read_text(encoding='utf-8-sig'))
    route_labels = ' '.join(str(x.get('id', '')) for x in ui.get('routes', []) if isinstance(x, dict)).lower()
    report = derive_criteria(features, level, league, scope, refs, route_labels, binding)
    validate_supported_criteria(report)
    checks = record.get('checks')
    required_ids, excluded_ids = set(report['required_criteria']), set(report['scoped_out_criteria'])
    if not isinstance(checks, dict) or set(checks) != required_ids | excluded_ids:
        raise ValueError('criteria_scope matrix has missing or unknown criterion IDs')
    for row in report['criteria']:
        observed = checks[row['id']]
        if not isinstance(observed, dict) or observed.get('disposition') != row['disposition']:
            raise ValueError('criteria_scope disposition mismatch: ' + row['id'])
        if row['disposition'] == 'required':
            if observed.get('status') != 'pass' or not str(observed.get('observed', '')).strip():
                raise ValueError('required criterion not passed with observation: ' + row['id'])
            if not set(row['checks']) <= set(observed.get('backing_check_ids', [])):
                raise ValueError('required criterion missing backing check IDs: ' + row['id'])
        elif observed.get('status') != 'not_applicable' or not str(observed.get('observed', '')).strip():
            raise ValueError('scoped-out criterion needs explicit reason: ' + row['id'])
    report['inputs'] = refs
    return report
