"""Offline temp-only controls for real bundle-byte dependency scheduling."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_ledger as C
import bundle_module_inputs as B


PATH = 'src/project.js'


def bundle(skin='1', audio='2', *, audio_dep=False, extra='', wrapper=''):
    dep = '{"./Skin":"Skin"}' if audio_dep else '{}'
    request = 'require("./Skin");' if audio_dep else ''
    # The throw is intentional: a static parser must never execute this JS.
    return ('throw new Error("NEVER EXECUTE MOCK PACKAGE");\n'
            'window.__require=function(t,n,r){return t;}({'
            'Skin:[function(require,module,exports){module.exports=' + skin + ';},{}],'
            'Audio:[function(require,module,exports){' + request + 'module.exports=' + audio + ';},' + dep + ']'
            + extra + '},{},["Skin"]);' + wrapper).encode()


def roots(files):
    return {'package': {p: C.sha(raw) for p, raw in files.items()},
            'adapter': {'/skin': 's', '/audio': 'a'}}


def scope(module):
    return {'basis': 'actual mock factory and consumer',
            'inputs': {'modules': [B.module_key(PATH, module)],
                       'adapter': ['/' + module.lower()]}}


class ModuleInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bundle-module-offline-')
        self.project = Path(self.tmp.name)
        self.ledger = C.Ledger(self.project)
        self.old = {PATH: bundle(), 'ordinary.js': b'var ordinary=1;'}
        self.new = dict(self.old, **{PATH: bundle(skin='9')})
    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()
    def declarations(self, *, package_owner=False):
        checks = {'skin': scope('Skin'), 'audio': scope('Audio')}
        if package_owner:
            checks['bundle.wrapper'] = {'basis': 'wrapper consumer', 'inputs': {'package': [PATH]}}
        (self.project/'docs/checks/check-inputs.json').write_text(json.dumps({'schema': C.SCOPE_SCHEMA, 'checks': checks}))
    def plan(self, cid, files):
        return self.ledger.prepare(cid, roots(files), {'mock': True}, 'same-tool')
    def passed(self, plan):
        return self.ledger.execute(plan, lambda: {'passed': True}, lambda row: row['passed'])
    def pair(self, old=None, new=None):
        return (C.expand_module_roots(roots(old or self.old), old or self.old),
                C.expand_module_roots(roots(new or self.new), new or self.new))
    def test_skin_change_only_invalidates_its_factory(self):
        a, b = self.pair()
        self.assertNotEqual(a['modules'][B.module_key(PATH, 'Skin')], b['modules'][B.module_key(PATH, 'Skin')])
        self.assertEqual(a['modules'][B.module_key(PATH, 'Audio')], b['modules'][B.module_key(PATH, 'Audio')])
        self.assertEqual(a['modules'][PATH+'::@envelope'], b['modules'][PATH+'::@envelope'])
        report = C.module_coverage(a, b)
        self.assertTrue(report['covered'])
        self.assertEqual(report['changed_bundles'], [PATH])
        self.assertEqual(report['changed_modules'], [B.module_key(PATH, 'Skin')])
    def test_unrelated_old_full_package_record_is_reused_without_new_execution(self):
        self.passed(self.plan('audio', self.old))
        original = self.ledger.previous('audio')[0]
        self.declarations()
        with C.module_sources(self.new, self.old):
            plan = self.plan('audio', self.new)
            self.assertEqual(plan['action'], 'reuse')
            self.assertEqual(plan['record']['executed_at'], original['executed_at'])
            self.assertEqual(self.plan('skin', self.new)['action'], 'run')
        self.assertNotIn('modules', self.ledger.previous('audio')[0]['roots'])
    def test_new_module_records_reuse_unrelated_and_run_skin(self):
        self.declarations()
        with C.module_sources(self.old):
            self.passed(self.plan('audio', self.old))
            self.passed(self.plan('skin', self.old))
        with C.module_sources(self.new, self.old):
            self.assertEqual(self.plan('audio', self.new)['action'], 'reuse')
            self.assertEqual(self.plan('skin', self.new)['action'], 'run')
    def test_envelope_change_cannot_be_hidden_by_factory_scope(self):
        changed = dict(self.old, **{PATH: bundle(wrapper='\nwindow.newBehavior=true;')})
        a, b = self.pair(new=changed)
        report = C.module_coverage(a, b)
        self.assertFalse(report['covered'])
        self.assertEqual(report['envelope_changed'], [PATH])
        self.declarations()
        with C.module_sources(self.old):
            self.passed(self.plan('audio', self.old))
        with C.module_sources(changed, self.old):
            self.assertEqual(self.plan('audio', changed)['action'], 'needs_scope')
    def test_explicit_wrapper_owner_still_invalidates_all_its_consumers(self):
        self.declarations(package_owner=True)
        with C.module_sources(self.old):
            self.passed(self.plan('audio', self.old))
        changed = dict(self.old, **{PATH: bundle(wrapper='/* wrapper-byte */')})
        with C.module_sources(changed, self.old):
            self.assertEqual(self.plan('audio', changed)['action'], 'run')
    def test_dependency_closure_tracks_real_referenced_factory(self):
        old = {PATH: bundle(audio_dep=True)}
        new = {PATH: bundle(skin='9', audio_dep=True)}
        a, b = self.pair(old, new)
        self.assertNotEqual(a['modules'][B.module_key(PATH, 'Audio')], b['modules'][B.module_key(PATH, 'Audio')])
    def test_dependency_map_bytes_are_not_normalized(self):
        a, b = self.pair(new=dict(self.old, **{PATH: bundle().replace(b'},{}],Audio', b'}, {}],Audio')}))
        self.assertNotEqual(a['modules'][B.module_key(PATH, 'Skin')], b['modules'][B.module_key(PATH, 'Skin')])
    def test_module_added_and_deleted_change_envelope_and_require_owner(self):
        for changed in (bundle(extra=',Extra:[function(r,m,e){m.exports=3;},{}]'),
                        bundle().replace(b'Skin:[function(require,module,exports){module.exports=1;},{}],', b'')):
            with self.subTest(raw=changed[-50:]):
                a, b = self.pair(new={PATH: changed})
                self.assertFalse(C.module_coverage(a, b)['covered'])
                self.assertIn(PATH, C.module_coverage(a, b)['envelope_changed'])
    def test_unknown_cocos3_and_ordinary_js_cannot_supply_fake_modules(self):
        for raw in (b'System.register("x",[],function(){return {setters:[],execute:function(){}};});',
                    b'var Skin={};'):
            files = {PATH: raw}
            a, b = self.pair(new=files)
            report = C.module_coverage(a, b)
            self.assertFalse(report['covered'])
            self.assertIn(PATH, report['unparsed_bundles'])
            with C.module_sources(files), self.assertRaises(C.NeedsScope):
                C.select_inputs(roots(files), scope('Skin'))
    def test_bad_module_selectors_fail_closed(self):
        for selector in ('missing', PATH+'::@source', PATH+'::module/Missing', ''):
            row = scope('Skin');row['inputs']['modules'] = [selector]
            with self.subTest(selector=selector), C.module_sources(self.old), self.assertRaises(C.NeedsScope):
                C.select_inputs(roots(self.old), row)
    def test_whole_modules_wildcard_still_binds_envelope(self):
        row = scope('Skin');row['inputs']['modules'] = [PATH+'::module/*']
        with C.module_sources(self.old):
            selected = C.select_inputs(roots(self.old), row)['modules']
            self.assertIn(PATH+'::@envelope', selected)
            self.assertIn(B.module_key(PATH, 'Audio'), selected)
    def test_no_actual_bytes_or_wrong_bytes_cannot_relabel_old_record(self):
        with self.assertRaises(C.NeedsScope):
            C.select_inputs(roots(self.old), scope('Skin'))
        with C.module_sources(self.new), self.assertRaises(C.NeedsScope):
            C.select_inputs(roots(self.old), scope('Skin'))
    def test_supplied_virtual_manifest_never_overrides_actual_bytes(self):
        fake = dict(roots(self.new), modules=C.expand_module_roots(roots(self.old), self.old)['modules'])
        with C.module_sources(self.new):
            result = C.select_inputs(fake, scope('Skin'))
        with C.module_sources(self.old):
            old = C.select_inputs(roots(self.old), scope('Skin'))
        self.assertNotEqual(result, old)
    def test_missing_old_bundle_prevents_full_package_record_migration(self):
        self.passed(self.plan('audio', self.old));self.declarations()
        with C.module_sources(self.new), self.assertRaises(C.NeedsScope):
            self.plan('audio', self.new)
    def test_modules_are_lazy_for_legacy_and_cocos3_projects(self):
        source = self.project/'does-not-exist'
        with C.module_sources(source), patch.object(B.subprocess, 'run', side_effect=AssertionError('must remain lazy')):
            self.assertEqual(C.select_inputs(roots(self.old), None), roots(self.old))
            self.assertEqual(C.with_module_inputs(roots(self.old), scope={'inputs': {'package': ['*']}}), roots(self.old))
    def test_nested_current_only_context_retains_outer_baseline_bytes(self):
        self.passed(self.plan('audio', self.old));self.declarations()
        with C.module_sources(self.new, self.old):
            with C.module_sources(self.new):
                self.assertEqual(self.plan('audio', self.new)['action'], 'reuse')
    def test_dynamic_and_unresolved_requires_are_unknown(self):
        for factory in (b'module.exports=require(name);', b'module.exports=require("Outside");',
                        b'var alias=require;module.exports=alias("Skin");',
                        b'module.exports=arguments[0]("Skin");', b'eval("require(\'Skin\')");'):
            files = {PATH: bundle().replace(b'module.exports=1;', factory)}
            expanded = C.expand_module_roots(roots(files), files)
            self.assertIn(PATH+'::@error', expanded['modules'])
            with C.module_sources(files), self.assertRaises(C.NeedsScope):
                C.select_inputs(roots(files), scope('Skin'))
    def test_source_metadata_must_match_package_hash(self):
        a, b = self.pair();b['modules'][PATH+'::@source'] = 'forged'
        self.assertFalse(C.module_coverage(a, b)['covered'])
    def test_unparsed_other_changed_js_remains_uncovered(self):
        changed = dict(self.new, **{'ordinary.js': b'var ordinary=2;'})
        a, b = self.pair(new=changed)
        self.assertFalse(C.module_coverage(a, b)['covered'])
        self.assertIn('ordinary.js', C.module_coverage(a, b)['unparsed_bundles'])


if __name__ == '__main__':
    unittest.main()
