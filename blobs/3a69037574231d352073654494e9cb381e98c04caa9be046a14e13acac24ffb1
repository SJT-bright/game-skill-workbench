"""Preview cache scheduling with the real ledger and isolated actual asset bytes.

No browser/Node, production game, or production record is patched. The callback is
an explicitly synthetic unit executor; its reports cannot establish a game pass.
"""
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import check_ledger as C
import preview_check_once as P


class PreviewInjectedDependencies(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'unit-project'
        self.export = self.root / 'unit-export'
        self.export.mkdir()
        (self.export / 'index.html').write_text('<html>dependency unit fixture</html>')
        (self.export / 'main.js').write_text('/* unchanged unit input; no engine */')
        self.export_before = C.manifest(self.export)
        self.calls = []
        core = Path(C.__file__).resolve().parent
        skills = core.parents[1]
        self.install = self.root / 'isolated-skills'
        self.module = self.install / 'remake-core/scripts/preview_check_once.py'
        self.module.parent.mkdir(parents=True)
        shutil.copy2(P.__file__, self.module)
        dependencies = [core / 'serve_preview.py', core / 'check_ledger.py',
                        core.parent / 'assets/preview-touch-bridge.js',
                        core.parent / 'assets/ad-simulator.js']
        check = skills / 'cocos-game-check/package-check/scripts'
        dependencies += [check / 'runtime_regression.py', check / 'ego_test_page.mjs']
        dependencies += [check / 'runtime_regression' / name for name in (
            'suites/trial_link.mjs', 'suites/trial_link.json', 'lib.mjs',
            'layout_rules.mjs', 'engine_adapter.mjs', 'session.mjs')]
        for source in dependencies:
            target = self.install / source.relative_to(skills)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        self.bridge = self.install / 'remake-core/assets/preview-touch-bridge.js'
        self.simulator = self.install / 'remake-core/assets/ad-simulator.js'
        self.patch = patch.object(P, '__file__', str(self.module))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def run_preview(self, kind, outcome='pass', ad_simulator=False):
        def execute():
            self.calls.append({'kind': kind, 'bridge_sha256': C.sha(self.bridge.read_bytes())})
            raw = self.root / ('unit-' + kind + '.json')
            raw.write_text(json.dumps({'schema': 'preview_dependency_unit_fixture.v1',
                                       'invocations': len(self.calls)}))
            return (outcome, 'synthetic dependency executor',
                    {'summary': {'passed': outcome == 'pass'}, 'raw_files': [str(raw)]})
        return P.run(self.project, kind, self.export, {'ad_simulator': ad_simulator}, execute)

    def count(self, kind):
        return sum(row['kind'] == kind for row in self.calls)

    def records(self, kind):
        with closing(sqlite3.connect(self.project / 'docs/checks/incremental/ledger.sqlite3')) as db:
            return dict(db.execute('SELECT key,data FROM records WHERE check_id=?', ('preview.' + kind,)))

    def change(self, asset):
        asset.write_bytes(asset.read_bytes() + b'\n/* isolated unit dependency changed */\n')

    def test_actual_injected_assets_are_in_the_right_rule_sets(self):
        for kind in ('home', 'ad-response'):
            with self.subTest(kind=kind):
                self.assertIn(self.bridge, P.rule_files(kind))
                self.assertIn(self.bridge, P.rule_files(kind, {'ad_simulator': False}))
                self.assertNotIn(self.simulator, P.rule_files(kind, {'ad_simulator': False}))
                self.assertIn(self.simulator, P.rule_files(kind, {'ad_simulator': True}))

    def test_bridge_change_retries_failed_items_without_rewriting_original_record(self):
        for kind in ('home', 'ad-response'):
            with self.subTest(kind=kind):
                self.assertEqual(self.run_preview(kind, 'block')[0], 'block')
                original = self.records(kind)
                with self.assertRaises(C.NeedsScope):
                    self.run_preview(kind)
                self.assertEqual(self.count(kind), 1)
                self.assertEqual(self.records(kind), original)
                self.change(self.bridge)
                self.assertEqual(self.run_preview(kind)[0], 'pass')
                self.assertEqual(self.count(kind), 2)
                current = self.records(kind)
                self.assertEqual(len(current), 2)
                for key, row in original.items():
                    self.assertEqual(current[key], row)
        self.assertEqual(C.manifest(self.export), self.export_before)

    def test_bridge_change_invalidates_pass_then_unchanged_bytes_reuse(self):
        for kind in ('home', 'ad-response'):
            with self.subTest(kind=kind):
                self.run_preview(kind)
                original = self.records(kind)
                self.assertIn('original_at', self.run_preview(kind)[2])
                self.assertEqual(self.count(kind), 1)
                self.change(self.bridge)
                revised = self.run_preview(kind)
                self.assertNotIn('original_at', revised[2])
                self.assertEqual(self.count(kind), 2)
                self.assertIn('original_at', self.run_preview(kind)[2])
                self.assertEqual(self.count(kind), 2)
                for key, row in original.items():
                    self.assertEqual(self.records(kind)[key], row)
        self.assertEqual(C.manifest(self.export), self.export_before)

    def test_bridge_timestamp_only_does_not_retest(self):
        for kind in ('home', 'ad-response'):
            self.run_preview(kind)
            self.bridge.touch()
            self.assertIn('original_at', self.run_preview(kind)[2])
            self.assertEqual(self.count(kind), 1)

    def test_simulator_change_invalidates_only_when_enabled(self):
        for kind in ('home', 'ad-response'):
            with self.subTest(kind=kind):
                self.run_preview(kind, ad_simulator=False)
                self.change(self.simulator)
                self.assertIn('original_at', self.run_preview(kind, ad_simulator=False)[2])
                self.assertEqual(self.count(kind), 1)
                self.run_preview(kind, ad_simulator=True)
                self.assertEqual(self.count(kind), 2)
                self.change(self.simulator)
                self.assertNotIn('original_at', self.run_preview(kind, ad_simulator=True)[2])
                self.assertEqual(self.count(kind), 3)
                self.assertIn('original_at', self.run_preview(kind, ad_simulator=True)[2])
                self.assertEqual(self.count(kind), 3)

    def test_missing_bridge_refuses_old_pass_without_executing(self):
        for kind in ('home', 'ad-response'):
            self.run_preview(kind)
        self.bridge.unlink()
        for kind in ('home', 'ad-response'):
            with self.assertRaises(C.NeedsScope):
                self.run_preview(kind)
            self.assertEqual(self.count(kind), 1)

    def test_disabled_simulator_is_not_required_but_enabled_missing_refuses(self):
        self.simulator.unlink()
        for kind in ('home', 'ad-response'):
            with self.subTest(kind=kind):
                self.assertEqual(self.run_preview(kind, ad_simulator=False)[0], 'pass')
                with self.assertRaises(C.NeedsScope):
                    self.run_preview(kind, ad_simulator=True)
                self.assertEqual(self.count(kind), 1)

    def test_game_input_change_still_requires_its_scope(self):
        for kind in ('home', 'ad-response'):
            self.run_preview(kind)
        (self.export / 'main.js').write_text('/* deliberately changed unit game input */')
        for kind in ('home', 'ad-response'):
            with self.assertRaises(C.NeedsScope):
                self.run_preview(kind)
            self.assertEqual(self.count(kind), 1)


if __name__ == '__main__':
    unittest.main()
