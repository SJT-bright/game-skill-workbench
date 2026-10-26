"""Synthetic evidence only; no game, browser, PCM capture or producer execution."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_sound_settings as sound
import audit_interaction_audio as interaction
import test_resource_and_issue_obligations as package_fixtures


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SoundProfile(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sound-profile-contract-')
        self.project = Path(self.temp.name) / 'Reviewed game'
        self.native = self.project / 'native'
        self.qa = self.project / 'qa'
        self.qa.mkdir(parents=True)
        self.profile = {'id': 'synthetic_sound_settings_v1', 'project': '', 'native_sha256': {'game.js': 'fixture', 'main.js': 'fixture', 'adapter.js': 'fixture', 'native-preload.js': 'fixture', 'native-load-guard.js': 'fixture', 'assets/main/index.js': 'fixture'}, 'producer_sha256': {'qa/g7-ui.mjs': 'fixture', 'qa/browser-helpers.mjs': 'fixture', 'qa/audio-settings-check.cjs': 'fixture', 'qa/capture-audio.mjs': 'fixture', 'qa/sound-issue-runner.py': 'fixture'}, 'normal': {'path': 'qa/issue-audio-delivery/all-sound-settings-normal.json', 'sha256': 'fixture'}, 'negative_source_sha256': 'fixture'}
        self.profile['project'] = str(self.project)
        for rel in self.profile['native_sha256']:
            p = self.native / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('exports.reviewed = ' + json.dumps(rel) + ';')
            self.profile['native_sha256'][rel] = sha(p)
        for rel in self.profile['producer_sha256']:
            p = self.project / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('synthetic producer ' + rel)
            self.profile['producer_sha256'][rel] = sha(p)
        self.negative = self.qa / 'original-native/assets/main/index.js'
        self.negative.parent.mkdir(parents=True)
        self.negative.write_text('exports.originalOffBug=true;')
        self.profile['negative_source_sha256'] = sha(self.negative)
        self.business = self.native / 'assets/main/index.js'
        self.web = self.project / 'preview/assets/main/index.js'
        self.web.parent.mkdir(parents=True)
        self.web.write_bytes(self.business.read_bytes())
        cases = [{'name': name, 'pass': True} for name in sound.UNIT_CASES]
        normal = {'observed': {'all_sound_contract_cases_pass': True, 'cases': cases},
                  'runner': {'sha256': self.profile['producer_sha256']['qa/sound-issue-runner.py']},
                  'case': 'all-sound-settings', 'harness_error': False,
                  'artifacts': {'assets/main/index.js': {'path': str(self.business), 'sha256': sha(self.business)}}}
        n = self.project / self.profile['normal']['path']
        n.parent.mkdir(parents=True, exist_ok=True)
        n.write_text(json.dumps(normal))
        self.profile['normal']['sha256'] = sha(n)
        self.state = {'display': [100, 100], 'gain': [1, 1], 'levels': [10, 10], 'on': [True, True]}
        rows = []
        for category, j in [('music', 0), ('sfx', 1)]:
            steps = [('decrement-'+str(i), (i-1)*10) for i in range(10, 0, -1)]
            steps += [('lower-bound', 0)] + [('increment-'+str(i), i*10) for i in range(1, 11)]
            steps += [('upper-bound', 100)] + [('select-'+str(i), (i+1)*10) for i in range(10)]
            steps += [('off-zero', 0), ('restore-half', 50), ('off-plus-ten', 10), ('zero-on-restore', 10)]
            for name, level in steps:
                self.state['display'][j] = level
                self.state['gain'][j] = level / 100
                self.state['levels'][j] = level // 10
                self.state['on'][j] = level > 0
                rows.append({'category': category, 'name': name, 'expected': level, 'observed': copy.deepcopy(self.state)})
        self.data = {'ui': {'pass': True, 'rows': rows},
                     'unit': {'file': str(self.business), 'pass': True, 'cases': copy.deepcopy(cases)},
                     'negative': {'file': str(self.negative), 'pass': False, 'cases': copy.deepcopy(cases)}}
        self.data['negative']['cases'][0]['pass'] = False
        pcm = []
        for label in ['music_full', 'music_half', 'music_zero', 'sfx_full', 'sfx_half', 'sfx_zero', 'sfx_off', 'both_zero', 'music_off', 'music_on']:
            value = 0 if label.endswith(('zero', 'off')) else .5 if label.endswith('half') else 1
            pcm.append({'label': label, 'maxRms': value, 'windowPeak': value,
                        'pcm': [-value, value], 'sampleRate': 48000, 'state': 'running'})
        self.data['pcm'] = {'runs': pcm}
        self.trace = self.qa / 'sound-trace.json'
        self.patch = patch.object(sound, 'PROFILE', self.profile)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def save(self):
        trace = {'schema': 'sound_settings_trace.v1', 'native_sha256': {'assets/main/index.js': sha(self.business)},
                 'web_equivalent': {'assets/main/index.js': str(self.web)}}
        for name, value in self.data.items():
            p = self.qa / (name + '.json')
            p.write_text(json.dumps(value))
            trace[name] = {'path': p.name, 'sha256': sha(p)}
        self.trace.write_text(json.dumps(trace))
        return trace

    def call(self):
        self.save()
        return interaction.audit(self.trace, self.native)

    def test_registered_normal_passes(self):
        self.assertTrue(self.call()['passed'])

    def test_empty_current_cases_refused(self):
        self.data['unit']['cases'] = []
        self.assertFalse(self.call()['passed'])

    def test_current_failed_case_refused(self):
        self.data['unit']['cases'][1]['pass'] = False
        self.assertFalse(self.call()['passed'])

    def test_wrong_case_coverage_refused(self):
        self.data['unit']['cases'][0]['name'] = 'unrelated test'
        self.assertFalse(self.call()['passed'])

    def test_old_control_must_reproduce_original_defect(self):
        self.data['negative']['cases'][0]['pass'] = True
        self.assertFalse(self.call()['passed'])

    def test_other_bus_mutation_refused(self):
        o = self.data['ui']['rows'][4]['observed']
        o['display'][1], o['gain'][1], o['levels'][1] = 20, .2, 2
        self.assertFalse(self.call()['passed'])

    def test_on_off_display_mismatch_refused(self):
        self.data['ui']['rows'][0]['observed']['on'][0] = False
        self.assertFalse(self.call()['passed'])

    def test_missing_web_equivalent_refused(self):
        trace = self.save()
        trace['web_equivalent'] = {}
        self.trace.write_text(json.dumps(trace))
        self.assertFalse(interaction.audit(self.trace, self.native)['passed'])

    def test_native_source_drift_refused_even_with_updated_trace_hash(self):
        self.business.write_text('exports.changed=true;')
        self.web.write_bytes(self.business.read_bytes())
        self.assertFalse(self.call()['passed'])

    def test_producer_drift_refused(self):
        (self.project / 'qa/g7-ui.mjs').write_text('changed producer')
        self.assertFalse(self.call()['passed'])

    def test_same_native_bytes_other_project_cannot_opt_in_by_schema(self):
        self.save()
        elsewhere = Path(self.temp.name) / 'unrelated.json'
        elsewhere.write_bytes(self.trace.read_bytes())
        self.assertFalse(interaction.audit(elsewhere, self.native)['passed'])

    def test_missing_normal_control_refused(self):
        (self.project / self.profile['normal']['path']).unlink()
        self.assertFalse(self.call()['passed'])

    def test_raw_tamper_refused(self):
        self.save()
        (self.qa / 'unit.json').write_text('{}')
        self.assertFalse(interaction.audit(self.trace, self.native)['passed'])

    def test_nan_pcm_refused(self):
        self.data['pcm']['runs'][0]['maxRms'] = float('nan')
        self.assertFalse(self.call()['passed'])

    def test_negative_muted_energy_refused(self):
        self.data['pcm']['runs'][2]['maxRms'] = -1
        self.assertFalse(self.call()['passed'])

    def test_pcm_summary_without_samples_refused(self):
        self.data['pcm']['runs'][0]['pcm'] = []
        self.assertFalse(self.call()['passed'])

    def test_pcm_samples_contradict_audible_summary_refused(self):
        self.data['pcm']['runs'][0]['pcm'] = [0, 0]
        self.assertFalse(self.call()['passed'])

    def test_missing_independent_both_zero_output_refused(self):
        self.data['pcm']['runs'] = [row for row in self.data['pcm']['runs'] if row['label'] != 'both_zero']
        self.assertFalse(self.call()['passed'])

    def test_both_zero_nonzero_max_rms_refused(self):
        row = next(row for row in self.data['pcm']['runs'] if row['label'] == 'both_zero')
        row['maxRms'] = .001
        row['pcm'] = [.001, -.001]
        self.assertFalse(self.call()['passed'])

    def test_default_raw_reference_cannot_leave_trace_parent(self):
        trace = self.save()
        sibling = self.project / 'unit-outside-trace-parent.json'
        sibling.write_bytes((self.qa / 'unit.json').read_bytes())
        trace['unit'] = {'path': '../' + sibling.name, 'sha256': sha(sibling)}
        self.trace.write_text(json.dumps(trace))
        self.assertFalse(interaction.audit(self.trace, self.native)['passed'])

    def test_fixed_normal_control_uses_explicit_project_base(self):
        original = self.project / self.profile['normal']['path']
        sibling = self.project / 'registered-normal.json'
        sibling.write_bytes(original.read_bytes())
        self.profile['normal']['path'] = sibling.name
        self.assertTrue(self.call()['passed'])

    def test_zero_denominator_refused_without_crash(self):
        self.data['pcm']['runs'][0]['maxRms'] = 0
        self.assertFalse(self.call()['passed'])

    def test_private_names_and_count_not_weakened(self):
        self.data['ui']['rows'] = self.data['ui']['rows'][:11]
        self.assertFalse(self.call()['passed'])


class WriterScope(unittest.TestCase):
    setUp = package_fixtures.EntryPoints.setUp
    tearDown = package_fixtures.EntryPoints.tearDown
    setup_package = package_fixtures.EntryPoints.setup_package

    def test_unregistered_sound_schema_stops_writer_before_runtime_and_no_zip(self):
        manifest = self.setup_package()
        trace = self.root / 'sound.json'
        trace.write_text('{"schema":"sound_settings_trace.v1"}')
        out = self.root / 'no-output.zip'
        with patch('build_checked_zip.audit_final_startup') as runtime:
            with self.assertRaisesRegex(ValueError, 'unregistered sound-only evidence scope'):
                package_fixtures.build(self.native, 'test-target', out,
                    resource_manifest=manifest, project=self.project, interaction_audio_trace=trace)
            runtime.assert_not_called()
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
