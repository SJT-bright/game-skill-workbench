"""Shared-gate integration fixtures; callback successes are NOT visual evidence.

Use the real six-family auditor and lightweight art record. Synthetic source,
runtime traces and callback scope isolate package/refusal decisions only.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SharedGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ad-six-gate-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.bundle = Path(self.tmp.name) / 'skills'
        scripts = self.bundle / 'remake-core/scripts'
        scripts.mkdir(parents=True)
        for name in ('ad_nodes_gate.py', 'art_check_record.py'):
            shutil.copy2(HERE / name, scripts / name)
        self.ad_scripts = self.bundle / 'ad-boost/scripts'
        self.ad_scripts.mkdir(parents=True)
        for name in ('ad_nodes.py', 'ad_node_policy.json'):
            shutil.copy2(SKILLS / 'ad-boost/scripts' / name, self.ad_scripts / name)
        fixture_path = SKILLS / 'ad-boost/scripts/tests/test_ad_nodes.py'
        fixture = load(fixture_path, 'ad_six_node_test_fixture')
        self.fixture = fixture.Nodes()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.project = self.fixture.root
        self.gate = load(scripts / 'ad_nodes_gate.py', 'ad_six_package_gate_fixture')
        self.manifest = self.fixture.manifest
        self.native = self.project / 'build/native'
        self.native.mkdir(parents=True)
        (self.native / 'game.js').write_text('startRealGameFixture();')
        self.configure_ui()
        self.configure_prepare_context()
        self.persist()

    def write(self, rel, value):
        path = self.project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value))
        return {'path': rel, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def configure_ui(self):
        for name in ('build/web', 'docs/test/ad-dumps'):
            (self.project / name).mkdir(parents=True)
        self.write('docs/art/first-piece.json', {'tool': 'art_production_preflight', 'passed': True,
                                                'scope': 'synthetic callback isolation, not UI approval'})
        self.manifest['ui'] = dict(web_export='build/web', dumps='docs/test/ad-dumps',
                                   first_piece_report='docs/art/first-piece.json')
        self.pages, self.visual, self.capture = [], {'cases': []}, {'cases': []}
        for node in self.manifest['nodes']:
            kind = node['kind']
            node['ui'] = {'page_ids': [kind], 'visual_case_ids': []}
            self.pages.append(dict(id=kind, name=kind, kind='home' if kind == 'home' else 'popup',
                                   close='Canvas/Close', ad_entries=[dict(e, role=e['role']) for e in node['entries']]))
            for width, height in ((375, 667), (390, 844)):
                vid = kind + '-' + str(width)
                node['ui']['visual_case_ids'].append(vid)
                self.visual['cases'].append(dict(id=vid, screen=kind, viewport_width=width, viewport_height=height))
                self.capture['cases'].append(dict(id='capture-' + vid, screen=kind, width=width, height=height))
        self.save_ui()
        self.write('.tiktok-kit/art-check-record.json', dict(kind='art-check-record', schema=1, board='localize',
                   first_full_pass={'time': 'fixture-prior-full-pass'},
                   last={'status': 'pass', 'scoped': ['new-advertisement-pages']}))

    def save_ui(self):
        self.write('docs/logic/pages.json', dict(schema='pages.v1', pages=self.pages))
        sha = hashlib.sha256((self.project / 'docs/logic/pages.json').read_bytes()).hexdigest()
        self.write('docs/art/screens.json', {'pages_sha256': sha, 'screens': [dict(id=p['id']) for p in self.pages]})
        self.write('docs/art/visual-slots.json', self.visual)
        self.write('docs/art/capture-plan.json', self.capture)

    def configure_prepare_context(self):
        art_root = self.bundle / 'remake-art'
        documents = []
        for relative in self.gate.ART_INSTRUCTIONS:
            path = art_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SKILLS / 'remake-art' / relative, path)
            documents.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        style = self.write('ART_DIRECTION.md', 'Synthetic gate fixture style; not a produced game UI.')
        context = {'schema': 'adboost_art_context.v1', 'context_ready': True, 'problems': [], 'board': 'remake',
                   'project': str(self.project), 'remake_art': {'root': str(art_root)}, 'documents': documents,
                   'style_sources': [{'kind': 'art_direction', 'path': str(self.project / style['path']),
                                      'sha256': style['sha256']}],
                   'scope': 'synthetic gate fixture only, never visual proof'}
        self.manifest['ui']['production_context'] = self.write('docs/art/ad-production-context.json', context)

    def persist(self):
        self.write('docs/adboost/ad_nodes.json', self.manifest)
        runtime = self.fixture.receipt()
        runtime['build_directory'] = 'build/native'
        runtime['build_artifacts'] = [{'path': 'build/native/game.js',
                                       'sha256': hashlib.sha256((self.native / 'game.js').read_bytes()).hexdigest()}]
        self.write('qa/ad-nodes-runtime.json', runtime)
        return runtime

    @staticmethod
    def synthetic_ui_callback(project, *, manifest, stage, ui):
        return {'passed': True, 'problems': [], 'checked_visual_case_ids': ui['required_visual_case_ids'],
                'scope': 'synthetic tool fixture, not actual UI/visual proof'}

    def check(self, **kwargs):
        kwargs.setdefault('native', self.native)
        kwargs.setdefault('art_stage_check', self.synthetic_ui_callback)
        return self.gate.check_project(self.project, **kwargs)

    def assert_refused(self, text=None, **kwargs):
        result = self.check(**kwargs)
        self.assertFalse(result['passed'], result)
        self.assertTrue(result['problems'])
        if text:
            self.assertIn(text, ' '.join(result['problems']))
        return result

    def test_six_standard_plus_two_extensions_keeps_standard_count_six(self):
        self.fixture.add_node('offline')
        self.fixture.add_node('quest')
        self.persist()
        result = self.check()
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['ad_nodes']['standard_count'], 6)
        self.assertEqual(result['ad_nodes']['extra_count'], 2)
        self.assertEqual(result['native_binding']['matched_members'], ['game.js'])

    def test_each_missing_standard_node_is_refused(self):
        original = copy.deepcopy(self.manifest['nodes'])
        for kind in self.gate.STANDARD:
            with self.subTest(kind=kind):
                self.manifest['nodes'] = [n for n in original if n['kind'] != kind]
                self.persist()
                self.assert_refused('strict standard six')

    def test_missing_same_bundle_tool_never_uses_an_installed_fallback(self):
        (self.ad_scripts / 'ad_nodes.py').unlink()
        self.assert_refused('required same-bundle tool missing')

    def test_bare_pass_and_fake_count_do_not_replace_nodes(self):
        self.manifest.update(nodes=[], standard_count=6, count=6, passed=True)
        self.persist()
        self.assert_refused('strict standard six')

    def test_bad_or_duplicate_json_fails_closed(self):
        self.write('docs/adboost/ad_nodes.json', '{"nodes":[],"nodes":[]}')
        self.assert_refused('duplicate JSON key')

    def test_runtime_directory_must_match_the_actual_writer_native(self):
        other = self.project / 'build/other-native'
        other.mkdir()
        shutil.copy2(self.native / 'game.js', other / 'game.js')
        self.assert_refused('not the Native selected', native=other)

    def test_exact_package_members_must_match_the_runtime_hashes(self):
        self.assert_refused('differs from exact package member', native=None, files={'game.js': b'oldBuild();'})
        result = self.check(native=None, files={'game.js': (self.native / 'game.js').read_bytes()})
        self.assertTrue(result['passed'], result)

    def test_missing_build_directory_and_outside_artifact_fail(self):
        runtime = self.persist()
        del runtime['build_directory']
        self.write('qa/ad-nodes-runtime.json', runtime)
        self.assert_refused('expected project-relative POSIX path')
        runtime = self.persist()
        runtime['build_artifacts'] = [self.write('qa/mock-build.js', 'fake();')]
        self.write('qa/ad-nodes-runtime.json', runtime)
        self.assert_refused('outside declared Native')

    def test_only_engine_or_adapter_artifacts_cannot_prove_actual_game_js(self):
        runtime = self.persist()
        runtime['build_artifacts'] = [self.write('build/native/engine-adapter.js', 'adapter();')]
        self.write('qa/ad-nodes-runtime.json', runtime)
        self.assert_refused('at least one actual game build JS')

    def test_old_source_hash_refuses_writer(self):
        entry = self.manifest['nodes'][0]['entries'][0]
        path = self.project / entry['evidence'][0]['path']
        path.write_text(path.read_text() + '\nsourceChanged();')
        self.assert_refused('strict standard six')

    def test_trial_allows_current_wiring_with_old_runtime_but_writer_refuses_it(self):
        self.write('qa/ad-nodes-runtime.json', {'schema': 'old-runtime', 'passed': True})
        result = self.check(stage='trial')
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['ad_nodes']['standard_count_runtime'], 0)
        self.assertIsNone(result['native_binding'])
        self.assert_refused('strict standard six')

    def test_missing_or_failed_lightweight_art_record_refuses(self):
        (self.project / '.tiktok-kit/art-check-record.json').unlink()
        self.assert_refused('lightweight art check blocks')
        self.write('.tiktok-kit/art-check-record.json', dict(kind='art-check-record', schema=1,
                   last={'status': 'fail', 'scoped': ['new-ad-ui'], 'blocking_rows': ['overlap']}))
        self.assert_refused('lightweight art check blocks')

    def formal_trial_owner(self):
        """Actual owner when bundled; explicit resolver protocol fixture otherwise.

        The production remake tree has no English owner and therefore does not
        recognize an English trial log. Only the isolated sandbox gets this
        resolver fixture to exercise the future same-bundle log protocol.
        """
        relative = Path('cocos-game-to-english/scripts/chinese_audit.py')
        target = self.bundle / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if (SKILLS / relative).is_file():
            shutil.copy2(SKILLS / relative, target)
        else:
            target.write_text('from pathlib import Path\n'
                'def resolve_out(project, out):\n'
                '    return Path(out).resolve() if out else (Path(project) / "docs/english/chinese-audit").resolve()\n')
        owner = self.gate._module(target)
        return Path(owner.resolve_out(self.project, None)) / 'trial-links.json'

    def test_earlier_trial_is_false_without_the_owning_formal_log(self):
        log = self.formal_trial_owner()
        self.assertFalse(log.exists())
        self.assertFalse(self.gate._earlier_formal_trial(self.project))
        # An unrelated hand-written status does not activate legacy art reuse.
        self.write('.tiktok-kit/earlier-trial.json', {'passed': True, 'draft': False})
        self.assertFalse(self.gate._earlier_formal_trial(self.project))

    def test_completed_owning_trial_preserves_scoped_art_without_full_recheck(self):
        log = self.formal_trial_owner()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(json.dumps([{'passed': True, 'draft': False,
            'snapshot': '/cleaned-up-prior-preview/snapshot', 'native_tree_sha256': 'a' * 64,
            'snapshot_manifest_sha256': 'b' * 64, 'export_manifest_sha256': 'b' * 64, 'open_problems': 0}]))
        self.assertTrue(self.gate._earlier_formal_trial(self.project))
        (self.project / '.tiktok-kit/art-check-record.json').unlink()
        result = self.check()
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['art']['level'], 'warn')
        self.assertTrue(result['ui']['check']['checked_visual_case_ids'])
        # A previous trial only reuses the prior full-run boundary. New affected
        # UI still has to pass its current scoped checker.
        self.assert_refused('required same-bundle tool missing', art_stage_check=None)

    def test_fake_draft_unfinished_or_inconsistent_trial_rows_are_not_prior_passes(self):
        log = self.formal_trial_owner()
        log.parent.mkdir(parents=True, exist_ok=True)
        good = {'passed': True, 'draft': False, 'snapshot': '/prior/snapshot', 'native_tree_sha256': 'a' * 64}
        variants = [dict(good, passed='true'), dict(good, passed=False), dict(good, draft=True),
                    dict(good, snapshot=True), dict(good, snapshot=' '), dict(good, native_tree_sha256='bad'),
                    dict(good, open_problems=1), dict(good, snapshot_manifest_sha256='a' * 64,
                                                     export_manifest_sha256='b' * 64),
                    {'passed': True, 'draft': False}]
        for row in variants:
            with self.subTest(row=row):
                log.write_text(json.dumps([row]))
                self.assertFalse(self.gate._earlier_formal_trial(self.project))
        log.write_text(json.dumps({'passed': True, 'draft': False}))
        self.assertFalse(self.gate._earlier_formal_trial(self.project))

    def test_ad_entry_page_and_visual_registration_are_required(self):
        self.pages[0]['ad_entries'] = []
        self.save_ui()
        self.assert_refused('button/role is not registered')
        self.pages[0]['ad_entries'] = self.manifest['nodes'][0]['entries']
        self.visual['cases'].pop(0)
        self.save_ui()
        self.assert_refused('visual case is missing')

    def test_changed_screens_registry_and_ambiguous_capture_mapping_fail(self):
        self.write('docs/art/screens.json', {'pages_sha256': 'old', 'screens': []})
        self.assert_refused('not derived from the current page registry')
        self.save_ui()
        self.capture['cases'].append(dict(self.capture['cases'][0], id='other-same-viewport'))
        self.save_ui()
        self.assert_refused('unambiguous capture mapping')

    def test_no_checker_or_incomplete_affected_case_coverage_is_not_a_visual_pass(self):
        self.assert_refused('required same-bundle tool missing', art_stage_check=None)
        def incomplete(project, **kwargs):
            return {'passed': True, 'problems': [], 'checked_visual_case_ids': []}
        self.assert_refused('scoped art/capture', art_stage_check=incomplete)

    def test_prepare_context_is_checked_but_never_replaces_scoped_ui_check(self):
        art_root = self.bundle / 'remake-art'
        self.assertTrue(self.check()['passed'])
        self.assert_refused('required same-bundle tool missing', art_stage_check=None)
        (art_root / 'SKILL.md').write_text('changed art instructions')
        self.assert_refused('owning art instructions changed')

    def test_missing_or_one_document_prepare_context_cannot_pass(self):
        del self.manifest['ui']['production_context']
        self.persist()
        self.assert_refused('production_context from the owning art Skill is required')
        self.configure_prepare_context()
        context = json.loads((self.project / 'docs/art/ad-production-context.json').read_text())
        context['documents'] = context['documents'][:1]
        self.manifest['ui']['production_context'] = self.write('docs/art/ad-production-context.json', context)
        self.persist()
        self.assert_refused('omitted owning art instructions')

    def test_preparation_needs_a_real_current_style_source(self):
        context_path = self.project / 'docs/art/ad-production-context.json'
        context = json.loads(context_path.read_text())
        context['style_sources'] = []
        self.manifest['ui']['production_context'] = self.write('docs/art/ad-production-context.json', context)
        self.persist()
        self.assert_refused('no real game style reference')
        self.configure_prepare_context()
        context = json.loads(context_path.read_text())
        # A document cannot stand in for a decoded original-game image.
        context['board'] = 'localize'
        context['style_sources'][0].update(kind='original_reference', pixels=[390, 844])
        self.manifest['ui']['production_context'] = self.write('docs/art/ad-production-context.json', context)
        self.persist()
        self.assert_refused('cannot identify image file')


if __name__ == '__main__':
    unittest.main()
