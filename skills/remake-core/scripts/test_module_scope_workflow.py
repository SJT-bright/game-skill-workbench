"""Strictly offline end-to-end module ownership and scoped-plan fixtures.

All bytes, ZIPs, SQLite records and frozen observations live in TemporaryDirectory.
Only gate._observe is mocked; its fixture implementation calls real Ledger.prepare
under real module_sources. The bundle starts with a throw and is parsed, never run.
"""
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import bundle_module_inputs as modules
import check_ledger as CL
import regression_scope_gate as gate


BUNDLE = 'assets/main/index.js'
SKIN = 'runtime.skin/visible'
AUDIO = 'runtime.audio/toggle'
STABLE = 'runtime.independent/unchanged'
ENVELOPE = 'runtime.bundle/loader'
BOOTSTRAP = 'runtime.bootstrap/entry'


def bundle(*, skin=1, audio=2, hidden=3, envelope=''):
    return ('throw new Error("OFFLINE FIXTURE MUST NEVER EXECUTE");\n'
            'window.__require=function(t,n,r){return t;}({'
            'Skin:[function(require,module,exports){module.exports=' + str(skin) + ';},{}],'
            'Audio:[function(require,module,exports){module.exports=' + str(audio) + ';},{}],'
            'Hidden:[function(require,module,exports){module.exports=' + str(hidden) + ';},{}]'
            '},{},["Skin"]);' + envelope).encode()


class ModuleScopeWorkflowTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix='module-scope-offline-')
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name).resolve()
        self.old = {'game.js': b'/* synthetic boot, never executed */',
                    BUNDLE: bundle(), 'stable.bin': b'independent unchanged observation'}
        self.current = dict(self.old, **{BUNDLE: bundle(skin=9)})
        self.archive = self.project / 'synthetic-old.zip'
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, raw in self.old.items():
                archive.writestr(name, raw)
        self.adapter = self.project / 'synthetic-adapter.json'
        self.adapter.write_text('{}')
        self.store = CL.Ledger(self.project)
        self.addCleanup(self.store.close)
        self.scope_path = self.project / 'docs/checks/check-inputs.json'
        self.checks = {
            SKIN: {'basis': 'fixture Skin factory is the skin consumer',
                   'inputs': {'modules': [modules.module_key(BUNDLE, 'Skin')]}},
            AUDIO: {'basis': 'fixture Audio factory is an independent audio consumer',
                    'inputs': {'modules': [modules.module_key(BUNDLE, 'Audio')]}},
            STABLE: {'basis': 'independent fixture observation outside the shared bundle',
                     'inputs': {'package': ['stable.bin']}},
        }

    def roots(self, files):
        return {'package': gate.package_manifest(files), 'adapter': CL.json_manifest({})}

    def seed_old_observations(self, *, envelope=False, envelope_marker=True):
        if envelope:
            self.checks[ENVELOPE] = {
                'basis': 'independent fixture loader observation for exactly this shared bundle',
                'inputs': {'package': [BUNDLE]},
                **({'module_envelope': BUNDLE} if envelope_marker else {}),
            }
        # Older real rows deliberately predate module manifests and declarations.
        self.assertFalse(self.scope_path.exists())
        for cid in self.checks:
            plan = self.store.prepare(cid, self.roots(self.old), {'fixture': True}, 'fixture-rule')
            self.assertEqual(plan['action'], 'run')
            original = self.project / (cid.replace('/', '-') + '-observation.json')
            original.write_text(json.dumps({'real_fixture_observation': cid, 'passed': True}))
            with redirect_stderr(io.StringIO()):
                self.store.execute(plan, lambda: {'passed': True, 'raw_files': [str(original)]},
                                   lambda result: result['passed'])
            record = self.store.previous(cid)[0]
            self.assertNotIn('modules', record['roots'])
            self.assertTrue(record['files'])
        self.write_scope()
        return self.records_snapshot()

    def write_scope(self):
        self.scope_path.write_text(json.dumps({'schema': CL.SCOPE_SCHEMA, 'checks': self.checks}))

    def records_snapshot(self):
        return self.store.db.execute('SELECT key, data FROM records ORDER BY key').fetchall()

    def observe(self, project, files, adapter, board, policy, prior_files=None):
        self.assertEqual(Path(project), self.project)
        self.assertEqual(Path(adapter), self.adapter)
        self.assertEqual((board, policy), ('localize', 'new'))
        self.assertEqual(prior_files, self.old)
        with CL.module_sources(files, prior_files):
            rows = [self.store.prepare(cid, self.roots(files), {'fixture': True}, 'fixture-rule')
                    for cid in self.checks]
        return {'ads': [], 'runtime': rows}

    def groups(self):
        return self.observe(self.project, self.current, self.adapter, 'localize', 'new', self.old)

    def create(self, proposed):
        with patch.object(gate, '_observe', side_effect=self.observe) as observed:
            result = gate.create_plan(self.project, self.current, self.adapter, board='localize', policy='new',
                                      prior=self.archive, mode='scoped', proposed=proposed)
        observed.assert_called_once()
        return result

    def repair(self, proposed):
        with patch.object(gate, '_observe', side_effect=self.observe):
            return gate.repair_report(self.project, self.current, self.adapter, board='localize', policy='new',
                                      prior=self.archive, mode='scoped', proposed=proposed)

    def baseline(self):
        return {'path': str(self.archive), 'sha256': gate.digest(self.archive)}

    def test_old_package_only_records_project_to_modules_without_rewriting_evidence(self):
        original_records = self.seed_old_observations()
        groups = self.groups()
        rows = {row['check_id']: row for row in groups['runtime']}
        self.assertEqual(rows[SKIN]['action'], 'run')
        self.assertEqual(rows[AUDIO]['action'], 'reuse')
        self.assertEqual(rows[STABLE]['action'], 'reuse')
        audio = self.store.previous(AUDIO)[0]
        self.assertEqual(rows[AUDIO]['record'], audio)
        self.assertNotIn('modules', audio['roots'])
        self.assertEqual(rows[AUDIO]['record']['executed_at'], audio['executed_at'])
        for file in audio['files']:
            self.assertEqual(CL.sha(Path(file['path']).read_bytes()), file['sha256'])
        approved = {SKIN: 'only the synthetic Skin factory changed'}
        self.assertEqual(gate.module_ownership(rows, approved, self.baseline(), self.current), ({BUNDLE}, set()))
        gate._check_impact(self.project, groups, approved, 'scoped', self.baseline(), self.current)
        plan = self.create(approved)
        self.assertEqual(plan['mode'], 'scoped')
        self.assertEqual(plan['baseline']['type'], 'evidence_recovery')
        self.assertFalse(plan['baseline']['old_official_pass_claimed'])
        self.assertEqual({cid for cid, row in plan['actions']['runtime'].items() if row['action'] == 'run'}, {SKIN})
        self.assertEqual(plan['actions']['runtime'][AUDIO]['action'], 'reuse')
        self.assertEqual(original_records, self.records_snapshot())
        self.assertFalse(Path(str(self.archive) + '.receipt.json').exists())

    def test_real_envelope_node_and_all_real_consumers_can_continue(self):
        original_records = self.seed_old_observations(envelope=True)
        self.current = dict(self.old, **{BUNDLE: bundle(envelope='\n/* actual wrapper-byte change */')})
        groups = self.groups()
        rows = {row['check_id']: row for row in groups['runtime']}
        self.assertEqual({cid: row['action'] for cid, row in rows.items()},
                         {SKIN: 'run', AUDIO: 'run', STABLE: 'reuse', ENVELOPE: 'run'})
        approved = {SKIN: 'Skin consumes changed shared loader envelope',
                    AUDIO: 'Audio consumes changed shared loader envelope',
                    ENVELOPE: 'the exact shared loader envelope changed'}
        self.assertEqual(gate.module_ownership(rows, approved, self.baseline(), self.current), ({BUNDLE}, {ENVELOPE}))
        gate._check_impact(self.project, groups, approved, 'scoped', self.baseline(), self.current)
        plan = self.create(approved)
        self.assertEqual({cid for cid, row in plan['actions']['runtime'].items() if row['action'] == 'run'}, set(approved))
        self.assertEqual(plan['actions']['runtime'][STABLE]['action'], 'reuse')
        self.assertEqual(original_records, self.records_snapshot())

    def test_package_owner_prose_cannot_replace_an_exact_envelope_node(self):
        self.seed_old_observations(envelope=True, envelope_marker=False)
        self.current = dict(self.old, **{BUNDLE: bundle(envelope='\n/* actual wrapper-byte change */')})
        groups = self.groups()
        rows = {row['check_id']: row for row in groups['runtime']}
        approved = {SKIN: 'wrapper affects Skin', AUDIO: 'wrapper affects Audio', ENVELOPE: 'claims wrapper ownership'}
        with self.assertRaisesRegex(CL.NeedsScope, '精确独立节点.*' + BUNDLE):
            gate.module_ownership(rows, approved, self.baseline(), self.current)
        report, plan = self.repair(approved)
        self.assertIsNone(plan)
        self.assertEqual(report['status'], 'repair_required')
        self.assertFalse(report['task_terminal'])
        self.assertEqual(report['browser_launches'], 0)
        self.assertTrue(any('精确独立节点' in issue['reason'] for issue in report['issues']))

    def test_envelope_cannot_continue_without_approval_of_each_real_consumer(self):
        self.seed_old_observations(envelope=True)
        self.current = dict(self.old, **{BUNDLE: bundle(envelope='\n/* actual wrapper-byte change */')})
        approved = {SKIN: 'wrapper affects Skin', ENVELOPE: 'exact wrapper check'}
        report, plan = self.repair(approved)
        self.assertIsNone(plan)
        self.assertEqual(report['status'], 'repair_required')
        reasons = ' '.join(issue['reason'] for issue in report['issues'])
        self.assertIn('真实模块消费者', reasons)
        self.assertIn(AUDIO, reasons, 'a consumer gap must name the missing independent check ID')
        self.assertEqual(report['browser_launches'], 0)

    def test_unmapped_factory_change_reports_the_actual_module_without_full_fallback(self):
        self.seed_old_observations()
        self.current = dict(self.old, **{BUNDLE: bundle(hidden=99)})
        groups = self.groups()
        rows = {row['check_id']: row for row in groups['runtime']}
        self.assertEqual(rows[SKIN]['action'], 'needs_scope')
        self.assertEqual(rows[AUDIO]['action'], 'needs_scope')
        with self.assertRaisesRegex(CL.NeedsScope, '真实模块变化缺少检查归属.*Hidden'):
            gate.module_ownership(rows, {SKIN: 'prose does not own Hidden'}, self.baseline(), self.current)
        report, plan = self.repair({SKIN: 'prose does not own Hidden'})
        self.assertIsNone(plan)
        self.assertEqual(report['status'], 'repair_required')
        self.assertEqual(report['browser_launches'], 0)
        self.assertTrue(any('Hidden' in issue['reason'] for issue in report['issues']))

    def test_unknown_bundle_format_is_an_input_repair_with_no_execution_fallback(self):
        self.seed_old_observations()
        valid_rows = {row['check_id']: row for row in self.groups()['runtime']}
        self.current = dict(self.old, **{BUNDLE: b'System.register("synthetic",[],function(){return {execute:function(){}};});'})
        with self.assertRaisesRegex(CL.NeedsScope, '实际模块格式或原字节.*' + BUNDLE):
            gate.module_ownership(valid_rows, {}, self.baseline(), self.current)
        report, plan = self.repair({SKIN: 'unsupported bytes cannot authorize a run'})
        self.assertIsNone(plan)
        self.assertEqual(report['status'], 'repair_required')
        self.assertEqual(report['browser_launches'], 0)
        self.assertTrue(any('System.register' in issue['reason'] for issue in report['issues']))

    def test_missing_old_raw_bundle_bytes_cannot_project_a_package_hash(self):
        original_records = self.seed_old_observations()
        with CL.module_sources(self.current), self.assertRaisesRegex(CL.NeedsScope, '原字节缺失|SHA-256 不符'):
            self.store.prepare(AUDIO, self.roots(self.current), {'fixture': True}, 'fixture-rule')
        self.assertEqual(original_records, self.records_snapshot())
        # Giving the actual old ZIP bytes restores the same historical row.
        with CL.module_sources(self.current, gate.archive_files(self.archive)):
            audio = self.store.prepare(AUDIO, self.roots(self.current), {'fixture': True}, 'fixture-rule')
        self.assertEqual(audio['action'], 'reuse')
        self.assertNotIn('modules', audio['record']['roots'])

    def test_unmapped_nonbundle_bytes_remain_a_concrete_package_gap(self):
        self.seed_old_observations()
        self.current = dict(self.old, **{'game.js': b'/* another synthetic boot byte */'})
        report, plan = self.repair({SKIN: 'module prose cannot own another package file'})
        self.assertIsNone(plan)
        self.assertEqual(report['status'], 'repair_required')
        self.assertEqual(report['browser_launches'], 0)
        self.assertTrue(any('game.js' in issue['reason'] for issue in report['issues']))

    def test_mapped_bootstrap_and_skin_change_keep_audio_and_stable_observations(self):
        self.checks[BOOTSTRAP] = {'basis': 'the actual ordinary bootstrap bytes are an independent input',
                                  'inputs': {'package': ['game.js']}}
        original_records = self.seed_old_observations()
        self.current = dict(self.current, **{'game.js': b'/* changed synthetic bootstrap, never executed */'})
        groups = self.groups()
        rows = {row['check_id']: row for row in groups['runtime']}
        self.assertEqual({cid: row['action'] for cid, row in rows.items()},
                         {SKIN: 'run', AUDIO: 'reuse', STABLE: 'reuse', BOOTSTRAP: 'run'})
        approved = {SKIN: 'the exact synthetic Skin factory changed',
                    BOOTSTRAP: 'the ordinary bootstrap bytes changed'}
        gate._check_impact(self.project, groups, approved, 'scoped', self.baseline(), self.current)
        plan = self.create(approved)
        self.assertEqual({cid for cid, row in plan['actions']['runtime'].items() if row['action'] == 'run'},
                         {SKIN, BOOTSTRAP})
        self.assertEqual(plan['actions']['runtime'][AUDIO]['action'], 'reuse')
        self.assertEqual(plan['actions']['runtime'][STABLE]['action'], 'reuse')
        self.assertEqual(original_records, self.records_snapshot())


if __name__ == '__main__':
    unittest.main()
