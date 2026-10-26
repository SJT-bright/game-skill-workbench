#!/usr/bin/env python3
"""Read-only, stdlib intake of a workshop pack; never run supplied code or certify its truth.
The output binds inspected files, not Cocos/model execution. Only absent workshop.json selects legacy.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path, PurePosixPath

PROFILE = 'workshop-quality-v3'
SCHEMA = 'workshop-intake.v1'
DIGEST = re.compile(r'^[0-9a-f]{64}$')
NON_ENGLISH = re.compile(r'[\u2e80-\u9fff\u0400-\u052f\uff00-\uffef]')
TEXT_SUFFIXES = {'.json', '.md', '.txt', '.csv', '.py', '.js', '.cjs', '.mjs', '.ts', '.html', '.css'}
ORDER = ['validate', 'apply_rules', 'update_ledger', 'publish_visuals']
FIELDS = ['accepted', 'outcome', 'events', 'next_state']
MAIN_ACTIONS = {'main_input', 'win', 'lose', 'cancel', 'pause', 'resume', 'retry', 'leave'}
PROP_POLICY = {'starter_amount': 1, 'grant_at': 'first_run', 'grant_once': True,
               'consume_order': 'starter_then_owned', 'invalid_use': 'no_charge',
               'refill_on_retry': False, 'refill_on_next_level': False,
               'refill_on_restart': False, 'refill_on_revive': False,
               'unspent_starter': 'persist_without_regrant'}
LIFECYCLE_CASES = {'starter_first_run', 'starter_retry_no_refill', 'starter_next_no_refill',
                   'starter_restart_no_refill', 'starter_revive_no_refill', 'starter_invalid_no_charge'}
REQUIRED_FILES = ['START_HERE.md', 'levels/game_levels.json', 'levels/level_plan.json',
                  'levels/actual_difficulty.json', 'feel/GAME_FEEL.json', 'implementation/BEHAVIOR.json',
                  'implementation/EXPERIENCE.json', 'references/MODEL_TESTS.json', 'runtime/behavior.json',
                  'runtime/domain_cases.json', 'runtime/session.cjs', 'runtime/motion.cjs',
                  'runtime/verify_golden.cjs', 'runtime/build_inputs.json', 'runtime/HELPER_REPORT.json',
                  'runtime/SCENE_BLUEPRINT.json', 'runtime/ASSET_REQUIREMENTS.json',
                  'runtime/PLAYABLE_ACCEPTANCE.json', 'runtime/UI_BLUEPRINT.md', 'runtime/COPY_CATALOG.md',
                  'runtime/IMPLEMENTATION_MAP.md', 'runtime/REMAKE_BRIEF.md', 'runtime/implementation_tasks.json',
                  'runtime/requirements.json', 'runtime/CREATION_SPEC.md', 'integration/BRIDGE.json',
                  'integration/assets/resources/config/level_plan.json',
                  'integration/assets/resources/config/unlock_table.json', 'integration/assets/modules/AdRewards.ts',
                  'integration/docs/modules.json', 'integration/docs/top-bar.json']


class IntakeError(ValueError):
    pass


def _hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IntakeError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def _json(raw):
    return json.loads(raw, object_pairs_hook=_strict_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(IntakeError('nonfinite JSON: ' + x)))


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


class Reader:
    def __init__(self, root):
        self.root = root
        self.files = {}
        self.cache = {}

    def path(self, rel):
        if not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel or any(ord(c) > 127 for c in rel):
            raise IntakeError('invalid ASCII relative pack path: ' + repr(rel))
        parts = PurePosixPath(rel).parts
        if PurePosixPath(rel).is_absolute() or '..' in parts or str(PurePosixPath(rel)) != rel:
            raise IntakeError('noncanonical or escaping pack path: ' + rel)
        p = self.root
        for part in parts:
            p = p / part
            if p.is_symlink():
                raise IntakeError('symlink is not an intake file: ' + rel)
        if not p.resolve().is_relative_to(self.root) or not p.is_file():
            raise IntakeError('missing or escaping pack file: ' + rel)
        return p

    def read(self, rel):
        p = self.path(rel)
        if rel not in self.files:
            size = p.stat().st_size
            if size > 64_000_000:
                raise IntakeError('file exceeds intake read budget: ' + rel)
            self.files[rel] = {'path': rel, 'sha256': _hash(p), 'size': size, 'role': rel.split('/')[0] if '/' in rel else 'design'}
        return p

    def json(self, rel):
        if rel not in self.cache:
            self.cache[rel] = _json(self.read(rel).read_text(encoding='utf-8-sig'))
        return self.cache[rel]

    def bind(self, rel, digest):
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise IntakeError('invalid SHA256 for ' + str(rel))
        self.read(rel)
        if self.files[rel]['sha256'] != digest:
            raise IntakeError('binding mismatch: ' + rel)

    def ref(self, row):
        if not isinstance(row, dict):
            raise IntakeError('path/SHA reference must be an object')
        self.bind(row['path'], row['sha256'])

    def mapping(self, rows):
        if not isinstance(rows, dict) or not rows:
            raise IntakeError('nonempty path/SHA mapping required')
        for rel, digest in rows.items():
            self.bind(rel, digest)

    def logical(self, name):
        options = [name, 'planning/' + name, 'art/' + name, 'audio/' + name]
        if name == 'GAME_DESIGN.md':
            options.append('planning/GAME_DESIGN_EN.md')
        for rel in options:
            if (self.root / rel).is_file():
                self.read(rel)
                return rel
        raise IntakeError('missing required design document: ' + name)

    def source_snapshots(self):
        # A JSON {text: ...} is never sufficient. Only explicitly bound source references
        # may preserve original-language source in their text field.
        allowed = set()
        references = []
        for logical, key, field in [('references/source_anchors.json', 'originals', 'logic'),
                                    ('references/comparisons.json', 'sources', 'original')]:
            if not (self.root / logical).exists():
                continue
            rows = self.json(logical).get(key, [])
            if not isinstance(rows, list):
                raise IntakeError('source references must be a list: ' + logical)
            for row in rows:
                ref = row.get(field)
                if isinstance(ref, dict):
                    references.append((logical, row, ref))
        for logical, row, ref in references:
            self.ref(ref)
            rel = ref['path']
            if not rel.startswith('references/') or not rel.endswith('.json'):
                continue
            data = self.json(rel)
            if not isinstance(data, dict) or not {'text', 'raw_sha256'} <= set(data):
                continue
            fields = {'text', 'raw_sha256', 'archive_sha256', 'archive_member', 'transformation'}
            if not set(data) <= fields or not isinstance(data['text'], str) or not isinstance(data['raw_sha256'], str) or not DIGEST.fullmatch(data['raw_sha256']):
                raise IntakeError('invalid source snapshot wrapper: ' + rel)
            if 'archive_sha256' in data and (not isinstance(data['archive_sha256'], str) or not DIGEST.fullmatch(data['archive_sha256'])):
                raise IntakeError('invalid source snapshot archive SHA: ' + rel)
            for key in ['archive_member', 'transformation']:
                if key in data and (not isinstance(data[key], str) or NON_ENGLISH.search(data[key])):
                    raise IntakeError('non-English or malformed source snapshot metadata: ' + rel)
            if logical == 'references/comparisons.json':
                if row.get('original_sha256') != data['raw_sha256']:
                    raise IntakeError('source snapshot raw SHA differs from comparison: ' + rel)
            elif row.get('raw_sha256') is not None and row['raw_sha256'] != data['raw_sha256']:
                raise IntakeError('source snapshot raw SHA differs from source anchor: ' + rel)
            if data.get('archive_sha256') is not None and row.get('archive_sha256') is not None and data['archive_sha256'] != row['archive_sha256']:
                raise IntakeError('source snapshot archive identity differs: ' + rel)
            allowed.add(rel)
        # Portable team evidence may stash an exact copy of an already-approved
        # source wrapper. Proof declarations cannot invent a new source exemption.
        original_sources = frozenset(allowed)
        proof_path = 'handoff/team/PROOF.json'
        if (self.root / proof_path).exists():
            proof = self.json(proof_path)
            rows = proof.get('files', [])
            if not isinstance(rows, list):
                raise IntakeError('team proof files must be a list')
            for row in rows:
                if not isinstance(row, dict) or row.get('path') not in original_sources:
                    continue
                rel = row['path']; digest = row.get('sha256'); blob = row.get('blob')
                if not isinstance(digest, str) or not DIGEST.fullmatch(digest) or digest != self.files[rel]['sha256']:
                    raise IntakeError('team source snapshot SHA mismatch: ' + rel)
                if not isinstance(blob, str) or blob != 'handoff/team/blobs/' + digest + '.json':
                    raise IntakeError('team source snapshot blob path must use the exact SHA: ' + rel)
                self.bind(blob, digest)
                if self.read(blob).read_bytes() != self.read(rel).read_bytes():
                    raise IntakeError('team source snapshot blob bytes differ: ' + rel)
                allowed.add(blob)
        return allowed

    def inventory(self):
        snapshots = self.source_snapshots()
        total = 0
        count = 0
        for parent, dirs, names in os.walk(self.root, followlinks=False):
            for name in sorted(dirs + names):
                p = Path(parent) / name
                rel = p.relative_to(self.root).as_posix()
                if p.is_symlink():
                    raise IntakeError('symlink is not permitted in pack: ' + rel)
                if any(ord(c) > 127 for c in rel):
                    raise IntakeError('pack filenames must be ASCII English: ' + repr(rel))
            for name in sorted(names):
                p = Path(parent) / name
                rel = p.relative_to(self.root).as_posix()
                self.read(rel)
                total += self.files[rel]['size']; count += 1
                if count > 10000 or total > 512_000_000:
                    raise IntakeError('pack exceeds intake file/read budget')
                if p.suffix.lower() in TEXT_SUFFIXES:
                    text = p.read_text(encoding='utf-8-sig')
                    engine_source = rel.startswith('source/') and p.suffix.lower() in {'.js', '.cjs', '.mjs', '.ts', '.json'}
                    if not engine_source and NON_ENGLISH.search(text):
                        raise IntakeError('non-English delivery text: ' + rel)
                    if p.suffix.lower() == '.json':
                        data = self.json(rel)
                        reviewed = {k: v for k, v in data.items() if k != 'text'} if rel in snapshots else data
                        if not engine_source and any(NON_ENGLISH.search(x) for x in _strings(reviewed)):
                            raise IntakeError('escaped non-English JSON text: ' + rel)
                    if not engine_source and p.suffix.lower() in {'.js', '.cjs', '.mjs', '.json'} and not text.isascii():
                        raise IntakeError('non-engine JS/JSON must be ASCII: ' + rel)


def _need(ok, message):
    if not ok:
        raise IntakeError(message)


def _ids(rows, label):
    _need(isinstance(rows, list), label + ' must be a list')
    keys = [r.get('id') for r in rows]
    _need(all(isinstance(k, str) and k for k in keys) and len(keys) == len(set(keys)), label + ' IDs must be distinct')
    return {r['id']: r for r in rows}


def _parameters(obj, prefix=''):
    rows = []
    for key, value in sorted(obj.items()):
        name = prefix + '.' + key if prefix else key
        if isinstance(value, dict) and 'value' in value:
            rows.append({'parameter': name, 'value': value['value'], 'unit': value.get('unit', ''),
                         'applies_to': value.get('applies_to', ''), 'source': value.get('source', {})})
        elif isinstance(value, dict):
            rows.extend(_parameters(value, name))
    return rows


def _module_path(base_skill):
    root = Path(base_skill).expanduser().resolve() if base_skill else Path(__file__).resolve().parents[1].parent / 'cocos-game-to-english'
    if root.name == 'cocos-game-from-starter':
        root = root.parent / 'cocos-game-to-english'
    p = root / 'assets/modules/AdRewards.ts'
    _need(p.is_file(), 'consuming base Skill AdRewards.ts is missing; pass --base-skill with the actual cocos-game-to-english Skill')
    return p


def _validate(r, base_skill):
    c = r.json('workshop.json')
    _need(isinstance(c, dict) and c.get('profile') == PROFILE, 'unsupported or malformed workshop profile; legacy fallback is forbidden')
    for rel in REQUIRED_FILES:
        r.read(rel)
    docs = {name: r.logical(name) for name in ['GAME_DESIGN.md', 'UI_PAGES.md', 'ECONOMY.json', 'ART_DIRECTION.md', 'AUDIO.md', 'COPY_EN.md']}
    e = r.json(docs['ECONOMY.json'])
    _need(c.get('approach') in ['modify_source', 'new_build'], 'explicit approach required')
    impl = c['implementation']; profile = c['feel']['profile']; design = impl['design_size']
    _need(impl.get('spec') == 'implementation/BEHAVIOR.json' and impl.get('experience_spec') == 'implementation/EXPERIENCE.json' and c['feel'].get('spec') == 'feel/GAME_FEEL.json', 'canonical behavior, experience and feel paths required')
    _need(impl.get('creator_version') in ['2.4.15', '3.8.8'] and impl.get('engine_kind') in (['new_build'] if c['approach'] == 'new_build' else ['editor_source', 'built_source']) and design.get('width') == 720 and type(design.get('height')) is int and 170 <= design['height'] <= 4096, 'explicit consistent engine and design canvas required')
    feeders = c['fusion']['feeders']; fi = _ids(feeders, 'feeders')
    _need(set(fi) == {'F1', 'F2', 'F3'} and len({x['slug'] for x in feeders} | {c['fusion']['base']}) == 4, 'one base and three different F1/F2/F3 sources required')
    for f in feeders:
        _need(type(f.get('intro_level')) is int and 1 <= f['intro_level'] <= 70 and all(f.get(k) for k in ['rule', 'decision_change', 'input_fit', 'ablation_case']), 'each feeder needs rule, adaptation and introduction facts')
    props = _ids(c.get('props', []), 'props')
    for p in props.values():
        _need(all(type(p.get(k)) is type(v) and p[k] == v for k, v in PROP_POLICY.items()) and p.get('grant_key'), 'first-run-only nonrefill starter policy required: ' + p['id'])
    _need(len({p['grant_key'] for p in props.values()}) == len(props), 'starter grant keys must be distinct')
    _need(e.get('props') == c.get('props', []), 'ECONOMY props differ from contract')
    for key in ['profile_revisit', 'add_home_screen']:
        s = c['systems'][key]
        _need(s.get('enabled') is True and s.get('unsupported') == 'hide' and s.get('verified_success_only') is True, 'platform entry contract incomplete: ' + key)
    gift = c['systems']['home_gift']
    _need(gift.get('reward_policy') == 'skill_dynamic_skin_progression' and 'coins' not in gift and gift.get('failed_claim') == 'keep_eligibility', 'dynamic home gift contract required')
    _need(c.get('ads') and all(x.get('format') == 'rewarded_video' and x.get('on_failure') == 'no_reward' for x in c['ads']), 'rewarded-video-only explicit ad failures required')
    levels = r.json('levels/game_levels.json')['levels']; plan = r.json('levels/level_plan.json')
    _need(len(levels) == 70 and plan.get('total_levels') == 70 and type(plan.get('seed')) is int, 'exactly 70 actual levels and original placement seed required')
    _need([x['id'] for x in levels] == list(range(1, 71)) and [x['level'] for x in plan['levels']] == list(range(1, 71)), 'actual/plan rows must cover ordered levels 1..70')
    for level, row in zip(levels, plan['levels']):
        _need(level.get('type') in ['normal', 'bonus', 'milestone'] and level['type'] == row['type'] and type(level.get('coins')) is int and level['coins'] == row['coins'] and level['coins'] >= 0 and isinstance(level.get('state'), dict) and level['state'] and isinstance(level.get('solution'), list) and level['solution'], 'actual layout/solution/type/coins mismatch at level ' + str(level['id']))
    feel = r.json('feel/GAME_FEEL.json')
    _need(feel.get('schema') == 'game-feel.v1' and feel.get('status') == 'parameter_reviewed' and feel.get('profile') == profile and profile in ['tap_grid', 'drag_snap', 'aim_release', 'runner_lane'] and feel.get('base_slug') == c['fusion']['base'], 'reviewed current feel/input profile required')
    _need(feel.get('engine_runtime') == 'pending', 'feel specification must not claim observed engine performance')
    r.ref(feel['base_input_evidence'])
    for group in feel['parameters'].values():
        for p in group.values():
            _need(isinstance(p, dict) and type(p.get('value')) in [int, float] and math.isfinite(p['value']) and p.get('unit'), 'feel values must be finite single numbers with units')
            if isinstance(p.get('source'), dict) and isinstance(p['source'].get('evidence'), dict):
                r.ref(p['source']['evidence'])
    b = r.json('implementation/BEHAVIOR.json')
    _need(b.get('schema') == 'behavior.v1' and b.get('status') == 'final', 'final behavior.v1 required')
    adapter = b['adapter_contract']
    _need(adapter.get('mode') == 'synchronous_pure_reducer' and adapter.get('commit_order') == ORDER and adapter.get('result_fields') == FIELDS, 'pure ordered adapter contract required')
    model = _ids(b['model_bindings'], 'model bindings')
    _need(model, 'actual model source bindings required')
    for m in model.values():
        r.ref(m); text = r.read(m['path']).read_text(encoding='utf-8')
        _need(isinstance(m.get('anchor'), str) and len(m['anchor']) >= 5 and text.count(m['anchor']) == m.get('hits') and m.get('hits', 0) > 0 and m.get('export') in text, 'model source anchor/export mismatch: ' + m['id'])
    actions = _ids(b['actions'], 'behavior actions')
    expected = MAIN_ACTIONS | set(fi) | {'prop:' + p for p in props}
    if profile in ['aim_release', 'runner_lane']:
        expected.add('simulation_tick')
    _need(set(actions) == expected, 'behavior must map every main event, F1/F2/F3 and prop')
    for a in actions.values():
        _need(a.get('model_binding') in model and a.get('input_schema') and a.get('result_meaning') and a.get('commit_order') == ORDER and isinstance(a.get('parameters'), list), 'behavior action mapping incomplete: ' + a['id'])
    _need(b['model_report'].get('path') == 'references/MODEL_TESTS.json', 'behavior must bind actual model report')
    r.ref(b['model_report']); report = r.json('references/MODEL_TESTS.json')
    _need(report.get('layer') == 'rules_model' and report.get('cocos_playtest') == 'pending', 'model report must retain rules-model layer and Cocos pending')
    r.ref(report['levels']); _need(report['levels']['path'] == 'levels/game_levels.json', 'model report levels path mismatch')
    code = report.get('implementation', [])
    _need(len(code) >= 3 and len({x['sha256'] for x in code}) >= 3, 'distinct verifier/solver/independent replay bindings required')
    for row in code:
        r.ref(row)
    _need(report.get('verifier') in {x['path'] for x in code}, 'verifier not included in model bindings')
    _need([x['level'] for x in report['results']] == list(range(1, 71)) and all(x.get('solved') is True and x.get('replayed') is True for x in report['results']), 'saved model report must cover all 70 solved/replayed results; this is not execution by intake')
    cases = report['cases']
    for case in cases:
        _need(case.get('passed') is True and case.get('input') is not None, 'saved model case is failed or lacks input')
        r.ref(case['evidence'])
        _need(r.json(case['evidence']['path']) == {k: v for k, v in case.items() if k != 'evidence'}, 'raw model case evidence differs')
    for prop in props:
        rows = [x for x in cases if x.get('prop_id') == prop]
        _need(LIFECYCLE_CASES <= {x['kind'] for x in rows}, 'missing per-prop starter lifecycle cases: ' + prop)
        for row in rows:
            if row.get('kind') not in LIFECYCLE_CASES:
                continue
            before, after = row['before'], row['after']
            _need({'starter', 'owned', 'granted'} <= set(before) and {'starter', 'owned', 'granted'} <= set(after), 'starter case missing actual ledgers')
            if row['kind'] == 'starter_first_run':
                _need(before['starter'] == 0 and before['granted'] is False and after['starter'] == 1 and after['granted'] is True and before['owned'] == after['owned'], 'first-run ledger must grant exactly one')
            else:
                _need(before == after and before['granted'] is True, 'retry/next/restart/revive/invalid must not refill or consume')
    selected = _ids(b['golden_cases'], 'golden cases'); indexes = [x['case_index'] for x in selected.values()]
    _need(all(type(i) is int and 0 <= i < len(cases) for i in indexes) and len(set(indexes)) == len(indexes), 'golden indexes invalid or duplicated')
    _need({'win', 'lose', 'illegal_input'} <= {cases[i]['kind'] for i in indexes}, 'golden win/lose/illegal references missing')
    _need(all(any(cases[i].get('mechanic') == f for i in indexes) for f in fi) and all(any(cases[i].get('prop_id') == p for i in indexes) for p in props), 'golden references omit feeder or prop')
    domain = r.json('runtime/domain_cases.json')
    wanted = [{'id': x['id'], 'model_report_sha256': b['model_report']['sha256'], 'case_index': x['case_index'], 'input_and_expected': cases[x['case_index']]} for x in b['golden_cases']]
    _need(domain == wanted, 'compiled domain cases differ from actual selected model indexes')
    runtime = r.json('runtime/behavior.json')
    _need(runtime.get('schema') == 'runtime-behavior.v1' and runtime.get('profile') == PROFILE, 'current runtime behavior schema required')
    for field, rel in [('workshop_sha256', 'workshop.json'), ('behavior_sha256', 'implementation/BEHAVIOR.json'), ('feel_sha256', 'feel/GAME_FEEL.json')]:
        r.bind(rel, runtime[field])
    _need(runtime.get('actions') == b['actions'] and runtime.get('model_bindings') == b['model_bindings'] and runtime.get('props') == c['props'] and runtime.get('design_size') == design and runtime.get('feel_profile') == profile, 'compiled runtime differs from current contract')
    flat_feel = {group: {key: p['value'] for key, p in rows.items()} for group, rows in feel['parameters'].items()}
    _need(runtime.get('feel') == flat_feel, 'compiled runtime feel values differ from canonical parameters')
    timing_sources = {'logic_commit_ms': 'timing.commit_delay_ms', 'next_input_ms': 'timing.logical_lock_ms', 'visual_tail_ms': 'timing.settle_ms', 'input_buffer_ms': 'input.input_buffer_ms', 'input_buffer_count': 'input.max_buffered_inputs'}
    _need(b.get('timing_sources') == timing_sources, 'behavior timing source mapping differs from canonical feel')
    for key, source in timing_sources.items():
        group, field = source.split('.')
        _need(runtime['timings'][key] == flat_feel[group][field], 'runtime timing value differs from canonical feel: ' + key)
    build = r.json('runtime/build_inputs.json')
    for field, rel in [('workshop_sha256', 'workshop.json'), ('behavior_sha256', 'implementation/BEHAVIOR.json'), ('feel_sha256', 'feel/GAME_FEEL.json'), ('model_report_sha256', 'references/MODEL_TESTS.json')]:
        r.bind(rel, build[field])
    for name in ['session.cjs', 'motion.cjs', 'verify_golden.cjs']:
        r.bind('runtime/' + name, build['assets'][name])
    experience = r.json('implementation/EXPERIENCE.json')
    _need(experience.get('schema') == 'experience.v1' and experience.get('status') == 'final', 'final planned experience.v1 required')
    source_mapping = {'workshop.json': 'workshop.json', 'feel/GAME_FEEL.json': 'feel/GAME_FEEL.json', 'implementation/BEHAVIOR.json': 'implementation/BEHAVIOR.json', 'references/MODEL_TESTS.json': 'references/MODEL_TESTS.json', 'ECONOMY.json': docs['ECONOMY.json']}
    _need(set(experience['bindings']) == set(source_mapping), 'experience source binding coverage incomplete')
    for logical, rel in source_mapping.items():
        r.bind(rel, experience['bindings'][logical])
    screens = _ids(experience['screens'], 'experience screens')
    required_screens = {'loading', 'home', 'map', 'gameplay', 'pause', 'complete', 'failed', 'settings', 'gift'} | ({'skins'} if e.get('skin_module') else set())
    _need(required_screens <= set(screens), 'full planned screen set missing')
    for s in screens.values():
        _need(s.get('initial_state') in s.get('states', []) and s.get('states') and isinstance(s.get('elements'), list) and s['elements'], 'screen needs explicit states and elements: ' + s['id'])
    for name, phases in {'gameplay': ['ready', 'acting'], 'pause': ['paused'], 'complete': ['won'], 'failed': ['failed']}.items():
        _need(screens[name].get('phase_guard') == phases, 'session/planned screen phase mapping incomplete: ' + name)
    pause = experience['lifecycle']['pause']
    _need(set(pause.get('owners', [])) == {'user', 'background', 'ad'} and pause.get('resume_when') == 'owners_empty_and_same_run' and pause.get('simulation_while_paused') == 'frozen' and pause.get('pointer_on_acquire') == 'cancel_without_commit', 'pause-owner lifecycle incomplete')
    for rel, schema in [('runtime/SCENE_BLUEPRINT.json', 'scene-blueprint.v1'), ('runtime/ASSET_REQUIREMENTS.json', 'asset-requirements.v1'), ('runtime/PLAYABLE_ACCEPTANCE.json', 'playable-acceptance.v1')]:
        data = r.json(rel)
        _need(data.get('schema') == schema and data.get('layer') == 'planned_specification' and data.get('runtime_status') == 'pending' and data.get('inputs') == experience['bindings'], 'runtime blueprint layer/bindings invalid: ' + rel)
        r.bind('implementation/EXPERIENCE.json', data['experience_sha256'])
    scene = r.json('runtime/SCENE_BLUEPRINT.json')
    _need(scene.get('screens') == experience['screens'] and scene.get('actions') == experience['actions'] and scene.get('routes') == experience['routes'] and scene.get('teaching') == experience['teaching'] and scene.get('lifecycle') == experience['lifecycle'], 'scene blueprint diverges from planned experience')
    bridge = r.json('integration/BRIDGE.json')
    _need(bridge.get('schema') == 'workshop-skill-bridge.v1' and bridge.get('compatibility', {}).get('status') == 'data_compatible_runtime_pending' and bridge['compatibility'].get('failures') == [], 'bridge must be data compatible while runtime stays pending')
    r.mapping(bridge['source_bindings']); r.mapping(bridge['generated_outputs'])
    _need({'workshop.json', 'levels/game_levels.json', 'levels/level_plan.json', 'levels/actual_difficulty.json', docs['ECONOMY.json'], docs['UI_PAGES.md'], docs['COPY_EN.md'], docs['GAME_DESIGN.md']} <= set(bridge['source_bindings']), 'bridge source coverage incomplete')
    _need({'integration/assets/resources/config/level_plan.json', 'integration/assets/resources/config/unlock_table.json', 'integration/assets/modules/AdRewards.ts', 'integration/docs/modules.json', 'integration/docs/top-bar.json'} <= set(bridge['generated_outputs']), 'bridge generated-output coverage incomplete')
    spec_binding = bridge['target_bindings']['starter_spec']
    _need(isinstance(c.get('target_spec_sha256'), str) and DIGEST.fullmatch(c['target_spec_sha256']) and c['target_spec_sha256'] == spec_binding.get('sha256') and spec_binding.get('path') == 'cocos-game-from-starter/references/starter-pack-spec.md', 'workshop and bridge target contract identities differ')
    module = bridge['target_bindings']['AdRewards']
    _need(module.get('path') == 'cocos-game-to-english/assets/modules/AdRewards.ts', 'unexpected target AdRewards identity')
    r.bind('integration/assets/modules/AdRewards.ts', module['sha256'])
    consumed = _module_path(base_skill)
    _need(_hash(consumed) == module['sha256'], 'consuming Skill AdRewards differs from the pack target; explicit target migration required')
    imported = r.json('integration/assets/resources/config/level_plan.json')
    _need(len(imported['levels']) == 70 and imported.get('seed') == plan['seed'], 'import plan count or original seed changed')
    for row, src in zip(imported['levels'], plan['levels']):
        _need(all(row[k] == src[k] for k in ['level', 'type', 'coins']) and row.get('reward', {}).get('coins', 0) == src.get('reward', {}).get('coins', 0), 'import plan changes original payout/type/order')
        payout = row['result_payout_input']
        _need(payout.get('level_coins') == src['coins'] and payout.get('milestone_extra_coins') == src.get('reward', {}).get('coins', 0) and payout.get('sum') == src['coins'] + src.get('reward', {}).get('coins', 0), 'import payout sum omits or duplicates milestone coins')
    tasks = r.json('runtime/implementation_tasks.json')
    _need(tasks.get('schema') == 'implementation-work-order.v1' and tasks.get('profile') == PROFILE, 'current implementation work order required')
    r.mapping(tasks['bindings'])
    _need(tasks.get('parameters') == _parameters(feel['parameters']), 'work order parameters differ from canonical feel facts')
    for task in tasks['tasks']:
        _need(task.get('inputs') and task.get('output') and task.get('acceptance'), 'implementation task lacks concrete input/output/acceptance')
        for rel in task['inputs']:
            _need(rel in tasks['bindings'], 'task input missing binding: ' + rel)
            r.read(rel)
    req = r.json('runtime/requirements.json')
    _need(req.get('schema') == 'creation-requirements.v1' and req.get('source') == 'compiled_pack_decisions', 'compiled requirements mapping required')
    requirements = _ids(req['requirements'], 'requirements')
    _need({'REQ-ENGINE', 'REQ-REUSE', 'REQ-LOOP', 'REQ-LEVELS', 'REQ-MODEL', 'REQ-FEEL', 'REQ-EXPERIENCE', 'REQ-ECONOMY', 'REQ-STARTER', 'REQ-PLATFORM', 'REQ-ADS', 'REQ-IMPORT', 'REQ-VERIFY'} <= set(requirements), 'required product decision mapping incomplete')
    for row in requirements.values():
        r.ref(row['source'])
        _need(row.get('classification') == 'specified' and row.get('actual_implementation_paths') == [] and row.get('verification', {}).get('downstream_runtime') == 'pending', 'input requirements must not assert completed runtime wiring')
    required_values = {'REQ-ENGINE': ('workshop.json', '/implementation', c['implementation']),
                       'REQ-REUSE': ('workshop.json', '/approach', c['approach']),
                       'REQ-LOOP': ('workshop.json', '/fusion', c['fusion']),
                       'REQ-MODEL': ('implementation/BEHAVIOR.json', '/model_bindings', b['model_bindings']),
                       'REQ-FEEL': ('feel/GAME_FEEL.json', '/parameters', _parameters(feel['parameters'])),
                       'REQ-EXPERIENCE': ('implementation/EXPERIENCE.json', '/', {'blueprint': 'runtime/SCENE_BLUEPRINT.json', 'assets': 'runtime/ASSET_REQUIREMENTS.json', 'acceptance': 'runtime/PLAYABLE_ACCEPTANCE.json'}),
                       'REQ-ECONOMY': (docs['ECONOMY.json'], '/', e),
                       'REQ-STARTER': ('workshop.json', '/props', c['props']),
                       'REQ-PLATFORM': ('workshop.json', '/systems', c['systems']),
                       'REQ-ADS': ('workshop.json', '/ads', c['ads']),
                       'REQ-IMPORT': ('integration/BRIDGE.json', '/import', bridge['import'])}
    for rid, (path, pointer, value) in required_values.items():
        row = requirements[rid]
        _need(row['source']['path'] == path and row['source'].get('json_pointer_or_section') == pointer and row.get('value') == value, 'requirement value/source does not match current facts: ' + rid)
    _need(requirements['REQ-LEVELS']['value'].get('count') == 70, 'requirements level count differs from actual levels')
    _need(requirements['REQ-VERIFY']['value'].get('result') == 'pending', 'requirements must retain pending playable verification')
    _need(all(key in tasks['bindings'] for key in ['workshop.json', 'levels/game_levels.json', 'levels/level_plan.json', 'references/MODEL_TESTS.json', 'runtime/session.cjs', 'runtime/motion.cjs', 'runtime/domain_cases.json', 'runtime/SCENE_BLUEPRINT.json', 'runtime/ASSET_REQUIREMENTS.json', 'runtime/PLAYABLE_ACCEPTANCE.json', 'integration/BRIDGE.json']), 'work order binding coverage incomplete')
    return {'approach': c['approach'], 'creator_version': impl['creator_version'], 'design_size': design,
            'level_count': 70, 'fusion_ids': sorted(fi), 'input_profile': profile, 'props': sorted(props),
            'prop_policy': 'first-new-save-only; starter_then_owned; success-only charge; no refill',
            'experience_screens': sorted(screens), 'session_phases': ['ready', 'acting', 'paused', 'won', 'failed'],
            'target_module': {'path': module['path'], 'sha256': module['sha256']},
            'recorded_golden_case_count': len(indexes), 'model_execution_by_intake': False}


def inspect_pack(pack, base_skill=None):
    """Return a serializable read-only input-binding report. Never execute any pack script."""
    result = {'schema': SCHEMA, 'route': 'blocked', 'status': 'blocked', 'pack_profile': None,
              'errors': [], 'warnings': [], 'file_inventory': [], 'facts': {},
              'handoff': {'brief': 'runtime/REMAKE_BRIEF.md', 'requirements': 'runtime/requirements.json',
                          'creation_spec': 'runtime/CREATION_SPEC.md', 'bridge': 'integration/BRIDGE.json'},
              'scope': 'input_structure_and_file_bindings_only',
              'not_verified': ['authenticity or truth of supplied design/reports', 'execution of rule models or golden cases',
                               'Cocos import, scenes or playable touch experience', 'engine/device performance',
                               'real platform/advertising callbacks and persistence', 'visible strings retained in source/ engine code; downstream English conversion is still required', 'upload, review or release']}
    reader = None
    try:
        raw_root = Path(pack).expanduser()
        _need(not raw_root.is_symlink() and raw_root.is_dir(), 'pack must be an existing ordinary directory')
        root = raw_root.resolve(); reader = Reader(root)
        marker = root / 'workshop.json'
        if not marker.exists() and not marker.is_symlink():
            result.update(route='legacy', status='legacy_pending_review')
            result['warnings'].append('No workshop.json: use the normal legacy starter intake and semantic review; this report grants no implementation acceptance.')
            return result
        c = reader.json('workshop.json')
        result['pack_profile'] = c.get('profile') if isinstance(c, dict) else None
        result['route'] = 'workshop_v3'
        reader.inventory()
        result['facts'] = _validate(reader, base_skill)
        for rel, row in reader.files.items():
            _need(_hash(reader.path(rel)) == row['sha256'], 'file changed during intake: ' + rel)
        result['status'] = 'bindings_verified_runtime_pending'
        result['warnings'].append('Matching hashes and correct structure show consistency with inspected inputs, not authenticity, safe code or game quality.')
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError) as exc:
        result['errors'].append(type(exc).__name__ + ': ' + str(exc))
        result['route'] = 'blocked'
    finally:
        if reader is not None:
            result['file_inventory'] = sorted(reader.files.values(), key=lambda x: x['path'])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='New JSON report; existing paths are never overwritten')
    parser.add_argument('--base-skill', type=Path)
    args = parser.parse_args(argv)
    # Output must be outside the inspected pack so intake never mutates its own input.
    root = args.pack.expanduser().resolve(); out = args.output.expanduser().absolute()
    if out.resolve().is_relative_to(root):
        parser.error('--output must be outside the pack; intake is read-only')
    if not out.parent.is_dir():
        parser.error('--output parent must already exist')
    report = inspect_pack(args.pack, args.base_skill)
    try:
        with out.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=True, indent=2, allow_nan=False); stream.write('\n')
    except FileExistsError:
        parser.error('--output already exists; refusing overwrite')
    print(json.dumps({'schema': SCHEMA, 'route': report['route'], 'status': report['status'], 'errors': report['errors']}, ensure_ascii=True))
    return 1 if report['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
