#!/usr/bin/env python3
"""Portable stdlib engineering fixtures; no game, model, engine or supplied script is executed."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import workshop_intake as wi


def put(root, rel, value):
    path = root / rel; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    return path


def read(root, rel):
    return json.loads((root / rel).read_text())


def digest(root, rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()


def ref(root, rel):
    return {'path': rel, 'sha256': digest(root, rel)}


def fixture(root, base):
    root.mkdir(); (base / 'assets/modules').mkdir(parents=True)
    put(base, 'assets/modules/AdRewards.ts', '// Synthetic exact module identity; never executed.\nexport const VERSION = 2;\n')
    for rel in wi.REQUIRED_FILES:
        put(root, rel, {} if rel.endswith('.json') else 'Synthetic engineering input; no engine execution.\n')
    for rel in ['GAME_DESIGN.md', 'UI_PAGES.md', 'ART_DIRECTION.md', 'AUDIO.md', 'COPY_EN.md']:
        put(root, rel, '# Synthetic English specification\n')
    prop = {'id': 'hint', 'grant_key': 'starter_v1_hint', 'unlock_level': 1, 'effect': 'Reveal a useful move.', **wi.PROP_POLICY}
    c = {'profile': wi.PROFILE, 'target_spec_sha256': 'a' * 64, 'approach': 'new_build', 'implementation': {'spec': 'implementation/BEHAVIOR.json', 'experience_spec': 'implementation/EXPERIENCE.json', 'creator_version': '3.8.8', 'engine_kind': 'new_build', 'design_size': {'width': 720, 'height': 1280}},
         'feel': {'spec': 'feel/GAME_FEEL.json', 'profile': 'tap_grid'}, 'fusion': {'base': 'base', 'feeders': [{'id': 'F' + str(i), 'slug': 'feeder' + str(i), 'intro_level': i * 3, 'rule': 'Synthetic rule.', 'decision_change': 'Changes legal target.', 'input_fit': 'Same board tap.', 'ablation_case': 'Removing rule changes output.'} for i in [1, 2, 3]]}, 'props': [prop],
         'systems': {k: {'enabled': True, 'unsupported': 'hide', 'verified_success_only': True} for k in ['profile_revisit', 'add_home_screen']},
         'ads': [{'format': 'rewarded_video', 'on_failure': 'no_reward'}]}
    c['systems']['home_gift'] = {'reward_policy': 'skill_dynamic_skin_progression', 'failed_claim': 'keep_eligibility'}
    put(root, 'workshop.json', c)
    put(root, 'ECONOMY.json', {'currency': 'Fixture Gems', 'skin_module': True, 'props': [prop]})
    levels = [{'id': n, 'type': 'milestone' if n % 10 == 0 else 'bonus' if n % 10 == 5 else 'normal', 'coins': 50, 'state': {'target': n}, 'solution': [{'tap': n}]} for n in range(1, 71)]
    plan = {'total_levels': 70, 'seed': 23, 'levels': [{'level': x['id'], 'type': x['type'], 'coins': x['coins'], **({'reward': {'coins': 250}} if x['type'] == 'milestone' else {})} for x in levels]}
    put(root, 'levels/game_levels.json', {'levels': levels}); put(root, 'levels/level_plan.json', plan)
    put(root, 'levels/actual_difficulty.json', {'levels': [{'level': n, 'actual_difficulty': n} for n in range(1, 71)]})
    for name, code in [('solver', 'def solve(level):\n    return level\n'), ('replay', 'def replay(level, action):\n    return bool(level)\n'), ('verify_model', 'def verify(level):\n    return True\n')]:
        put(root, 'tools/' + name + '.py', code)
    cases = [{'kind': kind, 'level': 1, 'input': {'tap': 1}, 'before': {'value': 0}, 'after': {'value': 1}, 'passed': True} for kind in ['win', 'lose', 'illegal_input']]
    cases += [{'kind': 'ablation', 'mechanic': f['id'], 'input': {'remove': f['id']}, 'before': {'legal': 2}, 'after': {'legal': 1}, 'passed': True} for f in c['fusion']['feeders']]
    for kind in sorted(wi.LIFECYCLE_CASES):
        before = {'starter': 0 if kind == 'starter_first_run' else 1, 'owned': 2, 'granted': kind != 'starter_first_run'}
        after = {'starter': 1, 'owned': 2, 'granted': True}
        cases.append({'kind': kind, 'prop_id': 'hint', 'input': {'event': kind}, 'before': before, 'after': after, 'passed': True})
    report = {'layer': 'rules_model', 'cocos_playtest': 'pending', 'cases': cases, 'verifier': 'tools/verify_model.py', 'implementation': [], 'results': [{'level': n, 'solved': True, 'replayed': True} for n in range(1, 71)]}
    put(root, 'references/MODEL_TESTS.json', report)
    parameters = {'timing': {'commit_delay_ms': 0, 'logical_lock_ms': 40, 'settle_ms': 120}, 'input': {'input_buffer_ms': 100, 'max_buffered_inputs': 1}}
    feel = {'schema': 'game-feel.v1', 'profile': 'tap_grid', 'status': 'parameter_reviewed', 'base_slug': 'base', 'engine_runtime': 'pending', 'base_input_evidence': ref(root, 'tools/solver.py'),
            'parameters': {group: {key: {'value': v, 'unit': 'ms' if key != 'max_buffered_inputs' else 'count'} for key, v in rows.items()} for group, rows in parameters.items()}}
    put(root, 'feel/GAME_FEEL.json', feel)
    binding = {'id': 'solver', **ref(root, 'tools/solver.py'), 'anchor': 'def solve(level):', 'hits': 1, 'export': 'solve'}
    behavior = {'schema': 'behavior.v1', 'status': 'final', 'model_bindings': [binding], 'model_report': {},
                'adapter_contract': {'mode': 'synchronous_pure_reducer', 'commit_order': wi.ORDER, 'result_fields': wi.FIELDS},
                'timing_sources': {'logic_commit_ms': 'timing.commit_delay_ms', 'next_input_ms': 'timing.logical_lock_ms', 'visual_tail_ms': 'timing.settle_ms', 'input_buffer_ms': 'input.input_buffer_ms', 'input_buffer_count': 'input.max_buffered_inputs'},
                'actions': [{'id': key, 'model_binding': 'solver', 'input_schema': {'payload': 'fixture'}, 'result_meaning': 'Synthetic defined transition output.', 'commit_order': wi.ORDER, 'parameters': []} for key in sorted(wi.MAIN_ACTIONS | {'F1', 'F2', 'F3', 'prop:hint'})],
                'golden_cases': [{'id': 'case' + str(i), 'case_index': i} for i in range(len(cases))]}
    put(root, 'implementation/BEHAVIOR.json', behavior)
    screens = [{'id': key, 'initial_state': 'default', 'states': ['default', 'error'] if key == 'loading' else ['default'], 'elements': [{'id': key + '.panel'}]} for key in ['loading', 'home', 'map', 'gameplay', 'pause', 'complete', 'failed', 'settings', 'gift', 'skins']]
    for screen in screens:
        screen['phase_guard'] = {'gameplay': ['ready', 'acting'], 'pause': ['paused'], 'complete': ['won'], 'failed': ['failed']}.get(screen['id'], [])
    experience = {'schema': 'experience.v1', 'status': 'final', 'screens': screens, 'actions': [], 'routes': [], 'teaching': {}, 'lifecycle': {'pause': {'owners': ['user', 'background', 'ad'], 'resume_when': 'owners_empty_and_same_run', 'simulation_while_paused': 'frozen', 'pointer_on_acquire': 'cancel_without_commit'}}}
    put(root, 'implementation/EXPERIENCE.json', experience)
    put(root, 'integration/assets/modules/AdRewards.ts', (base / 'assets/modules/AdRewards.ts').read_text())
    imported = copy.deepcopy(plan)
    for row in imported['levels']:
        extra = row.get('reward', {}).get('coins', 0)
        row['result_payout_input'] = {'level_coins': row['coins'], 'milestone_extra_coins': extra, 'sum': row['coins'] + extra}
    put(root, 'integration/assets/resources/config/level_plan.json', imported)
    seal(root)
    return root


def seal(root):
    """Refresh bindings around deliberately synthetic facts; never execute or validate a game."""
    c = read(root, 'workshop.json'); b = read(root, 'implementation/BEHAVIOR.json'); feel = read(root, 'feel/GAME_FEEL.json')
    report = read(root, 'references/MODEL_TESTS.json')
    for i, case in enumerate(report['cases']):
        body = {k: v for k, v in case.items() if k != 'evidence'}; rel = 'references/model/case' + str(i) + '.json'; put(root, rel, body); case['evidence'] = ref(root, rel)
    report['levels'] = ref(root, 'levels/game_levels.json'); report['implementation'] = [ref(root, 'tools/' + x + '.py') for x in ['solver', 'replay', 'verify_model']]
    put(root, 'references/MODEL_TESTS.json', report); b['model_report'] = ref(root, 'references/MODEL_TESTS.json'); put(root, 'implementation/BEHAVIOR.json', b)
    flat = {g: {k: p['value'] for k, p in rows.items()} for g, rows in feel['parameters'].items()}
    runtime = {'schema': 'runtime-behavior.v1', 'profile': wi.PROFILE, 'actions': b['actions'], 'model_bindings': b['model_bindings'], 'props': c['props'], 'design_size': c['implementation']['design_size'], 'feel_profile': 'tap_grid', 'feel': flat,
               'timings': {k: flat[s.split('.')[0]][s.split('.')[1]] for k, s in b['timing_sources'].items()}}
    build = {'assets': {name: digest(root, 'runtime/' + name) for name in ['session.cjs', 'motion.cjs', 'verify_golden.cjs']}}
    for key, rel in [('workshop_sha256', 'workshop.json'), ('behavior_sha256', 'implementation/BEHAVIOR.json'), ('feel_sha256', 'feel/GAME_FEEL.json')]:
        runtime[key] = build[key] = digest(root, rel)
    build['model_report_sha256'] = digest(root, 'references/MODEL_TESTS.json')
    put(root, 'runtime/behavior.json', runtime); put(root, 'runtime/build_inputs.json', build)
    put(root, 'runtime/domain_cases.json', [{'id': row['id'], 'model_report_sha256': b['model_report']['sha256'], 'case_index': row['case_index'], 'input_and_expected': report['cases'][row['case_index']] if 0 <= row['case_index'] < len(report['cases']) else None} for row in b['golden_cases']])
    exp = read(root, 'implementation/EXPERIENCE.json'); exp['bindings'] = {rel: digest(root, rel) for rel in ['workshop.json', 'feel/GAME_FEEL.json', 'implementation/BEHAVIOR.json', 'references/MODEL_TESTS.json', 'ECONOMY.json']}; put(root, 'implementation/EXPERIENCE.json', exp)
    common = {'experience_sha256': digest(root, 'implementation/EXPERIENCE.json'), 'inputs': exp['bindings'], 'layer': 'planned_specification', 'runtime_status': 'pending'}
    scene = {**common, 'schema': 'scene-blueprint.v1', **{k: exp[k] for k in ['screens', 'actions', 'routes', 'teaching', 'lifecycle']}}
    put(root, 'runtime/SCENE_BLUEPRINT.json', scene)
    put(root, 'runtime/ASSET_REQUIREMENTS.json', {**common, 'schema': 'asset-requirements.v1'})
    put(root, 'runtime/PLAYABLE_ACCEPTANCE.json', {**common, 'schema': 'playable-acceptance.v1'})
    output_paths = ['integration/assets/resources/config/level_plan.json', 'integration/assets/resources/config/unlock_table.json', 'integration/assets/modules/AdRewards.ts', 'integration/docs/modules.json', 'integration/docs/top-bar.json']
    source_paths = ['workshop.json', 'levels/game_levels.json', 'levels/level_plan.json', 'levels/actual_difficulty.json', 'ECONOMY.json', 'UI_PAGES.md', 'COPY_EN.md', 'GAME_DESIGN.md']
    bridge = {'schema': 'workshop-skill-bridge.v1', 'compatibility': {'status': 'data_compatible_runtime_pending', 'failures': []}, 'source_bindings': {p: digest(root, p) for p in source_paths}, 'generated_outputs': {p: digest(root, p) for p in output_paths},
              'target_bindings': {'starter_spec': {'path': 'cocos-game-from-starter/references/starter-pack-spec.md', 'sha256': c['target_spec_sha256']}, 'AdRewards': {'path': 'cocos-game-to-english/assets/modules/AdRewards.ts', 'sha256': digest(root, 'integration/assets/modules/AdRewards.ts')}}, 'import': {'fixture': 'Only a synthetic import mapping, no implementation claim.'}}
    put(root, 'integration/BRIDGE.json', bridge)
    task_inputs = ['workshop.json', 'levels/game_levels.json', 'levels/level_plan.json', 'references/MODEL_TESTS.json', 'runtime/session.cjs', 'runtime/motion.cjs', 'runtime/domain_cases.json', 'runtime/SCENE_BLUEPRINT.json', 'runtime/ASSET_REQUIREMENTS.json', 'runtime/PLAYABLE_ACCEPTANCE.json', 'integration/BRIDGE.json']
    tasks = {'schema': 'implementation-work-order.v1', 'profile': wi.PROFILE, 'parameters': wi._parameters(feel['parameters']), 'bindings': {p: digest(root, p) for p in task_inputs}, 'tasks': [{'id': 'I1', 'inputs': task_inputs, 'output': 'Synthetic adapter', 'acceptance': 'Actual runtime checks pending.'}]}
    put(root, 'runtime/implementation_tasks.json', tasks)
    values = {'REQ-ENGINE': ('workshop.json', '/implementation', c['implementation']), 'REQ-REUSE': ('workshop.json', '/approach', c['approach']), 'REQ-LOOP': ('workshop.json', '/fusion', c['fusion']), 'REQ-LEVELS': ('levels/game_levels.json', '/levels', {'count': 70}), 'REQ-MODEL': ('implementation/BEHAVIOR.json', '/model_bindings', b['model_bindings']),
              'REQ-FEEL': ('feel/GAME_FEEL.json', '/parameters', wi._parameters(feel['parameters'])), 'REQ-EXPERIENCE': ('implementation/EXPERIENCE.json', '/', {'blueprint': 'runtime/SCENE_BLUEPRINT.json', 'assets': 'runtime/ASSET_REQUIREMENTS.json', 'acceptance': 'runtime/PLAYABLE_ACCEPTANCE.json'}), 'REQ-ECONOMY': ('ECONOMY.json', '/', read(root, 'ECONOMY.json')), 'REQ-STARTER': ('workshop.json', '/props', c['props']), 'REQ-PLATFORM': ('workshop.json', '/systems', c['systems']), 'REQ-ADS': ('workshop.json', '/ads', c['ads']), 'REQ-IMPORT': ('integration/BRIDGE.json', '/import', bridge['import']), 'REQ-VERIFY': ('runtime/PLAYABLE_ACCEPTANCE.json', '/', {'result': 'pending'})}
    put(root, 'runtime/requirements.json', {'schema': 'creation-requirements.v1', 'source': 'compiled_pack_decisions', 'requirements': [{'id': rid, 'classification': 'specified', 'source': {**ref(root, path), 'json_pointer_or_section': pointer}, 'value': value, 'actual_implementation_paths': [], 'verification': {'downstream_runtime': 'pending'}} for rid, (path, pointer, value) in values.items()]})


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workshop-intake-'); self.addCleanup(self.temp.cleanup)
        self.top = Path(self.temp.name).resolve(); self.base = self.top / 'skills/cocos-game-to-english'
        self.root = fixture(self.top / 'pack', self.base)

    def inspect(self):
        return wi.inspect_pack(self.root, self.base)

    def blocked(self, needle=None):
        report = self.inspect(); self.assertEqual('blocked', report['status'], report)
        if needle:
            self.assertIn(needle, '\n'.join(report['errors']))
        return report

    def edit(self, rel, fn, reseal=False):
        value = read(self.root, rel); fn(value); put(self.root, rel, value)
        if reseal:
            seal(self.root)

    def test_full_current_fixture_is_input_bound_only(self):
        before = {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        report = self.inspect(); self.assertEqual(report['status'], 'bindings_verified_runtime_pending', report)
        self.assertFalse(report['facts']['model_execution_by_intake']); self.assertIn('authenticity or truth of supplied design/reports', report['not_verified'])
        self.assertEqual(len(before), len(report['file_inventory'])); self.assertTrue(all(wi.DIGEST.fullmatch(x['sha256']) for x in report['file_inventory']))
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()})
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_only_absent_contract_selects_legacy(self):
        (self.root / 'workshop.json').unlink(); report = self.inspect()
        self.assertEqual(report['route'], 'legacy'); self.assertEqual(report['status'], 'legacy_pending_review')

    def test_unknown_profile_cannot_downgrade(self):
        self.edit('workshop.json', lambda x: x.update(profile='workshop-quality-v999'))
        self.blocked('unsupported or malformed')

    def test_broken_contract_cannot_downgrade(self):
        put(self.root, 'workshop.json', '{broken'); self.blocked()

    def test_same_profile_missing_required_file_is_blocked(self):
        (self.root / 'runtime/SCENE_BLUEPRINT.json').unlink(); self.blocked('missing')

    def test_model_source_tamper_is_blocked_without_execution(self):
        put(self.root, 'tools/solver.py', 'raise RuntimeError("MUST NOT EXECUTE")\n'); self.blocked('binding mismatch')

    def test_duplicate_json_keys_are_blocked(self):
        put(self.root, 'workshop.json', '{"profile":"workshop-quality-v3","profile":"legacy"}'); self.blocked('duplicate JSON key')

    def test_escaping_binding_is_blocked(self):
        self.edit('integration/BRIDGE.json', lambda x: x['source_bindings'].update({'../outside.json': '0' * 64})); self.blocked('escaping')

    def test_absolute_binding_is_blocked(self):
        self.edit('integration/BRIDGE.json', lambda x: x['source_bindings'].update({'/tmp/outside.json': '0' * 64})); self.blocked('escaping')

    def test_pack_symlink_is_blocked(self):
        outside = put(self.top, 'outside.txt', 'outside')
        (self.root / 'linked.txt').symlink_to(outside); self.blocked('symlink')

    def test_english_text_is_enforced_including_escaped_json(self):
        self.edit('runtime/HELPER_REPORT.json', lambda x: x.update(label='\u4e2d\u6587'))
        self.blocked('non-English')

    def test_nonenglish_filename_is_blocked(self):
        put(self.root, '\u4e2d\u6587.txt', 'English text'); self.blocked('filenames')

    def test_consuming_module_drift_is_blocked(self):
        put(self.base, 'assets/modules/AdRewards.ts', '// changed consuming module\n'); self.blocked('consuming Skill AdRewards differs')

    def test_missing_consuming_skill_is_not_silently_assumed(self):
        (self.base / 'assets/modules/AdRewards.ts').unlink(); self.blocked('consuming base Skill')

    def test_actual_level_count_not_plan_label(self):
        self.edit('levels/game_levels.json', lambda x: x['levels'].pop(), reseal=True); self.blocked('70 actual levels')

    def test_plan_coin_difference_rejected_after_rebinding(self):
        self.edit('levels/level_plan.json', lambda x: x['levels'][0].update(coins=99), reseal=True); self.blocked('mismatch at level 1')

    def test_three_feeders_are_required_after_rebinding(self):
        self.edit('workshop.json', lambda x: x['fusion']['feeders'].pop(), reseal=True); self.blocked('F1/F2/F3')

    def test_prop_retry_refill_rejected_after_rebinding(self):
        self.edit('workshop.json', lambda x: x['props'][0].update(refill_on_retry=True), reseal=True); self.blocked('first-run-only')

    def test_golden_index_is_real_not_label(self):
        self.edit('implementation/BEHAVIOR.json', lambda x: x['golden_cases'][0].update(case_index=999), reseal=True); self.blocked('golden indexes')

    def test_golden_expected_case_tamper(self):
        self.edit('runtime/domain_cases.json', lambda x: x[0]['input_and_expected'].update(kind='invented')); self.blocked('compiled domain cases')

    def test_model_report_hash_drift(self):
        self.edit('references/MODEL_TESTS.json', lambda x: x.update(invented='changed')); self.blocked('binding mismatch')

    def test_raw_case_evidence_tamper(self):
        self.edit('references/model/case0.json', lambda x: x.update(passed=False)); self.blocked('binding mismatch')

    def test_full_session_phase_mapping_required(self):
        self.edit('implementation/EXPERIENCE.json', lambda x: next(s for s in x['screens'] if s['id'] == 'pause').update(phase_guard=['ready']), reseal=True); self.blocked('phase mapping')

    def test_planned_blueprint_cannot_claim_runtime_pass(self):
        self.edit('runtime/SCENE_BLUEPRINT.json', lambda x: x.update(runtime_status='passed')); self.blocked('layer/bindings')

    def test_rebound_import_cannot_lose_final_extra_coins(self):
        self.edit('integration/assets/resources/config/level_plan.json', lambda x: x['levels'][-1]['reward'].update(coins=0)); seal(self.root); self.blocked('original payout')

    def test_rebound_runtime_timing_cannot_be_invented(self):
        self.edit('runtime/behavior.json', lambda x: x['timings'].update(next_input_ms=999))
        self.blocked('runtime timing')

    def test_requirements_cannot_change_bound_product_facts(self):
        self.edit('runtime/requirements.json', lambda x: next(r for r in x['requirements'] if r['id'] == 'REQ-ENGINE')['value'].update(creator_version='invented'))
        self.blocked('current facts')

    def test_work_order_cannot_copy_invented_feel_numbers(self):
        self.edit('runtime/implementation_tasks.json', lambda x: x['parameters'][0].update(value=999))
        self.blocked('work order parameters')

    def test_requirements_cannot_copy_invented_feel_numbers(self):
        self.edit('runtime/requirements.json', lambda x: next(r for r in x['requirements'] if r['id'] == 'REQ-FEEL')['value'][0].update(value=999))
        self.blocked('current facts')

    def test_contract_and_bridge_target_identity_must_agree(self):
        self.edit('integration/BRIDGE.json', lambda x: x['target_bindings']['starter_spec'].update(sha256='b' * 64))
        self.blocked('target contract identities')

    def snapshot(self, reference='anchor', extra=None):
        text = '// Original source comment: \u539f\u59cb\u6e90\u7801\nconst value = 1;\n'
        raw_sha = hashlib.sha256(text.encode('utf-8')).hexdigest()
        rel = 'references/originals/raw_snapshot.json'
        put(self.root, rel, {'text': text, 'raw_sha256': raw_sha, **(extra or {})})
        if reference == 'anchor':
            put(self.root, 'references/source_anchors.json', {'originals': [{'slug': 'base', 'logic': ref(self.root, rel)}]})
        elif reference == 'comparison':
            put(self.root, 'references/comparisons.json', {'sources': [{'id': 'base', 'original': ref(self.root, rel), 'original_sha256': raw_sha}]})
        return rel

    def test_explicitly_bound_original_source_snapshot_retains_raw_language(self):
        self.snapshot()
        report = self.inspect(); self.assertEqual(report['status'], 'bindings_verified_runtime_pending', report)

    def test_comparison_snapshot_retains_raw_language_with_exact_raw_sha(self):
        self.snapshot('comparison')
        report = self.inspect(); self.assertEqual(report['status'], 'bindings_verified_runtime_pending', report)

    def test_capture_source_metadata_wrapper_is_supported(self):
        self.snapshot(extra={'archive_sha256': 'a' * 64, 'archive_member': 'logic.js', 'transformation': 'UTF-8-SIG decode; platform IDs redacted; JSON ASCII escaping'})
        report = self.inspect(); self.assertEqual(report['status'], 'bindings_verified_runtime_pending', report)

    def test_unreferenced_text_wrapper_is_not_a_source_exemption(self):
        self.snapshot('unreferenced'); self.blocked('non-English')

    def test_forged_snapshot_reference_sha_is_blocked(self):
        self.snapshot()
        self.edit('references/source_anchors.json', lambda x: x['originals'][0]['logic'].update(sha256='0' * 64))
        self.blocked('binding mismatch')

    def test_comparison_snapshot_raw_sha_cannot_be_forged(self):
        self.snapshot('comparison')
        self.edit('references/comparisons.json', lambda x: x['sources'][0].update(original_sha256='0' * 64))
        self.blocked('raw SHA differs')

    def test_snapshot_wrapper_cannot_hide_player_enum_field(self):
        self.snapshot(extra={'player_enum': ['\u4e2d\u6587']}); self.blocked('invalid source snapshot wrapper')

    def test_actual_player_enum_is_not_source_language(self):
        self.snapshot()
        self.edit('runtime/HELPER_REPORT.json', lambda x: x.update(player_enum=['\u4e2d\u6587']))
        self.blocked('non-English')

    def test_engine_source_comments_are_preserved_for_downstream_translation(self):
        put(self.root, 'source/assets/engine.js', '// \u539f\u59cb\u6ce8\u91ca\nconst value = 1;\n')
        report = self.inspect(); self.assertEqual(report['status'], 'bindings_verified_runtime_pending', report)

    def test_nonengine_javascript_stays_ascii_english(self):
        put(self.root, 'runtime/unbound_helper.js', '// \u4e2d\u6587\n')
        self.blocked('non-English')

    def proof_snapshot(self, source):
        h = digest(self.root, source); blob = 'handoff/team/blobs/' + h + '.json'
        path = self.root / blob; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((self.root / source).read_bytes())
        put(self.root, 'handoff/team/PROOF.json', {'files': [{'path': source, 'sha256': h, 'blob': blob}]})
        return blob

    def test_bound_team_blob_of_approved_source_wrapper_is_allowed(self):
        source = self.snapshot('comparison'); self.proof_snapshot(source)
        report = self.inspect(); self.assertEqual(report['status'], 'bindings_verified_runtime_pending', report)

    def test_fake_proof_source_path_does_not_exempt_player_document(self):
        source = self.snapshot('unreferenced'); self.proof_snapshot(source)
        self.blocked('non-English')

    def test_fake_proof_path_cannot_exempt_different_wrapper_bytes(self):
        source = self.snapshot('comparison'); blob = self.proof_snapshot(source)
        wrapped = read(self.root, blob); wrapped['text'] = '// \u4f2a\u9020\u6587\u6848\n'; put(self.root, blob, wrapped)
        self.blocked('binding mismatch')

    def test_proof_snapshot_sha_must_equal_approved_current_source(self):
        source = self.snapshot('comparison'); self.proof_snapshot(source)
        self.edit('handoff/team/PROOF.json', lambda x: x['files'][0].update(sha256='0' * 64))
        self.blocked('team source snapshot SHA mismatch')

    def test_proof_snapshot_filename_must_be_exact_hash_json(self):
        source = self.snapshot('comparison'); blob = self.proof_snapshot(source)
        alt = 'handoff/team/blobs/not_the_hash.json'; put(self.root, alt, read(self.root, blob))
        self.edit('handoff/team/PROOF.json', lambda x: x['files'][0].update(blob=alt))
        self.blocked('blob path must use the exact SHA')

    def test_unreferenced_blob_with_source_text_is_not_exempt(self):
        source = self.snapshot('comparison'); h = digest(self.root, source)
        put(self.root, 'handoff/team/blobs/' + h + '.json', read(self.root, source))
        self.blocked('non-English')

    def test_cli_new_output_outside_pack_no_overwrite(self):
        out = self.top / 'intake.json'; command = [sys.executable, '-B', str(Path(wi.__file__)), '--pack', str(self.root), '--base-skill', str(self.base), '--output', str(out)]
        first = subprocess.run(command, capture_output=True, text=True); self.assertEqual(0, first.returncode, first.stderr + first.stdout)
        raw = out.read_bytes(); second = subprocess.run(command, capture_output=True, text=True); self.assertNotEqual(0, second.returncode); self.assertEqual(raw, out.read_bytes())
        inside = subprocess.run(command[:-1] + [str(self.root / 'intake.json')], capture_output=True, text=True)
        self.assertNotEqual(0, inside.returncode); self.assertFalse((self.root / 'intake.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
