"""Calibration only; no game acceptance implied."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_page_richness as audit
import visual_maintenance_scope as visual
from maintenance_scope import sha


class Cases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.binding = {'source_sha256': 'src', 'web_tree_sha256': 'web', 'native_tree_sha256': 'native', 'build_tag': 'r'}
        self.scene = self.root / 'main.fire'
        self.scene.write_text('[{"__type__":"cc.Node","_name":"btn-sound"},{"__type__":"cc.Node","_name":"btn-shake"}]', encoding='utf-8')
        self.scope_file = self.root / 'scope.json'
        self.scope_file.write_text('{}', encoding='utf-8')
        self.policy_file = self.root / 'policy.json'
        self.dumps = self._settings_dumps()
        self._write_policy()

    def tearDown(self):
        self.temp.cleanup()
        audit.MAINTENANCE_RULES = set()

    def _settings_dumps(self):
        output = []
        for width, height in ((393, 852), (375, 667)):
            raw = {
                'tool': 'ui_dump', 'schema': 1, 'engine': '2.4.15', 'api': '2.x', 'scene': 'main',
                'page': {'width': width, 'height': height, 'dpr': 3}, 'canvas_css': [0, 0, width, height],
                'canvases': 1, 'cameras': 0, 'truncated': False, 'errors': [],
                'nodes': [
                    {'id': 's', 'name': 'btn-sound', 'path': 'Canvas/panel-setting/panel/sound/btn-sound',
                     'depth': 3, 'rect': [.1, .1, .1, .1], 'opacity': 1, 'comps': {'button': {'interactable': True}}},
                    {'id': 'h', 'name': 'btn-shake', 'path': 'Canvas/panel-setting/panel/shake/btn-shake',
                     'depth': 3, 'rect': [.2, .1, .1, .1], 'opacity': 1, 'comps': {'button': {'interactable': True}}},
                ],
            }
            raw_path = self.root / ('raw-%d.json' % width)
            raw_path.write_text(json.dumps(raw), encoding='utf-8')
            shot = self.root / ('shot-%d.png' % width)
            shot.write_bytes(('pixels-%d' % width).encode())
            dump_path = self.root / ('dump-%d.json' % width)
            derived = dict(raw, producer='ego_page.dump_ui', purpose='settings_sound', screen='settings',
                           screenshot=str(shot), _file=str(dump_path),
                           derived_provenance={'source_dump': str(raw_path), 'source_sha256': sha(raw_path),
                                               'source_screenshot_sha256': sha(shot)})
            dump_path.write_text(json.dumps(derived), encoding='utf-8')
            output.append(derived)
        return output

    def _write_policy(self, rule='settings_original_switches'):
        entries = []
        for d in self.dumps:
            path = Path(d['_file'])
            entries.append({'path': str(path), 'sha256': sha(path)})
        self.policy_file.write_text(json.dumps({
            'schema': 'maintenance_visual_policy.v2', 'binding': self.binding,
            'scope': {'path': str(self.scope_file), 'sha256': sha(self.scope_file)},
            'original_scene_refs': [{'path': str(self.scene), 'sha256': sha(self.scene)}],
            'rules': [rule],
            'mappings': [{'rule': rule, 'anchors': ['btn-sound', 'btn-shake'], 'current_dumps': entries,
                          'reason': 'The original game contains these existing settings controls and this page is retained.'}],
        }), encoding='utf-8')

    def _validated(self):
        return {'original_sources': [{'path': str(self.scene), 'sha256': sha(self.scene)}], 'existing_features': ['daily_checkin'],
                'economy_catalog': {}, 'runtime_trace': {}}

    def test_valid_named_mapping_has_exact_report_boundary(self):
        with patch.object(visual, 'load_scope', return_value=self._validated()):
            result = visual.validate_policy(self.policy_file, self.scope_file, self.root, self.binding, self.dumps)
        self.assertEqual(result['rules'], ['settings_original_switches'])
        self.assertEqual(result['mappings'][0]['skipped_template_checks'],
                         ['required:settings', 'settings_general', 'settings_sound'])
        self.assertEqual(len(result['mappings'][0]['current_pages']), 2)

    def test_default_new_project_templates_remain_strict(self):
        audit.MAINTENANCE_RULES = set()
        d = {'nodes': [], 'purpose': 'settings_sound', '_file': str(self.root / 'empty.json')}
        problems, _ = audit.check(d)
        self.assertTrue(any(x.startswith('settings_sound:') for x in problems))
        d['purpose'] = 'home'
        problems, _ = audit.check(d)
        self.assertTrue(any(x.startswith('home_page:') for x in problems))

    def test_only_named_templates_are_mapped(self):
        audit.MAINTENANCE_RULES = {'settings_original_switches'}
        d = {'nodes': [], 'purpose': 'settings_sound', '_file': str(self.root / 'empty.json')}
        problems, _ = audit.check(d)
        self.assertFalse(any(x.startswith('settings_sound:') for x in problems))
        self.assertTrue(any(x.startswith('monotonous:') for x in problems))
        d['purpose'] = 'home'
        problems, _ = audit.check(d)
        self.assertTrue(any(x.startswith('home_page:') for x in problems))

    def test_home_mapping_does_not_waive_generic_visual_rules(self):
        d = {'nodes': [], 'purpose': 'home', '_file': str(self.root / 'empty.json')}
        audit.MAINTENANCE_RULES = set()
        default, _ = audit.check(d)
        audit.MAINTENANCE_RULES = {'home_original_composition'}
        mapped, _ = audit.check(d)
        self.assertTrue(any(x.startswith('home_page:') for x in default))
        self.assertFalse(any(x.startswith('home_page:') for x in mapped))
        self.assertTrue(any(x.startswith('monotonous:') for x in mapped))

    def test_result_mapping_does_not_waive_result_page_content(self):
        d = {'nodes': [], 'purpose': 'result_win', '_file': str(self.root / 'empty.json')}
        audit.MAINTENANCE_RULES = {'result_original_multiplier'}
        problems, _ = audit.check(d)
        self.assertTrue(any(x.startswith('result_page:') for x in problems))
        self.assertFalse(any(x.startswith('result_double:') for x in problems))

    def test_checkin_mapping_only_waives_day7_size(self):
        nodes = []
        for day in range(1, 8):
            y = .08 + (day - 1) * .1
            nodes.append({'name': 'card%d' % day, 'path': 'Canvas/card%d' % day, 'rect': [.2, y, .2, .06],
                          'opacity': 1, 'comps': {'sprite': {'frame': 'card'}}})
            nodes.append({'name': 'day%d' % day, 'path': 'Canvas/card%d/day%d' % (day, day),
                          'rect': [.25, y + .01, .1, .03], 'opacity': 1,
                          'comps': {'label': {'string': str(day), 'fontSize': 12, 'height': 12}}})
        d = {'nodes': nodes, 'purpose': 'checkin', '_file': str(self.root / 'empty.json')}
        audit.MAINTENANCE_RULES = set()
        default, _ = audit.check(d)
        audit.MAINTENANCE_RULES = {'checkin_original_card_sizes'}
        mapped, _ = audit.check(d)
        self.assertTrue(any('day-7 card must be the big one' in x for x in default))
        self.assertFalse(any('day-7 card must be the big one' in x for x in mapped))
        self.assertTrue(any(x.startswith('checkin_page:') for x in mapped))

    def test_missing_original_toggle_blocks_mapping(self):
        raw_path = Path(self.dumps[1]['derived_provenance']['source_dump'])
        raw = json.loads(raw_path.read_text())
        raw['nodes'][1]['comps']['button']['interactable'] = False
        raw_path.write_text(json.dumps(raw), encoding='utf-8')
        broken = copy.deepcopy(self.dumps[1])
        broken['nodes'][1]['comps']['button']['interactable'] = False
        broken['derived_provenance']['source_sha256'] = sha(raw_path)
        path = Path(broken['_file'])
        path.write_text(json.dumps(broken), encoding='utf-8')
        self.dumps[1] = broken
        self._write_policy()
        with self.assertRaisesRegex(ValueError, 'active btn-sound and btn-shake'):
            with patch.object(visual, 'load_scope', return_value=self._validated()):
                visual.validate_policy(self.policy_file, self.scope_file, self.root, self.binding, self.dumps)

    def test_policy_requires_explicit_mapping_records(self):
        data = json.loads(self.policy_file.read_text())
        data['mappings'] = []
        self.policy_file.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'per-rule visual mappings'):
            with patch.object(visual, 'load_scope', return_value=self._validated()):
                visual.validate_policy(self.policy_file, self.scope_file, self.root, self.binding, self.dumps)

    def test_unknown_mapping_rejected(self):
        self._write_policy('ignore_all')
        with self.assertRaisesRegex(ValueError, 'unknown, duplicate, or malformed'):
            with patch.object(visual, 'load_scope', return_value=self._validated()):
                visual.validate_policy(self.policy_file, self.scope_file, self.root, self.binding, self.dumps)

    def test_stale_binding_rejected(self):
        with self.assertRaisesRegex(ValueError, 'current binding required'):
            with patch.object(visual, 'load_scope', return_value=self._validated()):
                visual.validate_policy(self.policy_file, self.scope_file, self.root, {**self.binding, 'build_tag': 'old'}, self.dumps)

    def test_one_ratio_rejected(self):
        data = json.loads(self.policy_file.read_text())
        data['mappings'][0]['current_dumps'] = data['mappings'][0]['current_dumps'][:1]
        self.policy_file.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'both real mobile ratios'):
            with patch.object(visual, 'load_scope', return_value=self._validated()):
                visual.validate_policy(self.policy_file, self.scope_file, self.root, self.binding, self.dumps)

    def test_same_ratio_twice_rejected(self):
        data = json.loads(self.policy_file.read_text())
        first = data['mappings'][0]['current_dumps'][0]
        data['mappings'][0]['current_dumps'][1] = first
        self.policy_file.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'duplicate viewport'):
            with patch.object(visual, 'load_scope', return_value=self._validated()):
                visual.validate_policy(self.policy_file, self.scope_file, self.root, self.binding, self.dumps)

    def test_raw_dump_mutation_rejected(self):
        raw = Path(self.dumps[0]['derived_provenance']['source_dump'])
        data = json.loads(raw.read_text())
        data['nodes'][0]['name'] = 'invented'
        raw.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'missing/changed evidence'):
            visual.validate_derived(self.dumps[0])

    def test_envelope_node_mutation_rejected(self):
        changed = copy.deepcopy(self.dumps[0])
        changed['nodes'][0]['name'] = 'invented'
        with self.assertRaisesRegex(ValueError, 'changed original field nodes'):
            visual.validate_derived(changed)

    def test_wrong_screenshot_rejected(self):
        shot = Path(self.dumps[0]['screenshot'])
        shot.write_bytes(b'wrong pixels')
        with self.assertRaisesRegex(ValueError, 'missing/changed evidence'):
            visual.validate_derived(self.dumps[0])

    def test_mapping_does_not_hide_small_text_or_any_other_visual_error(self):
        node = {'name': 'label', 'path': 'Canvas/lbl', 'rect': [0, 0, .1, .01], 'screen': [0, 0, .1, .01],
                'opacity': 1, 'comps': {'label': {'string': 'bad text', 'fontSize': 5, 'height': 10,
                                                 'color': [20, 20, 20]}}}
        d = {'nodes': [node], 'purpose': 'settings_sound', '_file': str(self.root / 'dump.json'),
             'page': {'width': 393, 'height': 852}, 'canvas_css': [0, 0, 393, 852]}
        audit.MAINTENANCE_RULES = {'settings_original_switches'}
        problems, _ = audit.check(d)
        self.assertTrue(any(x.startswith('small_text:') for x in problems))
        self.assertTrue(any(x.startswith('plain_text:') for x in problems))

    def test_mapping_requires_current_dump_in_the_full_audit_set(self):
        data = json.loads(self.policy_file.read_text())
        extra = self.root / 'unrelated.json'
        extra.write_text('{}')
        data['mappings'][0]['current_dumps'][0] = {'path': str(extra), 'sha256': sha(extra)}
        self.policy_file.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'not in this audit input'):
            with patch.object(visual, 'load_scope', return_value=self._validated()):
                visual.validate_policy(self.policy_file, self.scope_file, self.root, self.binding, self.dumps)


if __name__ == '__main__':
    unittest.main()
